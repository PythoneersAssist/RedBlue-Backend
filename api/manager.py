from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Stores active WebSocket connections for each game session
        self.active_connections: Dict[str, Dict[WebSocket, int]] = {}

    async def connect(self, game_code: str, websocket: WebSocket):
        await websocket.accept()
        if game_code not in self.active_connections:
            self.active_connections[game_code] = {}
        self.active_connections[game_code][websocket] = 0  # Initialize choice to 0 or any default value

    def disconnect(self, game_code: str, websocket: WebSocket):
        if game_code in self.active_connections:
            del self.active_connections[game_code][websocket]
            if not self.active_connections[game_code]:
                del self.active_connections[game_code]

    async def broadcast(self, game_code: str, message: dict):
        """Broadcast a message to all connections in a given game session."""
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                await connection.send_json(message)
    
    async def get_websocket(self,game_code: str, websocket: WebSocket):
        """
        Get the WebSocket connection for a specific game session.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                if connection == websocket:
                    return connection
        pass
    
    async def store_choice(self, game_code: str, websocket: WebSocket):
        """
        Store the player's choice for the current round.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                if connection == websocket:
                    self.active_connections[game_code][websocket] = 1

    async def has_choice(self, game_code: str):
        """
        Check if a player has made a choice in the current round.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                if self.active_connections[game_code][connection] == 0:
                    return False
        print("Looks like user has made a choice")
        return True

    async def clear_choices(self, game_code: str):
        """
        Clear the choices for all players in the current round.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                self.active_connections[game_code][connection] = 0

    async def is_room_full(self, game_code: str):
        """
        Check if the game room is full (i.e., has two players).
        """
        if game_code in self.active_connections:
            return len(self.active_connections[game_code]) == 2
        return False