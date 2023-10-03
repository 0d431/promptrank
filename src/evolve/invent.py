import os
from ruamel.yaml import YAML
from src.llm import complete
from .helper import LS, EVOLUTION_MODEL, generate_random_id

##############################################
TOURNAMENT_SUMMARIES = """Tournament "{tournament}":

The objective of this tournament was to {objective} with the following evaluation criteria:
{criteria}
---
"""


##############################################
INVENTION_PROMPT = """As an expert AI instruction designer, your task is to create an instruction template for an AI tool in order to maximize its performance in a competition. The competition consists of a series of tournaments. In each tournament, the AI tool is evaluated on a set of challenges.

The tool will compete in the following tournaments in the competition:

{tournament_summary}

The instruction template for the AI must reference the following Python f-string placeholders:
{placeholders}

Placeholders used in the instruction template will be replaced with the respective actual content during the tournament to generate the specific instructions.

Your task is to create the best possible instruction template for the AI tool to win the competition. You can give the AI a suitable persona in the instruction template, or use other means of putting it into the right frame. Be crafty and creative!

Take note that there can be only one instruction template that will be used for all tournaments! You must under no circumstances mention or refer to the competition or its tournaments in the instruction template.

Take a deep breath and carefully analyze the tournament objectives and evaluation criteria.

Now, it is time to write the best possible instruction template."""


##############################################
def invent_player(tournaments, model, temperature, player_prefix, variations=1):
    """Invent instructions for a new player."""

    tournament_summaries = []

    # scan all tournaments
    for tournament in tournaments.values():
        # get the relevant tournament optimization targets
        tournament_summaries.append(
            {
                "competition": tournament["meta"]["competition"]["name"],
                "tournament": tournament["meta"]["tournament"],
                "objective": tournament["evaluation"]["objective"],
                "criteria": tournament["evaluation"]["criteria"],
            }
        )

    # collect the targets
    tournament_summary = "\n".join(
        [TOURNAMENT_SUMMARIES.format(**c) for c in tournament_summaries]
    )

    # generate invention prompt
    prompt = INVENTION_PROMPT.format(
        tournament_summary=tournament_summary,
        placeholders=tournaments[next(iter(tournaments))]["meta"]["competition"]["placeholders"],
    )

    # generate variations
    invented_players = []
    for ix in range(variations):
        # player name
        invented_player = (
            f"{player_prefix}invented-{model}-t{temperature*10:02.0f}-{generate_random_id()}"
        )
        invented_players.append(invented_player)

        print(f"Generating {invented_player} - variation {ix+1} of {variations}...")
        invented_completion = complete(EVOLUTION_MODEL, 1.0, prompt)

        # clean
        invented_completion = invented_completion.strip(" \n'\"")

        # save fused prompt
        yaml = YAML()
        player_filename = f"competitions/{tournament_summaries[0]['competition']}/players/{invented_player}.yaml"
        os.makedirs(os.path.dirname(player_filename), exist_ok=True)
        with open(player_filename, "w") as f:
            yaml.dump(
                {
                    "name": invented_player,
                    "model": model,
                    "temperature": temperature,
                    "prompt": LS(invented_completion),
                },
                f,
            )

    # return list of enhanced players
    return invented_players
