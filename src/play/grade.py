import re
import json
from llm import complete
from src.competition.leaderboard import update_leaderboard_with_grade
from src.play.perform import perform, escape_player_name, run_in_parallel


##############################################
def _get_grade_id(challenge_name, player_name):
    """Generate a unique ID for a grading"""

    return challenge_name + ":" + escape_player_name(player_name)


##############################################
def _find_performance(tournament, next_performances):
    """Find the next performance to grade"""

    # find the number of grades per player
    gradings_by_player = {player_name: 0 for player_name in tournament["players"]}

    for grade in tournament["grades"].values():
        player_name = grade["player"]["name"]
        gradings_by_player[player_name] = gradings_by_player[player_name] + 1

    # add the planned gradings
    for _, challenge_name, player_name in next_performances:
        gradings_by_player[player_name] = gradings_by_player[player_name] + 1

    # get the name of the player with least grades
    player_name = min(gradings_by_player, key=lambda k: gradings_by_player[k])

    # find the first challenge that this player has not yet been graded on
    next_challenge_name = None
    for challenge_name in tournament["challenges"]:
        grade_id = _get_grade_id(challenge_name, player_name)
        if grade_id not in tournament["grades"]:
            # check this is not already planned
            found = False
            for _, planned_challenge_name, planned_player_name in next_performances:
                if (
                    planned_player_name == player_name
                    and planned_challenge_name == challenge_name
                ):
                    found = True
                    break

            if not found:
                next_challenge_name = challenge_name
                break

    # find next minimum number of performances graded
    gradings_by_player[player_name] = gradings_by_player[player_name] + 1
    next_min_performances = min(gradings_by_player.values())

    return next_challenge_name, player_name, next_min_performances


##############################################
def _evaluate(tournament, challenge, output):
    """Perform the grading of a performance"""

    evaluation = complete(
        prompt=tournament["grading"]["prompt"].format(
            **challenge,
            objective=tournament["grading"]["objective"],
            output=output,
        ),
        system=tournament["grading"].get("system", ""),
        model=tournament["grading"]["model"],
        temperature=tournament["grading"]["temperature"],
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
def _grade_performance(tournament, challenge_name, player_name):
    """Grade a player's performance on a challenge"""

    id = _get_grade_id(challenge_name, player_name)
    challenge = tournament["challenges"][challenge_name]
    player = tournament["players"][player_name]

    # perform performances if needed
    performance = perform(tournament, challenge_name, player)

    # get grade
    awarded_grade, reasoning = _evaluate(
        tournament,
        challenge,
        performance["output"],
    )

    # if the grade is not an A, repeat until majority decision
    if awarded_grade not in ("A", "Z"):
        grade_map = {"A": 0, "B": 0, "C": 0, "D": 0, "X": 0, "Z": 0}
        grade_map[awarded_grade] = 1

        while True:
            # get grade
            new_awarded_grade, new_reasoning = _evaluate(
                tournament,
                challenge,
                performance["output"],
            )

            # update the grade map
            grade_map[new_awarded_grade] = grade_map[new_awarded_grade] + 1

            # majority now?
            if grade_map[new_awarded_grade] > sum(grade_map.values()) / 2:
                awarded_grade = new_awarded_grade
                reasoning = f"MAJORITY GRADE ({str(grade_map)}): {new_reasoning}"
                break

            # give up?
            if sum(grade_map.values()) > 10:
                # use grade with relative majority
                awarded_grade = max(grade_map, key=lambda k: grade_map[k])
                reasoning = f"GAVE UP ({str(grade_map)}): {reasoning}"
                break

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
        f"competitions/{tournament['meta']['competition']['name']}/tournaments/{tournament['meta']['tournament']}/grades/{id}.json",
        "w",
    ) as file:
        json.dump(grade, file, indent=2)

    return grade


##############################################
def grade_next_performances(
    tournament, min_performances_all_players, max_performances_to_grade=1
):
    # find next performances to grade
    next_performances = []
    while len(next_performances) < max_performances_to_grade:
        challenge_name, player_name, next_min_performances = _find_performance(
            tournament, next_performances
        )

        if challenge_name is None:
            break

        next_performances.append((tournament, challenge_name, player_name))

        if next_min_performances >= min_performances_all_players:
            break

    # grade the performances
    grades = run_in_parallel(_grade_performance, next_performances, 5)

    # store
    for grade in grades:
        tournament["grades"][grade["id"]] = grade
        update_leaderboard_with_grade(tournament, grade)

    # return the new minimum number of performances graded
    return next_min_performances
