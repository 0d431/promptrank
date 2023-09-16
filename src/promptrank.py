import dotenv
dotenv.load_dotenv()

import argparse
from match import run_match
from tournament import load_tournament
from analyze import analyze_players, plot_elo_history


def play(competition, tournament, number_matches):
    """Play a number of matches."""

    tournament_state = load_tournament(competition, tournament)

    for _i in range(number_matches):
        print(f"\nPlaying match {_i + 1}/{number_matches}")
        run_match(tournament_state)

    print(
        f"\nDone - {tournament_state['meta']['pairings'] - len(tournament_state['matches'])} matches left to play"
    )


def analyze(competition, tournament, write_file):
    """Analyze player performance."""

    tournament_state = load_tournament(competition, tournament)
    print(f"\nAnalyzing {len(tournament_state['players'])} players")

    dump, _analysis = analyze_players(tournament_state)

    if write_file:
        with open(f"competitions/{competition}/tournaments/{tournament}/analysis.md", "w") as f:
            f.write(dump + "\n\n### ELO score development\n![ELO Development](./elo_history.png)")

        plot_elo_history(tournament_state, f"competitions/{competition}/tournaments/{tournament}/elo_history.png")
    else:
        print(dump)


def main():
    """Command-line interface."""

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
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze player performance."
    )
    analyze_parser.add_argument(
        "-w",
        "--write_file",
        action="store_true",
        help="If set, write analysis to analysis.md in tournament directory.",
    )

    args = parser.parse_args()

    if args.command == "play":
        play(args.competition, args.tournament, args.number)
    elif args.command == "analyze":
        analyze(args.competition, args.tournament, args.write_file)
    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    main()
