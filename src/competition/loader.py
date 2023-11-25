import os
import json
import glob
import yaml
from src.competition.leaderboard import generate_leaderboard
from src.play.perform import unescape_player_name


##############################################
def get_name_from_path(path):
    """Get the name of a file from its path"""
    return ".".join(path.split("/")[-1].split(".")[:-1])


##############################################
def resolve_tournaments(competition, tournament=""):
    """Get all tournaments of a competition"""
    if tournament != "":
        return [tournament]
    else:
        return [
            tournament.split("/")[-1]
            for tournament in glob.glob(f"competitions/{competition}/tournaments/*")
        ]


##############################################
def load_matches(competition, tournament_state, discard_outdated=True):
    """Load the competition into a structure representing its state"""

    tournament = tournament_state["meta"]["tournament"]

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



##############################################
def load_grades(competition, tournament_state, discard_outdated=True):
    """Load the gradings into a competition state"""

    tournament = tournament_state["meta"]["tournament"]

    # load the grades
    tournament_state["grades"] = {}
    for grade_filename in glob.glob(
        f"competitions/{competition}/tournaments/{tournament}/grades/*.json"
    ):
        with open(grade_filename, "r") as file:
            grade_time = os.path.getmtime(grade_filename)
            grade_name = get_name_from_path(grade_filename)
            grade = json.load(file)

            # skip if player is not in the active set
            if grade["player"]["name"] not in tournament_state["players"]:
                continue

            # ok, use this grade
            tournament_state["grades"][grade_name] = grade

            # if this match is older than challenge or player or eval, discard it
            player_time = tournament_state["players"][
                tournament_state["grades"][grade_name]["player"]["name"]
            ]["updated"]
            challenge_time = tournament_state["challenges"][
                tournament_state["grades"][grade_name]["challenge"]
            ]["updated"]

            if discard_outdated and grade_time < max(player_time, challenge_time):
                print(f"      discarding outdated grade {grade_name}")
                del tournament_state["grades"][grade_name]
                os.remove(grade_filename)

    print(f"    loaded {len(tournament_state['grades'])} previous grades")

    # clean up performances that are older than the respective player or challenge
    for performance_filename in glob.glob(
        f"competitions/{competition}/performances/*.json"
    ):
        performance_time = os.path.getmtime(performance_filename)
        performance_name = get_name_from_path(performance_filename)
        player_name = unescape_player_name(performance_name.split(":")[1])
        challenge_name = performance_name.split(":")[0]

        # skip players not in this set
        if player_name not in tournament_state["players"]:
            continue

        player_time = tournament_state["players"][player_name]["updated"]
        challenge_time = tournament_state["challenges"][challenge_name]["updated"]

        if discard_outdated and performance_time < max(player_time, challenge_time):
            print(f"      discarding outdated performance {performance_name}")
            os.remove(performance_filename)


##############################################
def load_players(competition, tournament_state, player_set):
    """Load the players into a competition state"""

    # obtain the valid player globs
    player_globs = ["*"]
    tournament_state["meta"]["player_set"] = player_set if player_set != "" else "all"

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
    for player_filename in glob.glob(
        f"competitions/{competition}/players/**/*.yaml", recursive=True
    ):
        # is the player filename matching any of the player set globs?
        played_is_in = False
        for player_glob in player_globs:
            direction, pattern = (
                (False, player_glob[1:])
                if player_glob.startswith("!")
                else (True, player_glob)
            )
            if glob.fnmatch.fnmatch("/".join(player_filename.split("/")[3:]), pattern):
                played_is_in = direction

        if not played_is_in:
            continue

        with open(player_filename, "r") as file:
            player = yaml.safe_load(file)
            player_name = player.get("name", get_name_from_path(player_filename))

            if player_name in tournament_state["players"]:
                print(
                    f"      WARNING: player {player_name} already exists, overwriting"
                )

            tournament_state["players"][player_name] = player
            tournament_state["players"][player_name]["name"] = player_name
            tournament_state["players"][player_name]["updated"] = os.path.getmtime(player_filename)
            tournament_state["players"][player_name]["performances"] = []

    print(f"    loaded {len(tournament_state['players'])} players")


##############################################
def load_challenges(competition, tournament_state):
    for challenge_filename in glob.glob(f"competitions/{competition}/challenges/*"):
        with open(challenge_filename, "r") as file:
            challenge_name = get_name_from_path(challenge_filename)
            if challenge_filename.endswith(".json"):
                tournament_state["challenges"][challenge_name] = json.load(file)
            else:
                tournament_state["challenges"][challenge_name] = yaml.safe_load(file)

            tournament_state["challenges"][challenge_name]["name"] = challenge_name
            tournament_state["challenges"][challenge_name]["updated"] = os.path.getmtime(
                challenge_filename
            )

    # sort challenges by key ascending
    tournament_state["challenges"] = dict(
        sorted(tournament_state["challenges"].items(), key=lambda x: x[0])
    )

    print(f"    loaded {len(tournament_state['challenges'])} challenges")


##############################################
def load_evaluation(competition, tournament, evaluation):
    """Load the comparative evaluation into a competition state"""

    eval_filename = (
        f"competitions/{competition}/tournaments/{tournament}/{evaluation}.yaml"
    )
    if os.path.exists(eval_filename):
        with open(eval_filename, "r") as file:
            return yaml.safe_load(file)
        
    return None


##############################################
def load_tournament(competition, tournament, player_set=""):
    """Load the competition into a structure representing its state"""

    print(f"  loading {tournament.upper()} of competition {competition.upper()}")

    state = dict(
        meta={"tournament": tournament, "stats": {}},
        players={},
        challenges={},
        comparison={},
        grading={},
        matches=[],
        grades=[],
    )

    # check if competition exists
    if not os.path.exists(f"competitions/{competition}"):
        print(f"Competition {competition} does not exist")
        exit(-1)

    # check if tournament exists
    if not os.path.exists(f"competitions/{competition}/tournaments/{tournament}"):
        print(f"Tournament {tournament} does not exist")
        exit(-1)

    # load the competition
    competition_filename = f"competitions/{competition}/competition.yaml"
    with open(competition_filename, "r") as file:
        state["meta"]["competition"] = yaml.safe_load(file)

    # load the players
    load_players(competition, state, player_set)

    # load the challenge
    load_challenges(competition, state)

    # load the matches
    load_matches(competition, state)

    # load the grades
    load_grades(competition, state)

    # load the comparative evaluation
    state["comparison"] = load_evaluation(competition, tournament, "comparison")

    # load the grading evaluation
    state["grading"] = load_evaluation(competition, tournament, "grading")
    
    return state


##############################################
def load_tournaments(competition, tournament, player_set):
    """Load all tournaments of a competition"""
    tournaments = {}
    for tournament_name in resolve_tournaments(competition, tournament):
        tournaments[tournament_name] = load_tournament(
            competition, tournament_name, player_set
        )

    return tournaments
