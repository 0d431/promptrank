import re
import glob
import random
import string
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString
import textwrap
from src.analyze import analyze_players, analyze_player
from src.tournament import load_tournament
from src.llm import complete


def LS(s):
    """Helper function for YAML writing"""
    return LiteralScalarString(textwrap.dedent(s))


##############################################
def _get_best_player(tournament_state):
    """Determine which the best performing player is and return it with its prompt and critique."""

    # get overall analysis of the tournament
    _, analysis = analyze_players(tournament_state, skip_critique=True)

    # get the best player
    best_player = tournament_state["players"][
        max(analysis, key=lambda x: analysis[x]["score"])
    ]

    # get the critique for the best player
    critique = analyze_player(tournament_state, best_player["name"])

    return best_player, critique


##############################################
def _collect_tournament_winners(competition, player_set):
    """Collect the best players from each tournament."""

    best_players = []

    # scan all tournaments
    for tournament in glob.glob(f"competitions/{competition}/tournaments/*"):
        # load tournament
        tournament_state = load_tournament(
            competition, tournament.split("/")[-1], player_set
        )

        best_player, critique = _get_best_player(tournament_state)
        best_players.append(
            {
                "name": best_player["name"],
                "model": best_player["model"],
                "instruction": best_player["prompt"],
                "temperature": best_player["temperature"],
                "critique": critique,
                "tournament": tournament_state["evaluation"]["name"],
                "objective": tournament_state["evaluation"]["objective"],
                "criteria": tournament_state["evaluation"]["criteria"],
            }
        )

    return best_players


##############################################
TOURNAMENT_OUTCOME = """Tournament {tournament}:

The winner in the {tournament} tournament of the competition was player {name}. The objective of this tournament was to {objective} with the following evaluation criteria:
{criteria}

This is the critique of the tournament judges on the performance of player {name}:
===BEGIN CRITIQUE===
{critique}
===END CRITIQUE===

This are the instruction that player {name} used:
===BEGIN INSTRUCTION===
{instruction}
===END INSTRUCTION===

"""

##############################################
FUSION_PROMPT = """Your task is to optimize instructions for an AI tool in order to maximize its performance in a competition. 
The competition consists of a series of tournaments. In each tournament, the AI tool will be evaluated on its performance on a set of challenges. 
The winner of each tournament will be the AI tool that performs best on the challenges in that tournament. 

This are the winning players of the tournaments in the competition, along with a critique of their shortcomings.
{tournament_outcomes}

Your task is now to fuse instructions of the winning players into a single AI tool instruction that combines the strengths of the winning players and overcomes their shortcomings.

Take a deep breath and silently analyze the instructions of the winning players and their critiques.

Now, it is time to write the best possible instructions based on the learnings from the winning players and their critiques. You are free to alter the instructions of the winning players in any way you deem helpful. You can also add new instructions. 
"""


#################################################
def _generate_random_id(length=3):
    return "".join(
        [random.choice(string.ascii_lowercase) for _ in range(length)]
    ).upper()


##############################################
def fuse_players(competition, player_set, variations=1):
    # get the best players from each tournament
    print(f"Collecting best players from all tournaments in {competition}...")
    tournament_winners = _collect_tournament_winners(competition, player_set)

    # generate variations
    fused_players = []
    variation_run = _generate_random_id()
    for ix in range(variations):
        # player name
        fused_player = f"{tournament_winners[0]['model']}-t{tournament_winners[0]['temperature']*10:02.0f}-fused-{variation_run}-{ix+1:02.0f}"
        fused_players.append(fused_player)

        print(f"Generating {fused_player} - variation {ix+1} of {variations}...")

        tournament_outcomes = []
        ancestors = {}
        for tournament_winner in tournament_winners:
            print(
                f"  Winner for {tournament_winner['tournament'].upper()}: {tournament_winner['name']}"
            )
            ancestors[
                f"ancestor-{tournament_winner['tournament'].lower()}"
            ] = tournament_winner["name"]
            tournament_outcomes.append(TOURNAMENT_OUTCOME.format(**tournament_winner))

        # generate fused prompt
        fused_prompt = complete(
            "gpt-4",
            1.0,
            FUSION_PROMPT.format(tournament_outcomes="\n".join(tournament_outcomes)),
        )

        # clean
        fused_prompt = re.sub(r"===[A-Z\s]+===", "", fused_prompt)
        fused_prompt = fused_prompt.strip(" \n'\"")

        # save fused prompt
        yaml = YAML()
        with open(
            f"competitions/{competition}/players/{fused_player}.yaml",
            "w",
        ) as f:
            yaml.dump(
                {
                    "name": fused_player,
                    "model": tournament_winners[0]["model"],
                    "temperature": tournament_winners[0]["temperature"],
                    **ancestors,
                    "prompt": LS(fused_prompt),
                },
                f,
            )

    # finally write a new player set for eval
    fused_player_set = f"{player_set}-{variation_run}"

    with open(
        f"competitions/{competition}/player_sets/{fused_player_set}.players",
        "w",
    ) as f:
        for fused_player in fused_players:
            f.write(f"{fused_player}.yaml\n")
        for tournament_winner in tournament_winners:
            f.write(f"{tournament_winner['name']}.yaml\n")

    print(
        f"Generated {variations} variations of fused players in player set {fused_player_set}."
    )
