import random


def generate_random_code(length: int):
    """
    Generate a random code of the given length.
    The code is a string of digits.
    """
    return "".join([str(random.randint(0, 9)) for _ in range(length)])

