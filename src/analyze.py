import random
from llm import complete

##############################################
ASSESSMENT_PROMPT = """The player {player} is participating in a tournament with the aim to {objective}. The player has received the following assessments of their performance against opponents in their matches:

{assessments}

Summarize the key strengths and weaknesses of {player} across all these assessments in a bullet list of at most 3 items:"""


def _analyze_player(tournament_state, player_name):
    """Evaluate the strengths and weaknesses of a player"""

    # collect assessments
    assessments = []

    for match in tournament_state["matches"].values():
        if match["result"]["winner"] in ("DRAW", "DNP"):
            continue

        assessment = match["result"]["assessment"]
        if match["player_A"]["name"] == player_name:
            assessment = assessment.replace("Player A", player_name)
            assessment = assessment.replace("Player B", "the opponent")
        elif match["player_B"]["name"] == player_name:
            assessment = assessment.replace("Player A", "the opponent")
            assessment = assessment.replace("Player B", player_name)
        else:
            # not a match involving this player
            continue

        assessments.append(assessment)

    # evaluate
    if len(assessments) > 0:
        random.shuffle(assessments)
        assessment = assessment[:50]

        return complete(
            "gpt-4",
            0.2,
            prompt=ASSESSMENT_PROMPT.format(
                player=player_name,
                assessments="\n".join(["- " + a for a in assessments]),
                objective=tournament_state["evaluation"]["objective"],
            ),
        )

    return "n/a"


def analyze_players(tournament_state):
    """Evaluate the strengths and weaknesses of all players"""

    analysis = {}
    for player_name in tournament_state["players"]:
        print(f"    {player_name}")
        analysis[player_name] = {
            "elo": int(tournament_state["leaderboard"][player_name]["elo"]),
            "score": f"{tournament_state['leaderboard'][player_name]['wins']}-{tournament_state['leaderboard'][player_name]['draws']}-{tournament_state['leaderboard'][player_name]['losses']}",
            "analysis": _analyze_player(tournament_state, player_name).replace(
                "\n", "<br>"
            ),
        }

    # sort by elo
    analysis = dict(
        sorted(analysis.items(), key=lambda x: x[1]["elo"], reverse=True)
    )

    # dump as markdown
    dump = "\n| Player | ELO | Score | Analysis |\n|---|---|---|---|\n"
    for player_name, player_analysis in analysis.items():
        dump += f"|{player_name}|{player_analysis['elo']}|{player_analysis['score']}|{player_analysis['analysis']}|\n"


    return dump, analysis