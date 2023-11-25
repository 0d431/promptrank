import os
import json
import datetime
import concurrent.futures
from llm import complete


##############################################
def run_in_parallel(fun, args, max_workers=10):
    """Execute a function in parallel on a set of args"""
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_arg = {executor.submit(fun, *arg): arg for arg in args}
        for future in concurrent.futures.as_completed(future_to_arg):
            results.append(future.result())

    return results


##############################################
def escape_player_name(player_name):
    """Escape a player name for use in a filename"""
    return player_name.replace("/", "=")


##############################################
def unescape_player_name(player_name):
    """Unescape a player name for use in a filename"""
    return player_name.replace("=", "/")


##############################################
def _get_performance_id(challenge_name, player_name):
    """Generate a unique ID for a performance"""

    return challenge_name + ":" + escape_player_name(player_name)


##############################################
def perform(tournament, challenge_name, player):
    """Perform a performance for a player"""

    performance_file = f"competitions/{tournament['meta']['competition']['name']}/performances/{_get_performance_id(challenge_name, player['name'])}.json"
    if not os.path.exists(performance_file):
        # create the performance
        challenge = tournament["challenges"][challenge_name]
        challenge["date"] = f"{datetime.datetime.now():%Y-%m-%d}"
        performance = {
            "player": player["name"],
            "challenge": challenge_name,
            "output": complete(
                system=player.get("system", ""),
                prompt=player["prompt"].format(**challenge),
                model=player["model"],
                temperature=player["temperature"],
            ),
        }
        
        # store the performance
        with open(performance_file, "w") as file:
            json.dump(performance, file, indent=2)
    else:
        # load the performance
        with open(performance_file, "r") as file:
            performance = json.load(file)

    return performance
