import os
import random
import warnings
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from llm import complete
from tournament import load_tournament, resolve_tournaments

warnings.simplefilter(action='ignore', category=FutureWarning)

##############################################
ASSESSMENT_PROMPT = """The player {player} is participating in a tournament with the aim to {objective}. The player has received the following assessments of their performance against opponents in their matches:

{assessments}

Silently analyze the performance of the player {player} across all these assessments. Then write one sentence to chacterise the overall profile of the player. Then add a bullet list with up to three, very detailed weaknesses of the player:"""


def analyze_player(tournament_state, player_name):
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
        assessments = assessments[:50]

        return complete(
            "gpt-4",
            1.0,
            prompt=ASSESSMENT_PROMPT.format(
                player=player_name,
                assessments="\n".join(["- " + a for a in assessments]),
                objective=tournament_state["evaluation"]["objective"],
            ),
        )

    return "n/a"


def analyze_players(tournament_state, skip_critique):
    """Evaluate the strengths and weaknesses of all players"""

    analysis = {}
    for player_name in tournament_state["players"]:
        wins = tournament_state["leaderboard"][player_name]["wins"]
        draws = tournament_state["leaderboard"][player_name]["draws"]
        losses = tournament_state["leaderboard"][player_name]["losses"]

        if skip_critique:
            critique = "n/a"
        else:
            critique = analyze_player(tournament_state, player_name).replace(
                "\n", "<br>"
            )

        print(f"    {player_name}")
        analysis[player_name] = {
            "name": player_name,
            "elo": int(tournament_state["leaderboard"][player_name]["elo"]),
            "score": tournament_state["leaderboard"][player_name]["score"],
            "score_stat": f"**{tournament_state['leaderboard'][player_name]['score']:.2f}**: {wins}-{draws}-{losses}",
            "analysis": critique,
        }

    # sort by elo
    analysis = dict(sorted(analysis.items(), key=lambda x: x[1]["score"], reverse=True))

    # collect scores
    scores = [
        tournament_state["leaderboard"][player_name]["score"]
        for player_name in tournament_state["players"]
    ]
    median = np.median(scores)
    average = np.mean(scores)
    stddev = np.std(scores)

    # dump as markdown
    dump = f"\n## {tournament_state['meta']['competition'].capitalize()} / {tournament_state['meta']['tournament'].capitalize()} / {tournament_state['meta']['player_set']}\n"
    dump += f"{len(tournament_state['players'])} players, {len(tournament_state['challenges'])} challenges, "
    dump += f"{len(tournament_state['matches'])} out of {tournament_state['meta']['pairings']} matches played\n"
    dump += f"\nMedian {median:.2f}; average {average:.2f} +/- {stddev:.2f} stddev\n"
    dump += "\n| Player | Score | Score Dev | ELO | Analysis |\n|---|---|---|---|\n"
    for player_name, player_analysis in analysis.items():
        dump += f"**{player_name}**|{player_analysis['score_stat']}|{(player_analysis['score'] - average)/stddev:.1f}|{player_analysis['elo']}|{player_analysis['analysis']}|\n"

    return dump, analysis


def _plot_history(
    tournament_state, history_field, title, axis_label, axis_min, axis_max, output_file
):
    """Plot the history of all players."""

    # extract history
    history = {k: v[history_field] for k, v in tournament_state["leaderboard"].items()}

    # find the length of the longest series
    max_length = max(len(series) for series in history.values())

    # pad the shorter series with NaN values
    padded_data = {
        label: np.pad(
            series, (0, max_length - len(series)), "constant", constant_values=np.nan
        )
        for label, series in history.items()
    }

    # convert dictionary to DataFrame
    df = pd.DataFrame(padded_data)

    # set up the figure and axes
    _fig, ax = plt.subplots(figsize=(12, 8))

    # plot using Seaborn with explicit line styles
    for column in tournament_state["leaderboard"].keys():
        sns.lineplot(data=df[column], ax=ax, label=column, linestyle="-", errorbar=None)

    # adjust the plot area to make room for the legend
    plt.subplots_adjust(right=0.8)

    # customize the chart
    ax.set_xlabel("Match")
    ax.set_ylabel(axis_label)
    ax.set_title(title)
    ax.set_ylim(axis_min, axis_max)
    ax.legend(df.columns, bbox_to_anchor=(1.01, 1.01), loc="upper left")

    # Save the chart as a PNG file
    plt.savefig(output_file)
    plt.close()


