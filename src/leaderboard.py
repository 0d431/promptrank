import json


##############################################
def generate_leaderboard(tournament_state, initial_elo=1000.0):
    """Generate the current leaderboard from the match history"""

    tournament_state["leaderboard"] = {}

    for player in tournament_state["players"]:
        # set up initial leaderboard entry for new player
        tournament_state["leaderboard"][player] = {
            "elo": initial_elo,
            "elo_history": [],
            "k_factor": 50.0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "matches": 0,
        }

    # re-play match history
    for _id, match in tournament_state["matches"].items():
        update_leaderboard(tournament_state, match, False)

    # now save
    save_leaderboard(tournament_state)


##############################################
def save_leaderboard(tournament_state):
    """Persist the updated matches and the leaderboard"""

    competition = tournament_state["meta"]["competition"]
    tournament = tournament_state["meta"]["tournament"]

    # write the leaderboard ordered by descending elo
    with open(
        f"competitions/{competition}/tournaments/{tournament}/leaderboard.json",
        "w",
    ) as file:
        json.dump(
            tournament_state["leaderboard"],
            file,
            indent=2,
        )


##############################################
def update_leaderboard(tournament_state, match, save=True):
    """Update the leaderboard based on a match"""

    # get player names
    player_A_name = match["player_A"]["name"]
    player_B_name = match["player_B"]["name"]
    winner_name = match["result"]["winner"]

    # skip Did Not Play matches
    if winner_name == "DNP":
        return

    # get player stats
    player_A_stats = tournament_state["leaderboard"][player_A_name]
    player_B_stats = tournament_state["leaderboard"][player_B_name]

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

    # finally re-calc K factor based on number of matches
    def _calc_k(matches):
        return max(50.0 / (1 + 0.1 * max(0, (matches - 20))), 10.0)

    player_A_stats["k_factor"] = _calc_k(player_A_stats["matches"])
    player_B_stats["k_factor"] = _calc_k(player_B_stats["matches"])

    # re-sort the leaderboard by ELO score desc
    tournament_state["leaderboard"] = dict(
        sorted(
            tournament_state["leaderboard"].items(),
            key=lambda x: x[1]["elo"],
            reverse=True,
        )
    )

    # store leaderboard
    if save:
        save_leaderboard(tournament_state)

    # return updated stats
    return player_A_stats, player_B_stats
