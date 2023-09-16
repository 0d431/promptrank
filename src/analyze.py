import random
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from llm import complete

##############################################
ASSESSMENT_PROMPT = """The player {player} is participating in a tournament with the aim to {objective}. The player has received the following assessments of their performance against opponents in their matches:

{assessments}

Silently analyze the performance of the player {player} across all these assessments. Then write one sentence to chacterise the key strengths of the player. Then add a bullet list with up to three, very detailed weaknesses of the player:"""


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
    analysis = dict(sorted(analysis.items(), key=lambda x: x[1]["elo"], reverse=True))

    # dump as markdown
    dump = f"\n# {tournament_state['meta']['competition'].upper()} competition\n"
    dump += f"## {tournament_state['meta']['tournament'].upper()} tournament\n"
    dump += f"{len(tournament_state['players'])} players, {len(tournament_state['challenges'])} challenges, "
    dump += f"{len(tournament_state['matches'])} out of {tournament_state['meta']['pairings']} matches played\n"
    dump += "\n| Player | ELO | Score | Analysis |\n|---|---|---|---|\n"
    for player_name, player_analysis in analysis.items():
        dump += f"**{player_name}**|{player_analysis['elo']}|{player_analysis['score']}|{player_analysis['analysis']}|\n"

    return dump, analysis


def plot_elo_history(tournament_state, output_file):
    """Plot the ELO history of all players."""

    # extract ELO history
    elo_history = {
        k: v["elo_history"] for k, v in tournament_state["leaderboard"].items()
    }

    # find the length of the longest series
    max_length = max(len(series) for series in elo_history.values())

    # pad the shorter series with NaN values
    padded_data = {
        label: np.pad(
            series, (0, max_length - len(series)), "constant", constant_values=np.nan
        )
        for label, series in elo_history.items()
    }

    # convert dictionary to DataFrame
    df = pd.DataFrame(padded_data)

    # set up the figure and axes
    _fig, ax = plt.subplots(figsize=(12, 8))

    # plot using Seaborn with explicit line styles
    for column in tournament_state["leaderboard"].keys():
        sns.lineplot(data=df[column], ax=ax, label=column, linestyle='-', errorbar=None)

    # adjust the plot area to make room for the legend
    plt.subplots_adjust(right=0.8)

    # customize the chart
    ax.set_xlabel("Match")
    ax.set_ylabel("ELO")
    ax.set_title("ELO score evolution")
    ax.legend(df.columns, bbox_to_anchor=(1.01, 1.01), loc='upper left')

    # Save the chart as a PNG file
    plt.savefig(output_file)
    plt.close()
