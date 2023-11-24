import os
import math
import random
from play.duel import play
from .invent import invent_player
from .enhance import enhance_player
from .merge import merge_players
from analyze.analyze import analyze_tournaments


# The number of matches for full evaluation
FULL_SEASON_MATCHES = 25

# The number of initial matches during initial audition against the refernce player
INITIAL_AUDITION_MATCHES = 12

# Winners per season
WINNERS_PER_SEASON = 4

# Initial challengers per season
CHALLENGERS_PER_SEASON = 12

# Surviving challengers per season
SURVIVING_CHALLENGERS_PER_SEASON = 4

# The model for new inventions
INVENTION_MODELS = ["gpt-3.5-turbo-instruct"]

# The temperature for new inventions
INVENTION_TEMPERATURE = 0.0


##############################################
def _collect_winners(tournaments, reference_player, number_of_winners):
    """Collect the best players from each tournament, plus the best balanced players to reach desired number of winners"""

    player_set = next(iter(tournaments.values()))["meta"]["player_set"]
    print(
        f"Determining {number_of_winners} winners from player set {player_set.upper()} across {len(tournaments)} tournaments..."
    )

    # scan all tournaments, fetch best players and tally balanced scores across tournaments
    winners = set()
    balanced_scores = {}
    for tournament in tournaments.values():
        # collect player -> score map
        scores = {
            p: tournament["leaderboard"][p]["score"]
            for p in tournament["players"]
            if p != reference_player
        }

        # get the best player
        winner = max(scores, key=scores.get)
        winners.add(winner)
        print(
            f"   {winner} won tournament {tournament['meta']['tournament']} with score {scores[winner]:.2f}"
        )

        # calculate balanced score as the harmonic mean of the score per tournament
        for player, score in scores.items():
            if player not in balanced_scores:
                balanced_scores[player] = 1.0

            balanced_scores[player] *= score

    # complete
    balanced_scores = {
        player: math.pow(score, 1.0 / len(tournaments))
        for player, score in balanced_scores.items()
    }
    best_balanced_player = max(balanced_scores, key=balanced_scores.get)
    print(f"   Best balanced player is {best_balanced_player} with balanced score {balanced_scores[best_balanced_player]:.2f}")

    # fetch the best balanced players to reach N winners
    while len(winners) < number_of_winners and len(balanced_scores) > 0:
        winner = max(balanced_scores, key=balanced_scores.get)
        if winner not in winners:
            winner_score = balanced_scores[winner]

            # only consider players that are above 50% balanced score
            if winner_score > 0.4:
                winners.add(winner)
                print(f"   {winner} achieved top balanced score {winner_score:.2f}")

        del balanced_scores[winner]

    return list(winners)[:number_of_winners], best_balanced_player


##############################################
def _create_challengers(
    tournaments,
    season,
    previous_season_winners,
    reference_player,
    challenger_player_set,
):
    """Create new challenger players based on the winners."""

    # first, 20% new players through invention
    number_of_inventions = int(0.2 * CHALLENGERS_PER_SEASON)
    invented_players = invent_player(
        tournaments,
        random.choice(INVENTION_MODELS),
        INVENTION_TEMPERATURE,
        season,
        number_of_inventions,
    )

    # now, 40% through enhancement
    number_of_enhancements = int(0.4 * CHALLENGERS_PER_SEASON)
    enhanced_players = []
    for _ in range(number_of_enhancements):
        enhanced_players.extend(
            enhance_player(
                tournaments,
                random.choice(previous_season_winners),
                season,
            )
        )

    # finally, generate the rest through merging
    number_of_merges = (
        CHALLENGERS_PER_SEASON - number_of_inventions - number_of_enhancements
    )
    merged_players = []
    for _ in range(number_of_merges):
        merged_players.extend(
            merge_players(
                tournaments,
                random.choice(previous_season_winners),
                random.choice(previous_season_winners),
                season,
            )
        )

    # now, create the challenger player set
    playerset_filename = f"competitions/{next(iter(tournaments.values()))['meta']['competition']['name']}/player_sets/{challenger_player_set}.players"
    os.makedirs(os.path.dirname(playerset_filename), exist_ok=True)

    with open(playerset_filename, "w") as f:
        f.write(
            "\n".join(
                [
                    f"{p}.yaml"
                    for p in invented_players
                    + enhanced_players
                    + merged_players
                    + [reference_player]
                ]
            )
        )


##############################################
def _cull_challengers(
    auditions,
    previous_season_winners,
    challenger_player,
    reference_player,
    full_season_player_set,
):
    """Cull the underperforming challengers and create the full season player set."""

    # collect the audition winners
    audition_winners, _best_balanced_performer = _collect_winners(
        auditions, challenger_player, SURVIVING_CHALLENGERS_PER_SEASON
    )

    # now, create the full season player set
    playerset_filename = f"competitions/{next(iter(auditions.values()))['meta']['competition']['name']}/player_sets/{full_season_player_set}.players"
    os.makedirs(os.path.dirname(playerset_filename), exist_ok=True)

    with open(playerset_filename, "w") as f:
        f.write(
            "\n".join(
                [
                    f"{p}.yaml"
                    for p in audition_winners
                    + previous_season_winners
                    + [reference_player]
                ]
            )
        )


##############################################
def evolve_season(competition, player_set, reference_player):
    """Evolve player set based on the last season's winners."""

    # find the latest season
    matching_sets = [
        ps
        for ps in os.listdir(f"competitions/{competition}/player_sets/")
        if ps.startswith(f"{player_set}-S")
        and ps.endswith(".players")
        and not ps.endswith("-challengers.players")
    ]

    season = 0
    if matching_sets:
        season = max(int(file.split("-S")[1][:2]) for file in matching_sets)
        print(f"Found latest season {season:02d}")

    this_season_player_set = f"{player_set}-S{season:02d}" if season > 0 else player_set
    new_season_player_set = f"{player_set}-S{season+1:02d}"

    # make sure all tournaments are fully played
    tournaments = play(competition, "", this_season_player_set, FULL_SEASON_MATCHES)
    analyze_tournaments(tournaments, False)

    # collect the winners of the season
    season_winners, best_balanced_player = _collect_winners(
        tournaments, reference_player, WINNERS_PER_SEASON
    )

    # finish season and create challengers, unless that has been done already
    challenger_player_set = f"{new_season_player_set}-challengers"
    if not os.path.exists(
        f"competitions/{competition}/player_sets/{challenger_player_set}.players"
    ):
        # create new players through merging, invention, and enhancement
        _create_challengers(
            tournaments,
            new_season_player_set + "/",
            season_winners,
            best_balanced_player,
            challenger_player_set,
        )
    else:
        print(f"Continuing audition for player set {challenger_player_set}...")

    # play the initial audition
    auditions = play(
        competition,
        "",
        challenger_player_set,
        INITIAL_AUDITION_MATCHES,
        best_balanced_player,
    )
    analyze_tournaments(auditions, False)


    # now cull underperformes from audition and create the full season player set
    _cull_challengers(
        auditions,
        season_winners,
        best_balanced_player,
        reference_player,
        new_season_player_set,
    )

    print(f"Prepared evolved next season on player set {new_season_player_set}.")
