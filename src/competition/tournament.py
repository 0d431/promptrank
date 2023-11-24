import os
import glob
import json
from competition.loader import *
from competition.leaderboard import generate_leaderboard
from const import TOURNAMENT


##############################################
def load_matches(tournament_state, tournament, discard_outdated=True):
    """Load the competition into a structure representing its state"""

    competition = tournament_state["meta"]["competition"]["name"]

    # load the matches
    tournament_state["matches"] = {}
    for match_filename in glob.glob(
        f"competitions/{competition}/tournaments/{tournament}/matches/*.json"
    ):
        with open(match_filename, "r") as file:
            match_time = os.path.getmtime(match_filename)
            match_name = get_name_from_path(match_filename)
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

            if discard_outdated and match_time < max(
                player_A_time, player_B_time, challenge_time
            ):
                print(f"      discarding outdated match {match_name}")
                del tournament_state["matches"][match_name]
                os.remove(match_filename)

    print(f"    loaded {len(tournament_state['matches'])} previous matches")

    # clean up performances that are older than the respective player or challenge
    for performance_filename in glob.glob(
        f"competitions/{competition}/performances/*.json"
    ):
        performance_time = os.path.getmtime(performance_filename)
        performance_name = get_name_from_path(performance_filename)
        player_name = performance_name.split(":")[1]
        challenge_name = performance_name.split(":")[0]

        # skip players not in this set
        if player_name not in tournament_state["players"]:
            continue

        player_time = tournament_state["players"][player_name]["updated"]
        challenge_time = tournament_state["challenges"][challenge_name]["updated"]

        if discard_outdated and performance_time < max(player_time, challenge_time):
            print(f"      discarding outdated performance {performance_name}")
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


##############################################
def load_tournament(competition, tournament, player_set):
    """Load a single tournament of a competition"""
    tournament_state = load_elements(competition, TOURNAMENT, tournament, player_set)[
        tournament
    ]
    load_matches(tournament_state, tournament)

    return tournament_state


##############################################
def load_tournaments(competition, tournament, player_set):
    """Load all tournaments of a competition"""
    tournaments = {}
    for tournament_name in resolve_elements(competition, TOURNAMENT, tournament):
        tournaments[tournament_name] = load_tournament(
            competition, tournament_name, player_set
        )

    return tournaments
