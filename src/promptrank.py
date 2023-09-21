import dotenv

dotenv.load_dotenv()

import os
import argparse
from match import run_match
from tournament import load_tournament
from analyze import (
    analyze_players,
    plot_elo_history,
    plot_score_history,
    plot_score_matrix,
)


def play(competition, tournament, players, number_matches):
    """Play a number of matches."""

    tournament_state = load_tournament(competition, tournament, players)

    while True:
        min_played = run_match(tournament_state, number_matches)

        if min_played == number_matches:
            print(f"All pairs have played at least {number_matches} matches; stopping")
            break

        print(
            f"\nPlayed match {len(tournament_state['matches']) + 1}/{tournament_state['meta']['pairings']} - {min_played:.0f} matches played by all pairs"
        )

    print(
        f"\nDone - {tournament_state['meta']['pairings'] - len(tournament_state['matches'])} matches left to play"
    )


def analyze(competition, tournament, players, skip_critique, write_file):
    """Analyze player performance."""

    tournament_state = load_tournament(competition, tournament, players)

    player_set = tournament_state["meta"]["player_set"]
    if player_set == "":
        player_set = "all"

    print(f"\nAnalyzing {len(tournament_state['players'])} players")
    dump, _analysis = analyze_players(tournament_state, skip_critique)

    if write_file:
        path = (
            f"competitions/{competition}/tournaments/{tournament}/analysis/{player_set}"
        )
        if not os.path.exists(path):
            os.makedirs(path)

        with open(f"{path}/analysis.md", "w") as f:
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
    else:
        print(dump)


def main():
    """Command-line interface."""

    parser = argparse.ArgumentParser(description="Promptrank Command-Line Interface")
    parser.add_argument("competition", type=str, help="Name of the competition.")
    parser.add_argument("tournament", type=str, help="Name of the tournament.")
    parser.add_argument(
        "players",
        type=str,
        help="Name of the player set file (optional).",
        nargs="?",
        default="",
    )

    subparsers = parser.add_subparsers(dest="command")

    # 'play' command parser
    play_parser = subparsers.add_parser("play", help="Play matches.")
    play_parser.add_argument(
        "-n", "--number", type=int, default=1, help="Number of matches to play."
    )

    # 'analyze' command parser
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze player performance."
    )
    analyze_parser.add_argument(
        "-s",
        "--skip_critique",
        action="store_true",
        help="If set, skips analysis of strengths and weaknesses.",
    )
    analyze_parser.add_argument(
        "-w",
        "--write_file",
        action="store_true",
        help="If set, write analysis to analysis.md in tournament directory.",
    )

    args = parser.parse_args()

    if args.command == "play":
        play(args.competition, args.tournament, args.players, args.number)
    elif args.command == "analyze":
        analyze(
            args.competition,
            args.tournament,
            args.players,
            args.skip_critique,
            args.write_file,
        )
    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    main()
