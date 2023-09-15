import os
import argparse

import dotenv

dotenv.load_dotenv()

from match import run_match
from tournament import load_tournament
from analyze import analyze_players


def play(competition, tournament, number_matches):
    """Play a number of matches."""

    tournament_state = load_tournament(competition, tournament)

    for _i in range(number_matches):
        print(f"\nPlaying match {_i + 1}/{number_matches}")
        run_match(tournament_state)

    print(
        f"\nDone - {tournament_state['meta']['pairings'] - len(tournament_state['matches'])} matches left to play"
    )


def analyze(competition, tournament):
    """Analyze player performance."""


    tournament_state = load_tournament(competition, tournament)
    print(f"\nAnalyzing {len(tournament_state['players'])} players")

    dump, _analysis = analyze_players(tournament_state)
    print(dump)


def main():
    parser = argparse.ArgumentParser(description="Promptrank Command-Line Interface")
    parser.add_argument("competition", type=str, help="Name of the competition.")
    parser.add_argument("tournament", type=str, help="Name of the tournament.")

    subparsers = parser.add_subparsers(dest="command")

    # 'play' command parser
    play_parser = subparsers.add_parser("play", help="Play matches.")
    play_parser.add_argument(
        "-n", "--number", type=int, default=1, help="Number of matches to play."
    )

    # 'analyze' command parser
    subparsers.add_parser("analyze", help="Analyze player performance.")

    args = parser.parse_args()

    if args.command == "play":
        play(args.competition, args.tournament, args.number)
    elif args.command == "analyze":
        analyze(args.competition, args.tournament)
    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    main()
