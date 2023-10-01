import random
from match import play
from analyze import analyze_players
from .helper import generate_random_id
from .invent import invent_player
from .enhance import enhance_player
from .merge import merge_players


# The number of matches for full evaluation
FULL_SEASON_MATCHES = 12

# The number of initial matches during initial audition against the refernce player
INITIAL_AUDITION_MATCHES = 10

# Winners per season
WINNERS_PER_SEASON = 4

# Initial challengers per season
CHALLENGERS_PER_SEASON = 10

# Surviving challengers per season
SURVIVING_CHALLENGERS_PER_SEASON = 4

# The model for new inventions
INVENTION_MODEL = "gpt-3.5-turbo"

# The temperature for new inventions
INVENTION_TEMPERATURE = 0.0


##############################################
def _collect_winners(tournaments, reference_player, number_of_winners):
    """Collect the best players from each tournament, plus the best balanced players to reach N winners"""

    season_results = {}
    print(
        f"Determining {number_of_winners} winners across {len(tournaments)} tournaments..."
    )

    # scan all tournaments
    for tournament in tournaments:
        # get overall analysis of the tournament
        _, analysis = analyze_players(tournament, skip_critique=True)

        # discard the reference player
        analysis.pop(reference_player)

        season_results[tournament["meta"]["name"]] = analysis

    # fetch the best players from each tournament
    winners = set()
    for tournament, analysis in season_results.items():
        # get the best players
        winners.add(analysis.keys()[0])
        print(
            f"   {analysis.keys()[0]} won tournament {tournament} with score {analysis.values()[0]['score']:.2f}"
        )

    # calculate balanced score as the harmonic mean of the score per tournament
    balanced_scores = {}
    for _tournament, analysis in season_results.items():
        for player, analysis in analysis.items():
            if player not in balanced_scores:
                balanced_scores[player] = 0.0

            balanced_scores[player] += 1.0 / analysis["score"]

    balanced_scores = {player: 1.0 / score for player, score in balanced_scores.items()}

    # sort by balanced score
    balanced_scores = {
        player: score
        for player, score in sorted(
            balanced_scores.items(), key=lambda item: item[1], reverse=True
        )
    }

    # fetch the best balanced players to reach N winners
    while len(winners) < number_of_winners and len(balanced_scores) > 0:
        winners.add(balanced_scores.keys()[0])
        print(
            f"   {balanced_scores.keys()[0]} with top balanced score {balanced_scores.values()[0]:.2f}"
        )
        balanced_scores.pop(balanced_scores.keys()[0])

    return list(winners)[:number_of_winners]


##############################################
def _create_challengers(
    competition,
    player_set,
    previous_season_winners,
    reference_player,
    challenger_player_set,
):
    """Create new challenger players based on the winners."""

    # create a season id for players
    season_id = generate_random_id()

    # first, 20% new players through invention
    number_of_inventions = int(0.2 * len(previous_season_winners))
    invented_players = invent_player(
        competition,
        INVENTION_MODEL,
        INVENTION_TEMPERATURE,
        season_id,
        number_of_inventions,
    )

    # now, 40% through enhancement
    number_of_enhancements = int(0.4 * len(previous_season_winners))
    enhanced_players = []
    for _ in range(number_of_enhancements):
        enhanced_players.append(
            enhance_player(
                competition,
                player_set,
                random.choice(previous_season_winners),
                season_id,
            )
        )

    # finally, generate the rest through merging
    number_of_merges = (
        len(previous_season_winners) - number_of_inventions - number_of_enhancements
    )
    merged_players = []
    for _ in range(number_of_merges):
        merged_players.append(
            merge_players(
                competition,
                player_set,
                random.choice(previous_season_winners),
                random.choice(previous_season_winners),
                season_id,
            )
        )

    # now, create the challenger player set
    with open(
        f"competitions/{competition}/players/{challenger_player_set}.players", "w"
    ) as f:
        f.write(
            "\n".join(
                invented_players
                + enhanced_players
                + merged_players
                + [reference_player]
            )
        )


##############################################
def _cull_challengers(
    auditions, previous_season_winners, reference_player, full_season_player_set
):
    """Cull the underperforming challengers and create the full season player set."""

    # collect the audition winners
    audition_winners = _collect_winners(
        auditions, reference_player, SURVIVING_CHALLENGERS_PER_SEASON
    )

    # now, create the full season player set
    with open(
        f"competitions/{auditions.values()[0]['meta']['competition_name']}/players/{full_season_player_set}.players",
        "w",
    ) as f:
        f.write(
            "\n".join(audition_winners + previous_season_winners + [reference_player])
        )


##############################################
def evolve_season(competition, player_set, reference_player):
    # determine the base player set name and the current season
    parts = player_set.rsplit("-S", 1)
    if len(parts) == 1:
        base_player_set = player_set
        season = 0
    else:
        base_player_set = parts[0]
        season = int(parts[1])

    # make sure all tournaments are fully played
    tournaments = play(competition, "", player_set, FULL_SEASON_MATCHES)

    # collect the winners of the season
    season_winners = _collect_winners(tournaments, reference_player, WINNERS_PER_SEASON)

    # get the new season's id
    new_season_player_set = f"{base_player_set}-S{season+1:02d}"

    # create new players through merging, invention, and enhancement, returning the challenger player set name
    challenger_player_set = f"{new_season_player_set}-challengers"
    _create_challengers(
        tournaments, player_set, season_winners, reference_player, challenger_player_set
    )

    # play the initial audition
    auditions = play(
        competition,
        "",
        challenger_player_set,
        INITIAL_AUDITION_MATCHES,
        reference_player,
    )

    # now cull underperformes from audition and create the full season player set
    _cull_challengers(
        auditions, reference_player, season_winners, new_season_player_set
    )

    print(f"Prepared evolved next season on player set {new_season_player_set}.")
