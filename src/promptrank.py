import dotenv

dotenv.load_dotenv()

import logging
import argparse
import datetime
from analyze.analyze import analyze_competition
from evolve.evolve import evolve_season
from play.duel import play, reevaluate_matches
from play.grade import grade_players


def _build_parser():
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description="Promptrank Command-Line Interface")
    parser.add_argument(
        "-c",
        "--competition",
        type=str,
        help="Name of the competition",
        required=True,
    )
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

    # 'grade' command parser
    grade_parser = subparsers.add_parser("grade", help="Grade players.")
    grade_parser.add_argument(
        "-n", "--number", type=int, default=1, help="Number of performances to rate."
    )

    # 'reevaluate' command parser
    reevaluate_parser = subparsers.add_parser("reevaluate", help="Re-evaluate matches.")

    # 'analyze' command parser
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze player performance."
    )
    analyze_parser.add_argument(
        "-q",
        "--critique",
        action="store_true",
        help="If set, generate critique of players' strengths and weaknesses.",
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
        help="Name of the referenec player for initial auditions.",
    )

    return parser


def main():
    """Command-line interface."""

    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "play":
        play(args.competition, args.tournament, args.players, args.number)
    if args.command == "reevaluate":
        reevaluate_matches(args.competition, args.tournament, args.players)
    if args.command == "grade":
        grade_players(args.competition, args.tournament, args.players, args.number)
    elif args.command == "analyze":
        analyze_competition(
            args.competition, args.tournament, args.players, args.critique
        )
    elif args.command == "evolve":
        evolve_season(args.competition, args.players, args.reference_player)
    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    log_filename = (
        f"log/promptrank_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    )
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s\n%(message)s\n======\n",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    main()
