import random


def generate_random_code(length: int):
    """
    Generate a random code of the given length.
    The code is a string of digits.
    """
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

def calculate_score(playerOne: int, playerTwo: int):
    """
    Calculate the score based on the choices of player one and player two.
    The scoring logic is as follows:
    - If both players choose the same color, they both get 1 point.
    - If player one chooses red (0) and player two chooses blue (1), player one gets 2 points.
    - If player one chooses blue (1) and player two chooses red (0), player two gets 2 points.
    """
    if not playerOne and not playerTwo:
        return 3, 3
    if not playerOne and playerTwo:
        return -6, 6
    if playerOne and not playerTwo:
        return  6, -6
    if playerOne and playerTwo:
        return -3, -3
