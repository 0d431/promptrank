import os
import glob
import json
from competition.loader import *


##############################################
def load_grades(grading_state, grading, discard_outdated=True):
    """Load the gradings into a competition state"""

    competition = grading_state["meta"]["competition"]["name"]

    # check if grading exists
    if not os.path.exists(f"competitions/{competition}/gradings/{grading}"):
        print(f"Grading {grading} does not exist")
        exit(-1)

    # load the grades
    grading_state["grades"] = {}
    for grade_filename in glob.glob(
        f"competitions/{competition}/gradings/{grading}/grades/*.json"
    ):
        with open(grade_filename, "r") as file:
            grade_time = os.path.getmtime(grade_filename)
            grade_name = get_name_from_path(grade_filename)
            grade = json.load(file)

            # skip if player is not in the active set
            if grade["player"]["name"] not in grading_state["players"]:
                continue

            # ok, use this grade
            grading_state["grades"][grade_name] = grade

            # if this match is older than challenge or player or eval, discard it
            player_time = grading_state["players"][
                grading_state["grades"][grade_name]["player"]["name"]
            ]["updated"]
            challenge_time = grading_state["challenges"][
                grading_state["grades"][grade_name]["challenge"]
            ]["updated"]

            if discard_outdated and grade_time < max(player_time, challenge_time):
                print(f"      discarding outdated grade {grade_name}")
                del grading_state["grades"][grade_name]
                os.remove(grade_filename)

    print(f"    loaded {len(grading_state['grades'])} previous grades")

    # clean up performances that are older than the respective player or challenge
    for performance_filename in glob.glob(
        f"competitions/{competition}/performances/*.json"
    ):
        performance_time = os.path.getmtime(performance_filename)
        performance_name = get_name_from_path(performance_filename)
        player_name = performance_name.split(":")[1]
        challenge_name = performance_name.split(":")[0]

        # skip players not in this set
        if player_name not in grading_state["players"]:
            continue

        player_time = grading_state["players"][player_name]["updated"]
        challenge_time = grading_state["challenges"][challenge_name]["updated"]

        if discard_outdated and performance_time < max(player_time, challenge_time):
            print(f"      discarding outdated performance {performance_name}")
            os.remove(performance_filename)

    return grading_state


##############################################
def load_grading(competition, grading, player_set):
    """Load a grading into a competition state"""

    grading_state = load_element(competition, "gradings", grading, player_set)
    load_grades(grading_state, grading)

    return grading_state


##############################################
def load_gradings(competition, grading, player_set):
    """Load all gradings of a competition"""
    gradings = {}
    for grading_name in resolve_elements(competition, "gradings", grading):
        gradings[grading_name] = load_grading(competition, grading_name, player_set)

    return gradings
