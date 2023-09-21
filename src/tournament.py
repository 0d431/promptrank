import os
import glob
import json
import yaml
from leaderboard import generate_leaderboard


##############################################
def load_tournament(competition, tournament, player_set=""):
    """Load the competition into a structure representing its state"""

    print(
        f"Loading tournament {tournament.upper()} of competition {competition.upper()}"
    )

    tournament_state = dict(
        meta={"competition": competition, "tournament": tournament},
        players={},
        challenges={},
        evaluation={},
        matches=[],
    )

    # check if competition exists
    if not os.path.exists(f"competitions/{competition}"):
        print(f"Competition {competition} does not exist")
        exit(-1)

    # load the players

    # obtain the valid player globs
    player_globs = ["*"]
    tournament_state["meta"]["player_set"] = player_set

    if player_set != "":
        if not os.path.exists(
            f"competitions/{competition}/player_sets/{player_set}.players"
        ):
            print(f"Player set {player_set} does not exist")
            exit(-1)

        print(f"    loading player set {player_set.upper()}")
        with open(
            f"competitions/{competition}/player_sets/{player_set}.players",
            "r",
        ) as f:
            # read player globs from all non-empty lines
            player_globs = [
                line.strip() for line in f.readlines() if line.strip() != ""
            ]

    # load players
    for player_filename in glob.glob(f"competitions/{competition}/players/*.yaml"):
        # is the player filename matching any of the player set globs?
        played_is_in = False
        for player_glob in player_globs:
            direction, pattern = (False, player_glob[1:]) if player_glob.startswith("!") else (True, player_glob)
            if glob.fnmatch.fnmatch(player_filename.split("/")[-1], pattern):
                played_is_in = direction

        if not played_is_in:
            continue

        with open(player_filename, "r") as file:
            player_name = player_filename.split("/")[-1].split(".")[0]
            tournament_state["players"][player_name] = yaml.safe_load(file)
            tournament_state["players"][player_name]["name"] = player_name
            tournament_state["players"][player_name]["updated"] = os.path.getmtime(
                player_filename
            )

    print(f"    loaded {len(tournament_state['players'])} players")

    # load the challenges
    for challenge_filename in glob.glob(
        f"competitions/{competition}/challenges/*.yaml"
    ):
        with open(challenge_filename, "r") as file:
            challenge_name = challenge_filename.split("/")[-1].split(".")[0]
            tournament_state["challenges"][challenge_name] = yaml.safe_load(file)
            tournament_state["challenges"][challenge_name]["name"] = challenge_name
            tournament_state["challenges"][challenge_name][
                "updated"
            ] = os.path.getmtime(challenge_filename)

    print(f"    loaded {len(tournament_state['challenges'])} challenges")

    # check if tournament exists
    if not os.path.exists(f"competitions/{competition}/tournaments/{tournament}"):
        print(f"Tournament {tournament} does not exist")
        exit(-1)

    # load the evaluation
    eval_filename = (
        f"competitions/{competition}/tournaments/{tournament}/evaluation.yaml"
    )
    eval_time = os.path.getmtime(eval_filename)
    with open(eval_filename, "r") as file:
        tournament_state["evaluation"] = yaml.safe_load(file)

    # load the matches
    tournament_state["matches"] = {}
    for match_filename in glob.glob(
        f"competitions/{competition}/tournaments/{tournament}/matches/*.json"
    ):
        with open(match_filename, "r") as file:
            match_time = os.path.getmtime(match_filename)
            match_name = match_filename.split("/")[-1].split(".")[0]
            match = json.load(file)

            # skip if either player is not in the active set
            if (
                match["player_A"]["name"] not in tournament_state["players"]
                or match["player_B"]["name"] not in tournament_state["players"]
            ):
                continue

            # ok, use this match
            tournament_state["matches"][match_name] = match

            # if this match is older than challenge or players or eval, discard it
            player_A_time = tournament_state["players"][
                tournament_state["matches"][match_name]["player_A"]["name"]
            ]["updated"]
            player_B_time = tournament_state["players"][
                tournament_state["matches"][match_name]["player_B"]["name"]
            ]["updated"]
            challenge_time = tournament_state["challenges"][
                tournament_state["matches"][match_name]["challenge"]
            ]["updated"]

            if match_time < max(
                player_A_time, player_B_time, challenge_time, eval_time
            ):
                print(f"Discarding outdated match {match_name}")
                del tournament_state["matches"][match_name]
                os.remove(match_filename)

    print(f"    loaded {len(tournament_state['matches'])} previous matches")

    # clean up performances that are older than the respective player or challenge
    for performance_filename in glob.glob(
        f"competitions/{competition}/performances/*.json"
    ):
        performance_time = os.path.getmtime(performance_filename)
        performance_name = performance_filename.split("/")[-1].split(".")[0]
        player_name = performance_name.split(":")[1]
        challenge_name = performance_name.split(":")[0]

        # skip players not in this set
        if player_name not in tournament_state["players"]:
            continue

        player_time = tournament_state["players"][player_name]["updated"]
        challenge_time = tournament_state["challenges"][challenge_name]["updated"]

        if performance_time < max(player_time, challenge_time):
            print(f"Discarding outdated performance {performance_name}")
            os.remove(performance_filename)

    # generate the leaderboard
    generate_leaderboard(tournament_state)
    print(f"    generated leaderboard")

    # calc number of matches
    tournament_state["meta"]["pairings"] = int(
        (len(tournament_state["players"]) * (len(tournament_state["players"]) - 1))
        * len(tournament_state["challenges"])
    )
    print(
        f"    {len(tournament_state['matches'])} of {tournament_state['meta']['pairings']} matches played"
    )

    return tournament_state
