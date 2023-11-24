import re
import json
import numpy as np
from llm import complete
from competition.grading import load_grading
from competition.loader import resolve_elements
from const import GRADING
from src.play.perform import *


##############################################
def _get_grade_id(challenge_name, player_name):
    """Generate a unique ID for a grading"""

    return challenge_name + ":" + escape_player_name(player_name)


##############################################
def _find_performance(grading):
    """Find the next performance to grade"""

    # find the number of grades per player
    gradings_by_player = {player_name: 0 for player_name in grading["players"]}

    for grade in grading["grades"].values():
        player_name = grade["player"]["name"]
        gradings_by_player[player_name] = gradings_by_player[player_name] + 1

    # get the name of the player with least grades
    player_name = min(gradings_by_player, key=lambda k: gradings_by_player[k])

    # find the first challenge that this player has not yet been graded on
    next_challenge_name = None
    for challenge_name in grading["challenges"]:
        grade_id = _get_grade_id(challenge_name, player_name)
        if grade_id not in grading["grades"]:
            next_challenge_name = challenge_name
            break

    return next_challenge_name, player_name, gradings_by_player[player_name] + 1


##############################################
def _evaluate(grading, challenge, output):
    """Perform the grading of a performance"""

    evaluation = complete(
        grading["evaluation"]["model"],
        grading["evaluation"]["temperature"],
        prompt=grading["evaluation"]["prompt"].format(
            **challenge,
            objective=grading["evaluation"]["objective"],
            output=output,
        ),
        system=grading["evaluation"].get("system", ""),
    )

    match = re.search(r"(?<=Grade: ).*?(?=\n)", evaluation)
    if match:
        assessment = match.group(0).strip()
    else:
        print("Failed to parse evaluation: " + evaluation)
        exit(-1)

    match = re.search(r"(?<=Reasoning: ).*\b", evaluation)
    if match:
        reasoning = match.group(0).strip()
    else:
        print("Failed to parse evaluation: " + evaluation)
        exit(-1)

    return assessment, reasoning


##############################################
def _grade_performance(grading, challenge_name, player_name):
    """Grade a player's performance on a challenge"""

    id = _get_grade_id(challenge_name, player_name)
    challenge = grading["challenges"][challenge_name]
    player = grading["players"][player_name]

    # perform performances if needed
    performance = perform(grading, challenge_name, player)

    # get grade
    awarded_grade, reasoning = _evaluate(
        grading,
        challenge,
        performance["output"],
    )

    # create the grade record
    grade = {
        "id": id,
        "player": {"name": player_name},
        "grade": awarded_grade,
        "reasoning": reasoning,
        "challenge": challenge["name"],
        "challenge_details": challenge,
        "player_output": performance["output"],
    }

    # store the match
    with open(
        f"competitions/{grading['meta']['competition']['name']}/{GRADING}/{grading['meta'][GRADING]}/grades/{id}.json",
        "w",
    ) as file:
        json.dump(grade, file, indent=2)

    return grade


##############################################
def grade_next_performances(
    grading, min_performances_all_players, max_performances_to_grade=1
):
    # find next performances to grade
    next_performances = []
    while len(next_performances) < max_performances_to_grade:
        challenge_name, player_name, next_min_performances = _find_performance(grading)

        if challenge_name is None:
            break

        next_performances.append((grading, challenge_name, player_name))

        if next_min_performances >= min_performances_all_players:
            break

    # grade the performances
    grades = run_in_parallel(_grade_performance, next_performances, 5)

    # store
    for grade in grades:
        grading["grades"][grade["id"]] = grade

    # return the new minimum number of performances graded
    return next_min_performances


##############################################
def grade_players(competition, grading_name, player_set, number_performances):
    """Grade at least N matches."""

    gradings = {}
    for grading_name in resolve_elements(competition, GRADING, grading_name):
        print(
            f"Grading {number_performances} performances in player set {player_set.upper()} for grading {grading_name.upper()}..."
        )

        grading = load_grading(competition, grading_name, player_set)
        gradings[grading_name] = grading

        while True:
            min_performances_all_players = grade_next_performances(
                grading, number_performances, 10
            )
            print(
                f"    {grading_name.upper()} - {len(grading['grades'])} performances graded; {min_performances_all_players:.0f}/{number_performances}"
            )
            if min_performances_all_players >= number_performances:
                break

    return gradings
