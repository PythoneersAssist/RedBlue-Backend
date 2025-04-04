import player


class Match:
    def __init__(self, code: str, ownerName: str):
        self.code = -1
        self.owner = None
        self.slave = None
        self.round = 0
        self.maxRounds = 10
        self.winner = None
    
    def add_player(self, name: str) -> dict:
        if not self.owner:
            self.owner = player.Player(name)
        elif not self.slave:
            self.slave = player.Player(name)
        else:
            raise Exception("Match is full") #TODO: raise a custom exception


    def get_winner(self) -> dict:
        assert self.round < self.maxRounds, "get_Winner() should only be called if the match is over"
        if self.owner.score == self.slave.score:
            return {
                "type": "game:winner", 
                "winner": None,
                }
        
        self.winner = self.owner if self.owner.score > self.slave.score else self.slave
        return {
            "type": "game:winner", 
            "winner": self.winner.name,
            }

    def calculate_round(self, ownerPick: int, slavePick: int) -> dict:
        assert self.round < self.maxRounds, "calculate_round() should only be called if the match is not over"
        self.owner.picks.append(ownerPick)
        self.slave.picks.append(slavePick)
        # RED = 0, BLUE = 1
        if not ownerPick and not slavePick:
            self.owner.score += 3
            self.slave.score += 3
        if not ownerPick and slavePick:
            self.owner.score -= 6
            self.slave.score += 6
        if ownerPick and not slavePick:
            self.owner.score += 6
            self.slave.score -= 6
        if ownerPick and slavePick:
            self.owner.score -= 3
            self.slave.score -= 3

        self.owner.past_score.append(self.owner.score)
        self.slave.past_score.append(self.slave.score)
        if self.round + 1 >= self.maxRounds:
            return self.get_winner()
        self.round += 1
        return {
            "type": "game:round",
            "round": self.round,
            "owner_score": self.owner.score,
            "slave_score": self.slave.score,
        }

