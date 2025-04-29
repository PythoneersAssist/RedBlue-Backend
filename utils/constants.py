"""
Module used to store code constants and strings.
"""

#pylint: disable=line-too-long

DISCONNECT_TIMEOUT = 600 # 10 minutes

NOT_FOUND_MESSAGE = "Game not found"
GAME_FULL_MESSAGE = "Game is full"
RECONNECTION_TOKEN_MESSAGE = "You have received a reconnection token. This should be used if the user disconnects."
GAME_IN_PROGRESS_MESSAGE = "Game is already in progress. Please provide a reconnection token."
INVALID_TOKEN_MESSAGE = "Invalid reconnection token. Please try again."
EXPIRED_TOKEN_MESSAGE = "Reconnection token has expired. You cannot join this game."
RECONNECTED_MESSAGE = "Reconnected successfully. You can now play the game."
PLAYER_RECONNECT_MESSAGE = "{0} has reconnected."
GF_MESSAGE = "Game is already finished."
INVALID_GAME_STATE = "Invalid game state. If you see this, I fucked up."
JOIN_MESSAGE = "Joined game succesfully."
WFPJ_MESSAGE = "Waiting for the other player to join..."
ROUND_MESSAGE = "Round {0} has started. Awaiting user input."
INVALID_CHOICE_MESSAGE = "Invalid choice. Must be 0 or 1. Please try again."
CHOICE_DISCONNECTED_MESSAGE = "The other player has disconnected however he can still reconnect and make a choice."
WFP_MESSAGE = "Waiting for the other player to finish the round."
UNEXPECTED_FINISH_MESSAGE = "The game has finished unexpectedly. If you see this, I fucked up."
DISCONNECT_MESSAGE = "{0} has disconnected"
GAME_TIMEOUT_MESSAGE = "The game has ended due to inactivity."
