from src.competition.loader import load_tournament, resolve_tournaments
from src.play.match import play_next_matches
from src.play.grade import grade_next_performances


##############################################
def play(competition, tournament_name, player_set, number_games, player_name=None):
    """Play until each player pair has played the given number of matches."""

    objective = f"against {player_name}" if player_name else "for all player pairs"

    tournaments = {}
    for tournament_name in resolve_tournaments(competition, tournament_name):
        # load the tournament
        tournament = load_tournament(competition, tournament_name, player_set)
        tournaments[tournament_name] = tournament

        # does this tournament have a competitive evaluation?
        if tournament["comparison"] is not None:
            # yes, so we play matches until each player pair has played the given number of matches
            print(
                f"Playing {number_games} matches {objective} in player set {player_set.upper()} for tournament {tournament_name.upper()}..."
            )

            while True:
                min_matches_all_players = play_next_matches(
                    tournament, number_games, player_name, 10
                )
                print(
                    f"    {tournament_name.upper()} - {len(tournament['matches'])} matches played; {min_matches_all_players:.0f}/{number_games} {objective}"
                )
                if min_matches_all_players >= number_games:
                    break

        # does the tournament have a grading evaluation?
        if tournament["grading"] is not None:
            # yes, so we grade players until we have given performances covered
            number_grades = number_games
            if tournament["comparison"] is not None:
                # we had pairwise matches, so we grade all pair performances
                number_grades *= (
                    len(tournament["players"]) * (len(tournament["players"]) - 1) / 2
                )

            print(
                f"Grading {number_grades} performances in player set {player_set.upper()} for tournament {tournament_name.upper()}..."
            )

            while True:
                min_performances_all_players = grade_next_performances(
                    tournament, number_grades, 10
                )
                print(
                    f"    {tournament_name.upper()} - {len(tournament['grades'])} performances graded; {min_performances_all_players:.0f}/{number_grades}"
                )
                if min_performances_all_players >= number_grades:
                    break

    return tournaments
