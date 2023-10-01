import dotenv

dotenv.load_dotenv()

import argparse
from analyze import analyze
from evolve.evolve import evolve_season
from match import play


def _build_parser():
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description="Promptrank Command-Line Interface")
    parser.add_argument("competition", type=str, help="Name of the competition.")
    parser.add_argument(
        "-t",
        "--tournament",
        type=str,
        help="Name of the tournament (optional; if not given, all tournaments are played)",
        nargs="?",
        default="",
    )
    parser.add_argument(
        "-p",
        "--players",
        type=str,
        help="Name of the player set file (optional; if not given, all players are used)",
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

    # 'evolve' command parser
    evolve_parser = subparsers.add_parser(
        "evolve",
        help="Play mutiple seasons to evolve the best players from all tournaments.",
    )
    evolve_parser.add_argument(
        "-r",
        "--reference_player",
        type=str,
        nargs=1,
        help="Name of the referenec player for initial auditions.",
    )

    return parser


def main():
    """Command-line interface."""

    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "play":
        play(args.competition, args.tournament, args.players, args.number)
    elif args.command == "analyze":
        analyze(args.competition, args.tournament, args.players, args.skip_critique)
    elif args.command == "evolve":
        evolve_season(args.competition, args.players, args.reference_player)
    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    main()
