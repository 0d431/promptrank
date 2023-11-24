import os
import json
import glob
import yaml


##############################################
def get_name_from_path(path):
    """Get the name of a file from its path"""
    return ".".join(path.split("/")[-1].split(".")[:-1])


##############################################
def resolve_elements(competition, type, element=""):
    """Get all elements of a competition"""
    if element != "":
        return [element]
    else:
        return [
            tournament.split("/")[-1]
            for tournament in glob.glob(f"competitions/{competition}/{type}/*")
        ]


##############################################
def load_element(competition, element_type, element, player_set=""):
    """Load the competition into a structure representing its state"""

    print(f"  loading {element.upper()} of competition {competition.upper()}")

    state = dict(
        meta={element_type: element, "stats": {}},
        players={},
        challenges={},
        evaluation={},
    )

    # check if competition exists
    if not os.path.exists(f"competitions/{competition}"):
        print(f"Competition {competition} does not exist")
        exit(-1)

    # load the competition
    competition_filename = f"competitions/{competition}/competition.yaml"
    with open(competition_filename, "r") as file:
        state["meta"]["competition"] = yaml.safe_load(file)

    # load the players

    # obtain the valid player globs
    player_globs = ["*"]
    state["meta"]["player_set"] = player_set if player_set != "" else "all"

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

            if player_name in state["players"]:
                print(
                    f"      WARNING: player {player_name} already exists, overwriting"
                )

            state["players"][player_name] = player
            state["players"][player_name]["name"] = player_name
            state["players"][player_name]["updated"] = os.path.getmtime(player_filename)
            state["players"][player_name]["performances"] = []
            
    print(f"    loaded {len(state['players'])} players")

    # load the challenges
    for challenge_filename in glob.glob(
        f"competitions/{competition}/challenges/*"
    ):
        with open(challenge_filename, "r") as file:
            challenge_name = get_name_from_path(challenge_filename)
            if challenge_filename.endswith(".json"):
                state["challenges"][challenge_name] = json.load(file)
            else:
                state["challenges"][challenge_name] = yaml.safe_load(file)

            state["challenges"][challenge_name]["name"] = challenge_name
            state["challenges"][challenge_name]["updated"] = os.path.getmtime(
                challenge_filename
            )

    print(f"    loaded {len(state['challenges'])} challenges")

    # load performance history
    for performance_filename in glob.glob(
        f"competitions/{competition}/performances/*.json"
    ):
        with open(performance_filename, "r") as file:
            performance = json.load(file)

            # skip players not in this set
            if performance["player"] not in state["players"]:
                continue

            state["players"][performance["player"]]["performances"].append(
                performance["challenge"]
            )

    # check if element exists
    if not os.path.exists(f"competitions/{competition}/{element_type}/{element}"):
        print(f"{element_type.capitalize()} {element} does not exist")
        exit(-1)

    # load the evaluation
    eval_filename = (
        f"competitions/{competition}/{element_type}/{element}/evaluation.yaml"
    )
    eval_time = os.path.getmtime(eval_filename)
    with open(eval_filename, "r") as file:
        state["evaluation"] = yaml.safe_load(file)

    return state


##############################################
def load_elements(competition, element_type, element, player_set):
    """Load all elements of a competition"""
    elements = {}
    for element_name in resolve_elements(competition, element_type, element):
        elements[element_name] = load_element(
            competition, element_type, element_name, player_set
        )

    return elements
