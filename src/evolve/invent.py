import re
import glob
from ruamel.yaml import YAML
from src.tournament import load_tournament
from src.llm import complete
from .helper import LS

##############################################
TOURNAMENT_SUMMARIES = """Tournament {tournament}:

The objective of this tournament was to {objective} with the following evaluation criteria:
{criteria}
---
"""


##############################################
INVENTION_PROMPT = """As an expert AI instruction designer, your task is to create instructions for an AI tool in order to maximize its performance in a competition. 
The competition consists of a series of tournaments. In each tournament, the AI tool is evaluated on a set of challenges.

The tool will compete in the following tournaments in the competition:
{tournament_summary}

The instructions for the AI will include the following placeholders:
{{company}} - the name of the company for which the AI tool is working
{{query}} - the query that the AI tool should answer
{{date}} - the date on which the AI tool should answer the query
{{summary}} - the synopsis of market research report from which excerpts are provided to the AI tool to answer the query
{{text}} - excerpts from market research reports from which the AI tool should answer the query

Your task is to create the best possible instructions for the AI tool to win the competition.

Take a deep breath and carefully analyze the tournament objectives and evaluation criteria.

Now, it is time to write the best possible instructions. 
"""


##############################################
def invent_player(competition, model, temperature, run_id, variations=1):
    """Invent instructions for a new player."""

    turnament_summaries = []

    # scan all tournaments
    for tournament in glob.glob(f"competitions/{competition}/tournaments/*"):
        # load tournament
        tournament_state = load_tournament(competition, tournament.split("/")[-1])

        # get the relevant tournament optimization targets
        turnament_summaries.append(
            {
                "tournament": tournament_state["meta"]["name"],
                "objective": tournament_state["meta"]["objective"],
                "criteria": tournament_state["evaluation"]["criteria"],
            }
        )

    # collect the targets
    tournament_summary = "\n".join(
        [TOURNAMENT_SUMMARIES.format(**c) for c in turnament_summaries]
    )

    # generate invention prompt
    prompt = INVENTION_PROMPT.format(
        tournament_summary=tournament_summary,
    )

    # generate variations
    invented_players = []
    for ix in range(variations):
        # player name
        invented_player = (
            f"{model}-t{temperature*10:02.0f}-invented-{run_id}-{ix+1:02.0f}"
        )
        invented_players.append(invented_player)

        print(f"Generating {invented_player} - variation {ix+1} of {variations}...")
        invented_completion = complete("gpt-4", 1.0, prompt)

        # clean
        invented_completion = re.sub(r"===[A-Z\s]+===", "", invented_completion)
        invented_completion = invented_completion.strip(" \n'\"")

        # save fused prompt
        yaml = YAML()
        with open(
            f"competitions/{competition}/players/{invented_player}.yaml",
            "w",
        ) as f:
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
