import re
import os
import json
import random
import datetime
import numpy as np
import concurrent.futures
from llm import complete
from leaderboard import update_leaderboard
from tournament import load_tournament, resolve_tournaments


##############################################
def run_in_parallel(fun, args, max_workers=5):
    """Execute a function in parallel on a set of args"""
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_arg = {executor.submit(fun, *arg): arg for arg in args}
        for future in concurrent.futures.as_completed(future_to_arg):
            results.append(future.result())

    return results


##############################################
def _escape_player_name(player_name):
    """Escape a player name for use in a filename"""
    return player_name.replace("/", "=")


##############################################
def _get_match_id(challenge_name, player_A_name, player_B_name):
    """Generate a unique ID for a match"""

    return (
        challenge_name
        + ":"
        + _escape_player_name(player_A_name)
        + "<>"
        + _escape_player_name(player_B_name)
    )


##############################################
def _get_performance_id(challenge_name, player_name):
    """Generate a unique ID for a performance"""

    return challenge_name + ":" + _escape_player_name(player_name)


##############################################
def _find_match(tournament_state, min_matches_to_play, player_name=None, scheduled_matches=[]):
    """Find the next match to play"""

    def _randomize(it):
        l = list(it)
        random.shuffle(l)
        return l

    # find the number of matches played among players
    labels = list(tournament_state["players"].keys())
    matches = np.zeros(
        (len(tournament_state["players"]), len(tournament_state["players"]))
    )

    for match in tournament_state["matches"].values():
        player_A_ix = labels.index(match["player_A"]["name"])
        player_B_ix = labels.index(match["player_B"]["name"])

        matches[player_A_ix, player_B_ix] += 1
        matches[player_B_ix, player_A_ix] += 1

    # add scheduled matches
    for match in scheduled_matches:
        player_A_ix = labels.index(match[2])
        player_B_ix = labels.index(match[3])

        matches[player_A_ix, player_B_ix] += 1
        matches[player_B_ix, player_A_ix] += 1

    # make sure to ignore diagonal
    for i in range(len(labels)):
        matches[i, i] = 100000

    # if a player is given, make sure to ignore other pairings
    if player_name is not None:
        for i, player_A_name in enumerate(labels):
            for j, player_B_name in enumerate(labels):
                if player_A_name != player_name and player_B_name != player_name:
                    matches[i, j] = 100000
                    matches[j, i] = 100000

    # find the pair of players with the least matches
    min_matches = int(np.min(matches))
    if min_matches >= min_matches_to_play:
        return None, None, None, min_matches

    player_A_ix, player_B_ix = np.where(matches == min_matches)
    player_A_name = labels[player_A_ix[0]]
    player_B_name = labels[player_B_ix[0]]

    # find a random challenge that this pair has not played yet
    for challenge_name in _randomize(tournament_state["challenges"].keys()):
        if (
            _get_match_id(challenge_name, player_A_name, player_B_name)
            not in tournament_state["matches"]
        ):
            return challenge_name, player_A_name, player_B_name, min_matches
        if (
            _get_match_id(challenge_name, player_B_name, player_A_name)
            not in tournament_state["matches"]
        ):
            return challenge_name, player_B_name, player_A_name, min_matches

    return None, None, None, min_matches


##############################################
def _evaluate(tournament, challenge, player_A_name, output_A, player_B_name, output_B):
    """Perform the evaluation of a match"""

    # print(f"      {tournament['meta']['tournament'].upper()} - evaluating {player_A_name} vs {player_B_name} on {challenge['name']}")
    evaluation = complete(
        tournament["evaluation"]["model"],
        tournament["evaluation"]["temperature"],
        prompt=tournament["evaluation"]["prompt"].format(
            **challenge,
            objective=tournament["evaluation"]["objective"],
            criteria=tournament["evaluation"]["criteria"],
            output_A=output_A,
            output_B=output_B,
        ),
        system=tournament["evaluation"].get("system", ""),
    )

    match = re.search(r"(?<=Assessment: ).*?(?=\n)", evaluation)
    if match:
        assessment = match.group(0).strip()
    else:
        print("Failed to parse evaluation: " + evaluation)
        exit(-1)

    match = re.search(r"(?<=Winner: ).*?$", evaluation)
    if match:
        winner = match.group(0).strip()
    else:
        print("Failed to parse evaluation: " + evaluation)
        exit(-1)

    if winner == "A":
        winner = player_A_name
    elif winner == "B":
        winner = player_B_name

    return assessment, winner


