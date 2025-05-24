"""
Utilities for game logic and creation
"""

import random


def generate_random_code(length: int):
    """
    Generate a random code of the given length.
    The code is a string of digits.
    """
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def calculate_score(player_one: int, player_two: int, bonusRound: bool):
    """
    Calculate the score based on the choices of player one and player two.
    The scoring logic is as follows:
    - If both players choose the same color, they both get 1 point.
    - If player one chooses red (0) and player two chooses blue (1), player one gets 2 points.
    - If player one chooses blue (1) and player two chooses red (0), player two gets 2 points.
    - If bonusRound is True, the score is doubled.
    """
    
    if not player_one and not player_two:
        score = (3, 3)
    elif not player_one and player_two:
        score = (-6, 6)
    elif player_one and not player_two:
        score = (6, -6)
    elif player_one and player_two:
        score = (-3, -3)
    else:
        score = (0, 0)  # Default case, though it shouldn't occur with valid inputs

    if bonusRound:
        score = (score[0] * 2, score[1] * 2)

    return score

def calculate_forfeit_score(abandoned, remained, rounds):
    scores = [abandoned + (-6 * (10 - rounds)), remained + (6 * (10 - rounds))]
    scores[0] += -24

    if rounds < 8:
        scores[0] += 12
        scores[1] += -12
        
    return scores
