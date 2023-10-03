import json
import random
import numpy as np

INITIAL_K = 10.0
FINAL_K = 1.0
INITIAL_MATCHES = 10
TRANSITION_MATCHES = 50


##############################################
def generate_leaderboard(tournament, initial_elo=1000.0):
    """Generate the current leaderboard from the match history"""

    tournament["leaderboard"] = {}

    for player in tournament["players"]:
        # set up initial leaderboard entry for new player
        tournament["leaderboard"][player] = {
            "elo": initial_elo,
            "elo_history": [],
            "score": 0.5,
            "score_history": [],
            "k_factor": INITIAL_K,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "matches": 0,
        }

    # re-play match history
    matches = list(tournament["matches"].values())
    random.shuffle(matches)
    for match in matches:
        update_leaderboard(tournament, match, False)

    # now save
    save_leaderboard(tournament)


##############################################
def save_leaderboard(tournament):
    """Persist the updated matches and the leaderboard"""

    competition = tournament["meta"]["competition"]["name"]
    tournament_name = tournament["meta"]["tournament"]

    # write the leaderboard ordered by descending elo
    with open(
        f"competitions/{competition}/tournaments/{tournament_name}/leaderboard.json",
        "w",
    ) as file:
        json.dump(
            tournament["leaderboard"],
            file,
            indent=2,
        )


##############################################
def update_leaderboard(tournament, match, save=True):
    """Update the leaderboard based on a match"""

    # get player names
    player_A_name = match["player_A"]["name"]
    player_B_name = match["player_B"]["name"]
    winner_name = match["result"]["winner"]

    # skip Did Not Play matches
    if winner_name == "DNP":
        return

    # get player stats
    player_A_stats = tournament["leaderboard"][player_A_name]
    player_B_stats = tournament["leaderboard"][player_B_name]

    # get current elos & k-factor, pre-match
    player_A_elo = player_A_stats["elo"]
    player_B_elo = player_B_stats["elo"]
    player_A_k_factor = player_A_stats["k_factor"]
    player_B_k_factor = player_B_stats["k_factor"]

    # calculate expected performance
    player_A_expected = 1.0 / (1.0 + pow(10.0, (player_B_elo - player_A_elo) / 400.0))
    player_B_expected = 1.0 / (1.0 + pow(10.0, (player_A_elo - player_B_elo) / 400.0))

    # update the player's performance
    player_A_actual = player_B_actual = None

    player_A_stats["matches"] += 1
    player_B_stats["matches"] += 1

    if winner_name == player_A_name:
        player_A_actual = 1.0
        player_A_stats["wins"] += 1

        player_B_actual = 0.0
        player_B_stats["losses"] += 1
    elif winner_name == player_B_name:
        player_A_actual = 0.0
        player_A_stats["losses"] += 1

        player_B_actual = 1.0
        player_B_stats["wins"] += 1
    else:
        player_A_actual = 0.5
        player_A_stats["draws"] += 1

        player_B_actual = 0.5
        player_B_stats["draws"] += 1

    # update elo
    player_A_stats["elo_history"].append(player_A_elo)
    player_A_stats["elo"] += player_A_k_factor * (player_A_actual - player_A_expected)
    player_B_stats["elo_history"].append(player_B_elo)
    player_B_stats["elo"] += player_B_k_factor * (player_B_actual - player_B_expected)

    # re-calc K factor based on number of matches
    def _calc_k(matches):
        return max(
            INITIAL_K
            / (1 + 10.0 / TRANSITION_MATCHES * max(0, (matches - INITIAL_MATCHES))),
            FINAL_K,
        )

    player_A_stats["k_factor"] = _calc_k(player_A_stats["matches"])
    player_B_stats["k_factor"] = _calc_k(player_B_stats["matches"])

    # update score
    player_A_stats["score_history"].append(player_A_stats["score"])
    player_A_stats["score"] = (
        1.0 * player_A_stats["wins"] + 0.5 * player_A_stats["draws"]
    ) / player_A_stats["matches"]
    player_B_stats["score_history"].append(player_B_stats["score"])
    player_B_stats["score"] = (
        1.0 * player_B_stats["wins"] + 0.5 * player_B_stats["draws"]
    ) / player_B_stats["matches"]

    # re-sort the leaderboard by score desc
    tournament["leaderboard"] = dict(
        sorted(
            tournament["leaderboard"].items(),
            key=lambda x: x[1]["score"],
            reverse=True,
        )
    )

    # calc aggregate stats
    scores = [
        tournament["leaderboard"][player_name]["score"]
        for player_name in tournament["leaderboard"]
    ]

    tournament["stats"] = {
        "median": np.median(scores),
        "average": np.mean(scores),
        "stddev": np.std(scores),
    }

    # store leaderboard
    if save:
        save_leaderboard(tournament)

    # return updated stats
    return player_A_stats, player_B_stats