##############################################
def _perform(tournament, challenge_name, player):
    """Perform a performance for a player"""

    performance_file = f"competitions/{tournament['meta']['competition']['name']}/performances/{_get_performance_id(challenge_name, player['name'])}.json"
    if not os.path.exists(performance_file):
        # create the performance
        # print(f"      {player['name']} performs {challenge_name}")
        challenge = tournament["challenges"][challenge_name]
        challenge["date"] = f"{datetime.datetime.now():%Y-%m-%d}"
        performance = {
            "player": player["name"],
            "challenge": challenge_name,
            "output": complete(
                player["model"],
                player["temperature"],
                player["prompt"].format(**challenge),
            ),
        }

        # store the performance
        with open(performance_file, "w") as file:
            json.dump(performance, file, indent=2)
    else:
        # load the performance
        with open(performance_file, "r") as file:
            performance = json.load(file)

    return performance


##############################################
def _play_match(tournament, challenge_name, player_A_name, player_B_name):
    """Play a match between two players"""

    id = _get_match_id(challenge_name, player_A_name, player_B_name)
    challenge = tournament["challenges"][challenge_name]
    player_A = tournament["players"][player_A_name]
    player_B = tournament["players"][player_B_name]

    # perform performances if needed
    performances = {}
    for player in (player_A, player_B):
        performances[player["name"]] = _perform(tournament, challenge_name, player)

    # perform the evaluation
    player_A_output = performances[player_A_name]["output"]
    player_B_output = performances[player_B_name]["output"]

    assessment, winner_name = _evaluate(
        tournament,
        challenge,
        player_A_name,
        player_A_output,
        player_B_name,
        player_B_output,
    )

    # create the match record
    match = {
        "id": id,
        "player_A": {"name": player_A_name},
        "player_B": {"name": player_B_name},
        "challenge": challenge["name"],
        "result": {"winner": winner_name, "assessment": assessment},
    }

    # store the match
    with open(
        f"competitions/{tournament['meta']['competition']['name']}/tournaments/{tournament['meta']['tournament']}/matches/{id}.json",
        "w",
    ) as file:
        json.dump(match, file, indent=2)

    return match


##############################################
def play_next_matches(
    tournament, min_matches_all_players, player_name=None, max_matches_to_play=1
):
    """Run a match between two players"""

    # find next matches
    next_matches = []
    while len(next_matches) < max_matches_to_play:
        challenge_name, player_A_name, player_B_name, next_min_matches = _find_match(
            tournament, min_matches_all_players, player_name, next_matches
        )

        if challenge_name is None:
            break

        next_matches.append((tournament, challenge_name, player_A_name, player_B_name))

        if next_min_matches >= min_matches_all_players:
            break

    # play the matches
    matches = run_in_parallel(_play_match, next_matches, 5)

    # update leaderboard
    for match in matches:
        tournament["matches"][match["id"]] = match
        update_leaderboard(tournament, match)

    # return the new minimum number of matches played
    return next_min_matches


##############################################
def play(competition, tournament_name, player_set, number_matches, player_name=None):
    """Play a number of matches."""

    objective = f"against {player_name}" if player_name else "for all player pairs"

    tournaments = {}
    for tournament_name in resolve_tournaments(competition, tournament_name):
        print(
            f"Playing {number_matches} matches {objective} in player set {player_set.upper()} for tournament {tournament_name.upper()}..."
        )

        tournament = load_tournament(competition, tournament_name, player_set)
        tournaments[tournament_name] = tournament

        while True:
            min_matches_all_players = play_next_matches(
                tournament, number_matches, player_name, 5
            )
            print(
                f"    {tournament_name.upper()} - {len(tournament['matches'])} matches played; {min_matches_all_players:.0f}/{number_matches} {objective}"
            )
            if min_matches_all_players >= number_matches:
                break

    return tournaments
