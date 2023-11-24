import re
import os
from ruamel.yaml import YAML
from analyze.analyze import get_player_critique
from src.llm import complete
from .helper import (
    LS,
    EVOLUTION_MODEL,
    generate_random_id,
    ensure_single_placeholder_occurrence,
)


##############################################
PLAYER_CRITIQUES = """Tournament "{tournament}":

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
    tournaments, player_A_name, player_B_name, player_prefix, variations=1
):
    # collect player's critiques

    player_A = player_B = None
    critiques = []

    # scan all tournaments
    for tournament in tournaments.values():
        # get the player
        if player_A is None:
            player_A = tournament["players"][player_A_name]
        if player_B is None:
            player_B = tournament["players"][player_B_name]

        # get the analysis of the players
        critiques.append(
            {
                "competition": tournament["meta"]["competition"]["name"],
                "tournament": tournament["meta"]["tournament"],
                "critique_A": get_player_critique(tournament, player_A_name, True),
                "critique_B": get_player_critique(tournament, player_B_name, True),
                "objective": tournament["evaluation"]["objective"],
                "criteria": tournament["evaluation"]["criteria"],
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
        merged_player = f"{player_prefix}merged-{player_A['model']}-t{player_A['temperature']*10:02.0f}-{generate_random_id()}"
        merged_players.append(merged_player)

        print(f"Generating {merged_player} - variation {ix+1} of {variations}...")
        merged_completion = complete(EVOLUTION_MODEL, 1.0, prompt)

        # clean
        merged_completion = re.sub(r"===[A-Z\s]+===", "", merged_completion)
        merged_completion = merged_completion.strip(" \n'\"")

        # force replacement of all occurrences of placeholder {text}, except for the first one
        merged_completion = ensure_single_placeholder_occurrence(
            merged_completion, "text"
        )

        # save fused prompt
        yaml = YAML()
        player_filename = (
            f"competitions/{critiques[0]['competition']}/players/{merged_player}.yaml"
        )
        os.makedirs(os.path.dirname(player_filename), exist_ok=True)
        with open(player_filename, "w") as f:
            yaml.dump(
                {
                    "name": merged_player,
                    "model": player_A["model"],
                    "temperature": player_A["temperature"],
                    "ancestor-A": player_A_name,
                    "ancestor-B": player_B_name,
                    "critiques": LS(critique_summary),
                    "prompt": LS(merged_completion),
                },
                f,
            )

    # finally return merged players
    return merged_players
