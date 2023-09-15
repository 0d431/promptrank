import re
import os
import json
import random
from llm import complete
from tournament import save_tournament
from leaderboard import update_leaderboard


##############################################
def _get_match_id(challenge_name, player_A_name, player_B_name):
    """Generate a unique ID for a match"""

    player_A_name, player_B_name = sorted([player_A_name, player_B_name])
    return challenge_name + ":" + player_A_name + "<>" + player_B_name


##############################################
def _get_performance_id(challenge_name, player_name):
    """Generate a unique ID for a performance"""

    return challenge_name + ":" + player_name


##############################################
def _find_match(tournament_state):
    """Find the next match to play"""

    def _randomize(it):
        l = list(it)
        random.shuffle(l)
        return l

    for challenge_name in _randomize(tournament_state["challenges"].keys()):
        for player_A_name in _randomize(tournament_state["players"].keys()):
            for player_B_name in _randomize(tournament_state["players"].keys()):
                if player_A_name < player_B_name:
                    if (
                        _get_match_id(challenge_name, player_A_name, player_B_name)
                        not in tournament_state["matches"]
                    ):
                        return challenge_name, player_A_name, player_B_name

    return None, None, None


##############################################
def _do_evaluate(
    tournament_state, challenge, player_A_name, output_A, player_B_name, output_B
):
    """Perform the evaluation of a match"""

    evaluation = complete(
        tournament_state["evaluation"]["model"],
        tournament_state["evaluation"]["temperature"],
        prompt=tournament_state["evaluation"]["prompt"].format(
            **challenge, output_A=output_A, output_B=output_B
        ),
        system=tournament_state["evaluation"]["system"],
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
def _evaluate(
    tournament_state, challenge, player_A_name, output_A, player_B_name, output_B
):
    """Evaluate a match, running symmetrical evaluations for fairness"""

    print("    evaluating match results")

    if len(output_A) == 0 or len(output_B) == 0:
        return "Either player failed to produce output", "DNP"

    # avoid lexical bias
    assessment_1, winner_1 = _do_evaluate(
        tournament_state, challenge, player_A_name, output_A, player_B_name, output_B
    )
    assessment_2, winner_2 = _do_evaluate(
        tournament_state, challenge, player_B_name, output_B, player_A_name, output_A
    )

    if winner_1 == "DRAW":
        return winner_1, assessment_1
    elif winner_2 == "DRAW":
        return winner_2, assessment_2
    elif winner_1 != winner_2:
        return (
            "DRAW",
            f"Inconclusive assessments: {assessment_1} <--VS--> {assessment_2}",
        )
    else:
        return assessment_1, winner_1


##############################################
def run_match(tournament_state):
    """Run a match between two players"""

    # find next match
    challenge_name, player_A_name, player_B_name = _find_match(tournament_state)
    if challenge_name is not None:
        # play the next match
        id = _get_match_id(challenge_name, player_A_name, player_B_name)
        print(f"    playing match {player_A_name} vs {player_B_name} on challenge {challenge_name}")

        challenge = tournament_state["challenges"][challenge_name]
        player_A = tournament_state["players"][player_A_name]
        player_B = tournament_state["players"][player_B_name]

        # perform performances if needed
        performances = {}
        for player in (player_A, player_B):
            performance_file = f"data/competitions/{tournament_state['meta']['competition']}/performances/{_get_performance_id(challenge_name, player['name'])}.json"
            if not os.path.exists(performance_file):
                # create the performance
                print(f"      rendering performance of {player['name']} for {challenge_name}")
                performances[player["name"]] = {
                    "player": player["name"],
                    "challenge": challenge,
                    "output": complete(
                        player["model"],
                        player["temperature"],
                        player["prompt"].format(**challenge),
                    ),
                }

                # store the performance
                with open(performance_file, "w") as file:
                    json.dump(performances[player["name"]], file, indent=2)
            else:
                # load the performance
                with open(performance_file, "r") as file:
                    performances[player["name"]] = json.load(file)

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
            f"data/competitions/{tournament_state['meta']['competition']}/tournaments/{tournament_state['meta']['tournament']}/matches/{id}.json",
            "w",
        ) as file:
            json.dump(match, file, indent=2)

        # update leaderboard
        update_leaderboard(tournament_state, match)

    # store the match
    save_tournament(tournament_state)
