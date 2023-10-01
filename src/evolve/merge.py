import re
import glob
from ruamel.yaml import YAML
from src.analyze import analyze_player
from src.tournament import load_tournament
from src.llm import complete
from .helper import LS


##############################################
PLAYER_CRITIQUES = """Tournament {tournament}:

The objective of this tournament was to {objective} with the following evaluation criteria:
{criteria}

This is the critique of the tournament judges on the performance of player {player_A}:
{critique_A}

This is the critique of the tournament judges on the performance of player {player_B}:
{critique_B}
---
"""

##############################################
MERGE_PROMPT = """Your task is to optimize instructions for an AI tool in order to maximize its performance in a competition. 
The competition consists of a series of tournaments. In each tournament, AI tools are evaluated on their performance on a set of challenges. 

In the previous competition, the players {player_A} and {player_B} have performed well.

This are the instruction that player {player_A} used:
===BEGIN INSTRUCTION===
{instruction_A}
===END INSTRUCTION===

This are the instruction that player {player_B} used:
===BEGIN INSTRUCTION===
{instruction_A}
===END INSTRUCTION===

This is a critique of their performance across all tournaments:
{critique_summary}

Your task is now to fuse the instructions of players {player_A} and {player_B} into a single AI tool instruction that combines the strengths of the the players and overcomes their weaknesses.

You are free to alter the instructions of the players in any way you deem helpful. You can also add new instructions. However, you must use all of the existing placeholders and not add new ones.

Take a deep breath and carefully analyze the instructions of the players and their critiques to understand where their strengths and weaknesses lie, how to best combine their advantages, and what new elements to introduce.

Now, it is time to write the best possible instructions based on the learnings from the players' critiques. 
"""


##############################################
def merge_players(
    competition, player_set, player_A_name, player_B_name, run_id, variations=1
):
    # collect player's critiques

    player_A = player_B = None
    critiques = []

    # scan all tournaments
    for tournament in glob.glob(f"competitions/{competition}/tournaments/*"):
        # load tournament
        tournament_state = load_tournament(
            competition, tournament.split("/")[-1], player_set
        )

        # get the player
        if player_A is None:
            player_A = tournament_state["players"][player_A_name]
        if player_B is None:
            player_B = tournament_state["players"][player_B_name]

        # get the analysis of the players
        critiques.append(
            {
                "tournament": tournament_state["meta"]["name"],
                "critique_A": analyze_player(tournament_state, player_A_name),
                "critique_B": analyze_player(tournament_state, player_B_name),
                "objective": tournament_state["evaluation"]["objective"],
                "criteria": tournament_state["evaluation"]["criteria"],
                "player_A": player_A_name,
                "player_B": player_B_name,
            }
        )

    # collect the critiques
    critique_summary = "\n".join([PLAYER_CRITIQUES.format(**c) for c in critiques])

    # generate enhancement prompt
    prompt = MERGE_PROMPT.format(
        critique_summary=critique_summary,
        player_A=player_A_name,
        player_B=player_B_name,
        instruction_A=player_A["prompt"],
        instruction_B=player_B["prompt"],
    )

    # generate variations
    merged_players = []
    for ix in range(variations):
        # player name
        merged_player = f"{player_A['model']}-t{player_A['temperature']*10:02.0f}-merged-{run_id}-{ix+1:02.0f}"
        merged_players.append(merged_player)

        print(f"Generating {merged_player} - variation {ix+1} of {variations}...")
        merged_completion = complete("gpt-4", 1.0, prompt)

        # clean
        merged_completion = re.sub(r"===[A-Z\s]+===", "", merged_completion)
        merged_completion = merged_completion.strip(" \n'\"")

        # save fused prompt
        yaml = YAML()
        with open(
            f"competitions/{competition}/players/{merged_player}.yaml",
            "w",
        ) as f:
            yaml.dump(
                {
                    "name": merged_player,
                    "model": player_A["model"],
                    "temperature": player_A["temperature"],
                    "ancestor-A": player_A_name,
                    "ancestor-B": player_B_name,
                    "prompt": LS(merged_completion),
                },
                f,
            )

    # finally return merged players
    return merged_players
