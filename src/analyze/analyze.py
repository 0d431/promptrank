import os
import math
import random
import warnings
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from llm import complete
from analyze.elo import calculate_winning_likelihoods, estimate_elo
from src.competition.loader import load_tournaments

warnings.simplefilter(action="ignore", category=FutureWarning)

CRITIQUE_MODEL = "gpt-4-1106-preview"

##############################################
CRITIQUE_PROMPT = """The player {player} is participating in a tournament with the aim to {objective}. The player has received the following assessments of their performance against opponents in their matches:

{assessments}

Silently analyze the performance of the player {player} across all these assessments. 

Then, firstly, give a detailed and highly specific assessment of the strengths of the player in a bullet list. 

Then, secondly, giuve a detailed and highly specific assessment of the weaknesses of the player in a bullet list.

Provide your response in like this:

STRENGTHS:
- ...
- ...
- ...

WEAKNESSES:
- ...
- ...
- ...

Now, it is time to provide your response."""


##############################################
def get_player_critique(tournament, player_name, do_critique):
    """Evaluate the strengths and weaknesses of a player"""

    if not do_critique:
        return "n/a"

    if "critiques" in tournament and player_name in tournament["critiques"]:
        return tournament["critiques"][player_name]

    # collect assessments
    assessments = []

    for match in tournament["matches"].values():
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

        critique = complete(
            CRITIQUE_MODEL,
            1.0,
            prompt=CRITIQUE_PROMPT.format(
                player=player_name,
                assessments="\n".join(["- " + a for a in assessments]),
                objective=tournament["evaluation"]["objective"],
            ),
        )
    else:
        critique = "n/a"

    tournament.get("critiques", {})[player_name] = critique
    return critique


##############################################
def _generate_tournament_analysis(tournament, do_critique):
    """Generate a markdown analysis of the tournament."""

    leaderboard = tournament["leaderboard"]

    median = tournament["stats"]["median"]
    average = tournament["stats"]["average"]
    stddev = tournament["stats"]["stddev"]

    # estimate ELO
    elo, loss = estimate_elo(*calculate_winning_likelihoods(list(leaderboard.keys()), tournament["matches"].values()))
    elo = { player_name: elo[i] for i, player_name in enumerate(leaderboard.keys()) }
    print(f"LOSS: {math.sqrt(loss):.3f}")

    # dump as markdown
    analysis = ""
    analysis = f"\n## {tournament['meta']['competition']['name'].capitalize()} / {tournament['meta'][TOURNAMENT].capitalize()} / {tournament['meta']['player_set']}\n"
    analysis += f"{len(tournament['players'])} players, {len(tournament['challenges'])} challenges, "
    analysis += f"{len(tournament['matches'])} out of {tournament['meta']['pairings']} matches played\n"
    analysis += (
        f"\nMedian {median:.2f}; average {average:.2f} +/- {stddev:.2f} stddev\n"
    )
    analysis += (
        "\n| Player | Score | Score Dev | ELO | Analysis |\n|---|---|---|---|---|\n"
    )
    for player_name, player_stat in leaderboard.items():
        score_stat = f"**{player_stat['score']:.2f}**: {player_stat['wins']}-{player_stat['draws']}-{player_stat['losses']}"
        analysis += f"**{player_name}**|{score_stat}|{(player_stat['score'] - average)/stddev:.1f}|{elo[player_name]:.0f}|{get_player_critique(tournament, player_name, do_critique)}|\n"

    return analysis


