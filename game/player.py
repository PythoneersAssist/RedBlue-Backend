class Player:
    def __init__(self, name: str):
        self.name = name
        self.score = 0
        self.picks = []
        self.past_score = []