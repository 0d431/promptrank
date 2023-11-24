import math 
import numpy as np
from scipy.optimize import minimize


##############################################
def calculate_winning_likelihoods(labels, matches):
    """Plot a matrix of score stats of each player pair."""

    # Create a matrix of scores
    matrix = np.zeros((len(labels), len(labels)))
    match_count = np.zeros((len(labels), len(labels)))

    for match in matches:
        player_A_name = match["player_A"]["name"]
        player_B_name = match["player_B"]["name"]

        if match["result"]["winner"] == "DRAW":
            matrix[labels.index(player_A_name), labels.index(player_B_name)] += 0.5
            matrix[labels.index(player_B_name), labels.index(player_A_name)] += 0.5
        elif match["result"]["winner"] == player_A_name:
            matrix[labels.index(player_A_name), labels.index(player_B_name)] += 1.0
        elif match["result"]["winner"] == player_B_name:
            matrix[labels.index(player_B_name), labels.index(player_A_name)] += 1.0
        else:
            # ignore DNP
            continue

        match_count[labels.index(player_A_name), labels.index(player_B_name)] += 1
        match_count[labels.index(player_B_name), labels.index(player_A_name)] += 1

    # divide matrix by number of matches
    matrix = np.divide(
        matrix, match_count, out=np.zeros_like(matrix), where=matches != 0
    )

    return matrix, match_count


##############################################
def _elo_prob(delta_R):
    """Computes expected winning probability using ELO model."""
    return 1.0 / (1 + 10 ** (-delta_R / 400))


##############################################
def _loss_function(R, observed_probs, observations):
    """Computes the loss (sum of squared differences) between observed
    probabilities and those given by the ELO model."""
    loss = 0.0
    count = 0
    for i in range(observed_probs.shape[0]):
        for j in range(observed_probs.shape[1]):
            if i == j:
                continue

            number_of_obs = observations[i, j]
            if number_of_obs == 0:
                continue

            observed_prob = observed_probs[i, j]
            if observed_prob == 0:
                observed_prob = 0.01
            if observed_prob == 1:
                observed_prob = 0.99

            weight = 1.0 / math.sqrt(observed_prob * (1 - observed_prob) / number_of_obs)
            expected_prob = _elo_prob(R[i] - R[j])
            loss += weight * (observed_prob - expected_prob) ** 2
            count += 1

    return loss / count


##############################################
def estimate_elo(observed_probs, observations):
    """Estimates ELO scores given a set of player pairs and the observed
    probabilities of the first player winning."""

    # set initial ELO
    initial_R = 1000 * np.ones(observed_probs.shape[0])
    additional_R = np.nansum(observed_probs, axis=1) / observed_probs.shape[0]
    for i in range(observed_probs.shape[0]):
        initial_R[i] += 500 * additional_R[i]

    # iterate
    res = minimize(
        fun=_loss_function,
        x0=initial_R,
        args=(observed_probs, observations),
        method="L-BFGS-B",  # This is a bounded version of the BFGS algorithm
    )

    return res.x, _loss_function(res.x, observed_probs, observations) 