def plot_elo_history(tournament_state, output_file):
    """Plot the ELO history of all players."""
    _plot_history(
        tournament_state, "elo_history", "ELO evolution", "ELO", 750, 1250, output_file
    )


def plot_score_history(tournament_state, output_file):
    """Plot the score history of all players."""
    _plot_history(
        tournament_state, "score_history", "Score evolution", "ELO", 0, 1, output_file
    )


def _plot_matrix(matrix, labels, fstring, output_file):
    """Plot a matrix of scores."""

    plt.figure(figsize=(10, 8))

    # Create a heatmap using Seaborn
    ax = sns.heatmap(
        matrix,
        annot=False,
        cmap="coolwarm",
        fmt=".2f",
        square=True,
        xticklabels=labels,
        yticklabels=labels,
    )

    # Add text annotations to the heatmap
    for i in range(len(labels)):
        for j in range(len(labels)):
            if i != j:
                ax.text(
                    j + 0.5,
                    i + 0.5,
                    fstring.format(value=matrix[i, j]),
                    ha="center",
                    va="center",
                )

    # Customize the plot
    plt.title("Score Matrix")
    plt.xticks(rotation=90, fontsize=7)
    plt.yticks(rotation=0, fontsize=7)

    # Save the chart as a PNG file
    plt.savefig(output_file)
    plt.close()


def plot_score_matrix(tournament_state, games_output_file, scores_output_file):
    """Plot a matrix of score stats of each player pair."""

    # Create a matrix of scores
    matrix = np.zeros(
        (len(tournament_state["players"]), len(tournament_state["players"]))
    )
    matches = np.zeros(
        (len(tournament_state["players"]), len(tournament_state["players"]))
    )

    labels = list(tournament_state["players"].keys())

    for match in tournament_state["matches"].values():
        player_A_name = match["player_A"]["name"]
        player_B_name = match["player_B"]["name"]

        if match["result"]["winner"] == "DRAW":
            matrix[labels.index(player_A_name), labels.index(player_B_name)] += 0.5
            matrix[labels.index(player_B_name), labels.index(player_A_name)] += 0.5
        elif match["result"]["winner"] == player_A_name:
            matrix[labels.index(player_A_name), labels.index(player_B_name)] += 1.0
        elif match["result"]["winner"] == player_B_name:
            matrix[labels.index(player_B_name), labels.index(player_A_name)] += 1.0
        else:
            # ignore DNP
            continue

        matches[labels.index(player_A_name), labels.index(player_B_name)] += 1
        matches[labels.index(player_B_name), labels.index(player_A_name)] += 1

    # divide matrix by number of matches
    matrix = np.divide(matrix, matches, out=np.zeros_like(matrix), where=matches != 0)

    _plot_matrix(matches, labels, "{value:.0f}", games_output_file)
    _plot_matrix(matrix, labels, "{value:.2f}", scores_output_file)


def analyze(competition, tournament, players, skip_critique):
    """Analyze player performance."""

    for tournament in resolve_tournaments(competition, tournament):
        print(f"Playing matches for tournament {tournament.upper()}...")

        tournament_state = load_tournament(competition, tournament, players)
        player_set = tournament_state["meta"]["player_set"]

        print(f"\nAnalyzing {len(tournament_state['players'])} players")
        dump, _analysis = analyze_players(tournament_state, skip_critique)

        path = (
            f"competitions/{competition}/tournaments/{tournament}/analysis/{player_set}"
        )
        if not os.path.exists(path):
            os.makedirs(path)

        with open(f"{path}/analysis-{player_set}.md", "w") as f:
            f.write(
                dump
                + "\n\n### ELO History\n![ELO History](./elo-history.png)"
                + "\n\n### Score History\n![Score History](./score-history.png)"
                + "\n\n### Score Matrix\n![Score Matrix](./score-matrix.png)"
                + "\n\n### Game Matrix\n![Game Matrix](./game-matrix.png)"
            )

        # plot histories
        plot_elo_history(
            tournament_state,
            f"{path}/elo-history.png",
        )
        plot_score_history(
            tournament_state,
            f"{path}/score-history.png",
        )

        # plot score matrix
        plot_score_matrix(
            tournament_state,
            f"{path}/game-matrix.png",
            f"{path}/score-matrix.png",
        )
