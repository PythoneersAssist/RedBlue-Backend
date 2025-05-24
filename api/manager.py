"""
ConnectionManager class to manage WebSocket connections for a game session.
This class handles the following functionalities:
1. Connect and disconnect players from a game session.
2. Store and retrieve player choices.
3. Broadcast messages to all players in a game session.
4. Check if a game room is full.
5. Clear player choices at the end of a round.
6. Handle reconnections and disconnections.
7. Monitor player disconnects and handle game state accordingly.
8. Store reconnection tokens for players.
9. Handle reconnection timers for players.
"""

from uuid import uuid4
from datetime import datetime

class ConnectionManager:
    """
    Manages WebSocket connections for a game session.
    Handles player connections, disconnections, and broadcasts messages.
    """
    def __init__(self):
        # Stores active WebSocket connections for each game session
        self.active_connections = {}
        self.reconnection_ids = {}
        self.sockets = {}
        self.reconnection_timers = {}
        self.chat_sockets = {}

    async def connect(self, game_code: str, player_name: str, websocket):
        """
        Connect a player to a game session.
        If the game session does not exist, create a new one.
        """
        if game_code not in self.active_connections:
            self.active_connections[game_code] = {}
            self.reconnection_ids[game_code] = {}
            self.sockets[game_code] = []
            self.reconnection_timers[game_code] = {}

        self.active_connections[game_code][player_name] = 0
        if not player_name in self.reconnection_ids[game_code]:
            self.reconnection_ids[game_code][player_name] =  uuid4()
        self.sockets[game_code].append(websocket) # Initialize choice to 0 or any default value
        print(self.active_connections[game_code])

    def disconnect(self, game_code: str, websocket, player_name: str):
        """
        Disconnect a player from a game session.
        If the player is not found, do nothing.
        """
        if game_code in self.sockets:
            self.active_connections[game_code].pop(player_name, None)
            self.sockets[game_code].remove(websocket)
            self.reconnection_timers[game_code][websocket] = datetime.now()

    async def disconnect_all(self, game_code: str):
        """
        Disconnect all players from a game session.
        This is used when the game is over or when a player has been disconnected for too long.
        """
        if game_code in self.sockets:
            print(self.sockets[game_code])
            for connection in self.sockets[game_code]:
                print(f"Disconnecting {connection.client} from game {game_code}")
                await connection.close(code=1000, reason="Game Over")
            del self.sockets[game_code]

    async def broadcast(self, game_code: str, message: dict):
        """Broadcast a message to all connections in a given game session."""

        if game_code in self.sockets:
            for connection in self.sockets[game_code]:
                await connection.send_json(message)

    async def get_websocket(self,game_code: str, player_name: str):
        """
        Get the WebSocket connection for a specific game session.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                if connection == player_name:
                    return connection

    async def store_choice(self, game_code: str, player_name: str):
        """
        Store the player's choice for the current round.
        """
        if game_code in self.active_connections:
            self.active_connections[game_code][player_name] = 1

    async def has_choice(self, game_code: str):
        """
        Check if a player has made a choice in the current round.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                if self.active_connections[game_code][connection] == 0:
                    return False
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

    async def chat_connect(self, game_code: str, websocket):
        """
        Connect a player to a game session.
        If the game session does not exist, create a new one.
        """
        if not game_code in self.chat_sockets:
            self.chat_sockets[game_code] = []
        self.chat_sockets[game_code].append(websocket)

    def chat_disconnect(self, game_code: str, websocket):
        """
        Disconnect a player from a game session.
        If the player is not found, do nothing.
        """
        if game_code in self.chat_sockets:
            self.chat_sockets[game_code].remove(websocket)

    async def chat_disconnect_all(self, game_code: str):
        """
        Disconnect all players from a game session.
        This is used when the game is over or when a player has been disconnected for too long.
        """
        if game_code in self.chat_sockets:
            for connection in self.chat_sockets[game_code]:
                await connection.close(code=1000, reason="Chat has ended.")
            del self.chat_sockets[game_code]

    async def chat_broadcast(self, game_code: str, message: dict):
        """Broadcast a message to all connections in a given game session."""
        if game_code in self.chat_sockets:
            for connection in self.chat_sockets[game_code]:
                await connection.send_json(message)
    
    async def delete_room(self, game_code: str):
        """
        Delete a game room and all associated data.
        This is used when the game is over or when a player has been disconnected for too long.
        """
        if game_code in self.active_connections:
            del self.active_connections[game_code]
        if game_code in self.reconnection_ids:
            del self.reconnection_ids[game_code]
        if game_code in self.sockets:
            del self.sockets[game_code]
        if game_code in self.reconnection_timers:
            del self.reconnection_timers[game_code]
        if game_code in self.chat_sockets:
            del self.chat_sockets[game_code]
