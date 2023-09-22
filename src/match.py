import re
import os
import json
import random
import datetime
import numpy as np
from llm import complete
from leaderboard import update_leaderboard
from tournament import load_tournament, resolve_tournaments


##############################################
def _get_match_id(challenge_name, player_A_name, player_B_name):
    """Generate a unique ID for a match"""

    return challenge_name + ":" + player_A_name + "<>" + player_B_name


##############################################
def _get_performance_id(challenge_name, player_name):
    """Generate a unique ID for a performance"""

    return challenge_name + ":" + player_name


##############################################
def _find_match(tournament_state, min_matches_to_play):
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

    # make sure to ignore diagonal
    for i in range(len(labels)):
        matches[i, i] = 100000

    # find the pair of players with the least matches
    min_matches = np.min(matches)
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
def _evaluate(
    tournament_state, challenge, player_A_name, output_A, player_B_name, output_B
):
    """Perform the evaluation of a match"""

    evaluation = complete(
        tournament_state["evaluation"]["model"],
        tournament_state["evaluation"]["temperature"],
        prompt=tournament_state["evaluation"]["prompt"].format(
            **challenge,
            objective=tournament_state["evaluation"]["objective"],
            criteria=tournament_state["evaluation"]["criteria"],
            output_A=output_A,
            output_B=output_B,
        ),
        system=tournament_state["evaluation"].get("system", ""),
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
def _perform(tournament_state, challenge_name, player):
    """Perform a performance for a player"""

    performance_file = f"competitions/{tournament_state['meta']['competition']}/performances/{_get_performance_id(challenge_name, player['name'])}.json"
    if not os.path.exists(performance_file):
        # create the performance
        print(f"      {player['name']} performs {challenge_name}")
        challenge = tournament_state["challenges"][challenge_name]
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
def run_match(tournament_state, min_matches):
    """Run a match between two players"""

    # find next match
    challenge_name, player_A_name, player_B_name, min_played = _find_match(
        tournament_state, min_matches
    )

    if challenge_name is not None:
        # play the next match
        id = _get_match_id(challenge_name, player_A_name, player_B_name)
        print(f"    {player_A_name} vs {player_B_name} on challenge {challenge_name}")

        challenge = tournament_state["challenges"][challenge_name]
        player_A = tournament_state["players"][player_A_name]
        player_B = tournament_state["players"][player_B_name]

        # perform performances if needed
        performances = {}
        for player in (player_A, player_B):
            performances[player["name"]] = _perform(
                tournament_state, challenge_name, player
            )

        # perform the evaluation
        player_A_output = performances[player_A_name]["output"]
        player_B_output = performances[player_B_name]["output"]

        assessment, winner_name = _evaluate(
            tournament_state,
            challenge,
            player_A_name,
            player_A_output,
            player_B_name,
            player_B_output,
        )

        # create the match record
        match = {
            "player_A": {"name": player_A_name},
            "player_B": {"name": player_B_name},
            "challenge": challenge["name"],
            "result": {"winner": winner_name, "assessment": assessment},
        }
        tournament_state["matches"][id] = match

        # store the match
        with open(
            f"competitions/{tournament_state['meta']['competition']}/tournaments/{tournament_state['meta']['tournament']}/matches/{id}.json",
            "w",
        ) as file:
            json.dump(match, file, indent=2)

        # update leaderboard
        update_leaderboard(tournament_state, match)
    else:
        print(f"    all pairs have played at least {min_played:.0f} matches")

    return min_played


##############################################
def play(competition, tournament, player_set, number_matches):
    """Play a number of matches."""

    for tournament in resolve_tournaments(competition, tournament):
        print(
            f"Playing {number_matches} matches for each pair in player set {player_set.upper()} for tournament {tournament.upper()}..."
        )

        tournament_state = load_tournament(competition, tournament, player_set)
        while True:
            min_played = run_match(tournament_state, number_matches)

            if min_played == number_matches:
                break

            print(
                f"  {tournament.upper()} match {len(tournament_state['matches']) + 1}/{tournament_state['meta']['pairings']} - {min_played:.0f} matches played by all pairs"
            )
