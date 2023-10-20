import re
import os
from ruamel.yaml import YAML
from src.llm import complete
from src.analyze import get_player_critique
from .helper import LS, EVOLUTION_MODEL, generate_random_id, ensure_single_placeholder_occurrence

##############################################
PLAYER_CRITIQUES = """Tournament "{tournament}":

The objective of this tournament was to {objective} with the following evaluation criteria:
{criteria}

This is the critique of the tournament judges on the performance of player {player_name}:
{critique}
---
"""


##############################################
ENHANCEMENT_PROMPT = """Your task is to optimize instructions for an AI tool in order to maximize its performance in a competition. 
The competition consists of a series of tournaments. In each tournament, the AI tool is evaluated on a set of challenges.

The tool {player_name} has used the following instructions in the competition:
===BEGIN INSTRUCTION===
{instruction}
===END INSTRUCTION===

These are the evaluations for the tool {player_name}:

{critique_summary}

Your task is to optimize the instructions for the tool {player_name} to improve its performance in the competition.

Take care to preserve the strengths of the tool {player_name} and to overcome its weaknesses, as descibed in the evaluations above.

You are free to alter the instructions of the tool {player_name} in any way you deem helpful. You can also add new instructions. However, you must use all of the existing placeholders and not add new ones.

Take a deep breath and carefully analyze the instructions of the player and its evaluations to understand where its strengths and weaknesses lie and think carefully about how to improve the weaknesses.

Now, it is time to write the best possible instructions based on the learnings from the evaluations. 
"""


##############################################
def enhance_player(tournaments, player_name, player_prefix, variations=1):
    """Take the given player and try to improve its shortcomings along all tournament dimensions."""

    player = None
    critiques = []

    # scan all tournaments
    for tournament in tournaments.values():
        # get the player
        if player is None:
            player = tournament["players"][player_name]

        # get the analysis of the player
        critiques.append(
            {
                "competition": tournament["meta"]["competition"]["name"],
                "tournament": tournament["meta"]["tournament"],
                "critique": get_player_critique(tournament, player_name, True),
                "objective": tournament["evaluation"]["objective"],
                "criteria": tournament["evaluation"]["criteria"],
                "player_name": player_name,
            }
        )

    # collect the critiques
    critique_summary = "\n".join([PLAYER_CRITIQUES.format(**c) for c in critiques])

    # generate enhancement prompt
    prompt = ENHANCEMENT_PROMPT.format(
        critique_summary=critique_summary,
        player_name=player_name,
        instruction=player["prompt"],
    )

    # generate variations
    enhanced_players = []
    for ix in range(variations):
        # player name
        enhanced_player = f"{player_prefix}enhanced-{player['model']}-t{player['temperature']*10:02.0f}-{generate_random_id()}"
        enhanced_players.append(enhanced_player)

        print(f"Generating {enhanced_player} - variation {ix+1} of {variations}...")
        enhanced_completion = complete(EVOLUTION_MODEL, 1.0, prompt)

        # clean
        enhanced_completion = re.sub(r"===[A-Z\s]+===", "", enhanced_completion)
        enhanced_completion = enhanced_completion.strip(" \n'\"")

        # force replacement of all occurrences of placeholder {text}, except for the first one
        enhanced_completion = ensure_single_placeholder_occurrence(enhanced_completion, "text")

        # save fused prompt
        yaml = YAML()
        player_filename = f"competitions/{critiques[0]['competition']}/players/{enhanced_player}.yaml"
        os.makedirs(os.path.dirname(player_filename), exist_ok=True)
        with open(player_filename, "w") as f:
            yaml.dump(
                {
                    "name": enhanced_player,
                    "model": player["model"],
                    "temperature": player["temperature"],
                    "ancestor": player_name,
                    "critique": LS(critique_summary),
                    "prompt": LS(enhanced_completion),
                },
                f,
            )

    # return list of enhanced players
    return enhanced_players