##############################################
def _generate_competition_analysis(tournaments):
    """Generate a markdown analysis of the entire competition."""

    # collect aggregated stats per tournament and player
    aggregated_stats = {}
    observed_probs = None
    observations = None
    player_names = list(next(iter(tournaments.values()))["players"])
    for tournament in tournaments.values():
        # does this tournament have a competitive evaluation?
        if tournament["comparison"] is None:
            # nope, skip
            continue

        leaderboard = tournament["leaderboard"]

        # estimate ELO
        tournament_OP, tournament_O = calculate_winning_likelihoods(player_names, tournament["matches"].values())
        if observed_probs is None:
            observed_probs = tournament_OP
            observations = tournament_O
        else:
            observed_probs += tournament_OP
            observations += tournament_O

        for player in leaderboard:
            if player not in aggregated_stats:
                aggregated_stats[player] = {
                    "score": 1.0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "matches": 0,
                }

            aggregated_stats[player]["score"] *= leaderboard[player]["score"]
            aggregated_stats[player]["wins"] += leaderboard[player]["wins"]
            aggregated_stats[player]["draws"] += leaderboard[player]["draws"]
            aggregated_stats[player]["losses"] += leaderboard[player]["losses"]
            aggregated_stats[player]["matches"] += leaderboard[player]["matches"]

    analysis = ""
    if len(aggregated_stats) > 0:
        # calculate balanced score as the geomtric mean of the score per tournament
        for player, stats in aggregated_stats.items():
            stats["score"] = math.pow(stats["score"], 1.0 / len(tournaments))

        # calc aggregate stats
        scores = [
            aggregated_stats[player_name]["score"] for player_name in aggregated_stats
        ]

        agg_median = np.median(scores)
        agg_average = np.mean(scores)
        agg_stddev = np.std(scores)

        # sort by score
        aggregated_stats = {
            k: v
            for k, v in sorted(
                aggregated_stats.items(), key=lambda item: item[1]["score"], reverse=True
            )
        }

        # get ELO
        elo, loss = estimate_elo(observed_probs/len(tournaments), observations)
        elo = { player_name: elo[i] for i, player_name in enumerate(player_names) }
        print(f"LOSS: {math.sqrt(loss):.3f}")


        # dump as markdown
        first_tournament = next(iter(tournaments.values()))

        analysis = f"\n## {first_tournament['meta']['competition']['name'].capitalize()} / {first_tournament['meta']['player_set']}\n"
        analysis += f"{len(tournaments)} tournaments: {', '.join(tournaments.keys())}\n"
        analysis += f"{len(first_tournament['players'])} players"
        analysis += f"\nMedian {agg_median:.2f}; average {agg_average:.2f} +/- {agg_stddev:.2f} stddev\n"

        analysis += "\n| Player | Total Score | Total Score Dev | ELO |"
        for tournament_name in tournaments:
            analysis += f" {tournament_name.capitalize()} Score | {tournament_name.capitalize()} Score Dev |"
        analysis += f"\n|---|---|---|---|{'---|'*2*len(tournaments)}\n"

        for player_name, player_stat in aggregated_stats.items():
            score_stat = f"**{player_stat['score']:.2f}**<br/>{player_stat['wins']}-{player_stat['draws']}-{player_stat['losses']}"
            analysis += f"**{player_name}**|{score_stat}|{(player_stat['score'] - agg_average)/agg_stddev:.1f}|{elo[player_name]:.0f}|"
            for tournament in tournaments.values():
                leaderboard = tournament["leaderboard"]
                score_stat = f"**{leaderboard[player_name]['score']:.2f}**<br/>{leaderboard[player_name]['wins']}-{leaderboard[player_name]['draws']}-{leaderboard[player_name]['losses']}"
                analysis += f"{score_stat}|{(leaderboard[player_name]['score'] - tournament['stats']['average'])/tournament['stats']['stddev']:.1f}|"
            analysis += "\n"

    return analysis


##############################################
def _plot_history(history, title, columns, axis_label, axis_min, axis_max, output_file):
    """Plot the history of all players."""

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
    for column in columns:
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



##############################################
def plot_score_history(leaderboard, output_file):
    """Plot the score history of all players."""
    _plot_history(
        {k: v["score_history"] for k, v in leaderboard.items()},
        "Score evolution",
        leaderboard.keys(),
        "ELO",
        0,
        1,
        output_file,
    )


##############################################
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


##############################################
def plot_score_matrix(players, matches, games_output_file, scores_output_file):
    """Plot a matrix of score stats of each player pair."""

    # Create a matrix of scores
    labels = list(players)
    matrix, match_count = calculate_winning_likelihoods(labels, matches)

    _plot_matrix(match_count, labels, "{value:.0f}", games_output_file)
    _plot_matrix(matrix, labels, "{value:.2f}", scores_output_file)


##############################################
def analyze_tournaments(tournaments, do_critique):
    """Analyze player performance for given tournaments."""

    competition = next(iter(tournaments.values()))["meta"]["competition"]["name"]

    # perform analysis per tournament
    for tournament in tournaments.values():
        # prepare output location
        player_set = tournament["meta"]["player_set"]
        tournament_name = tournament["meta"]["tournament"]

        path = f"competitions/{competition}/analysis/{player_set}"
        if not os.path.exists(path):
            os.makedirs(path)

        # does this tournament have a competitive evaluation?
        if tournament["comparison"] is not None:
            # obtain the analysis
            analysis = _generate_tournament_analysis(tournament, do_critique)

            with open(f"{path}/{tournament_name}.md", "w") as f:
                f.write(
                    analysis
                    + f"\n\n### Score History\n![Score History](./{tournament_name}-score-history.png)"
                    + f"\n\n### Score Matrix\n![Score Matrix](./{tournament_name}-score-matrix.png)"
                    + f"\n\n### Game Matrix\n![Game Matrix](./{tournament_name}-game-matrix.png)"
                )

            # plot histories
            plot_score_history(
                tournament["leaderboard"],
                f"{path}/{tournament_name}-score-history.png",
            )

            # plot score matrix
            plot_score_matrix(
                tournament["players"],
                tournament["matches"].values(),
                f"{path}/{tournament_name}-game-matrix.png",
                f"{path}/{tournament_name}-score-matrix.png",
            )

        # does this tournament have a grading evaluation?
        if tournament["grading"] is not None:
            # just export an excel with the grades
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Grades"
            
            for g in tournament["grades"].values():
                # write header
                if len(sheet["A"]) == 1:
                    sheet.append(["Player", "Grade", *g["challenge_details"].keys(), "Reasoning", "Output"])
                    
                sheet.append([g["player"]["name"], g["grade"], *g["challenge_details"].values(), g["reasoning"], g["player_output"]])

            workbook.save( f"{path}/{tournament_name}.xlsx")


    # now perform grand joint analysis
    with open(f"{path}/_analysis.md", "w") as f:
        f.write(_generate_competition_analysis(tournaments))


##############################################
def analyze(competition, tournament, player_set, do_critique):
    """Analyze player performance for a given competition."""
    analyze_tournaments(
        load_tournaments(competition, tournament, player_set), do_critique
    )
