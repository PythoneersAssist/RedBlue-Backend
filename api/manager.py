from uuid import uuid4

class ConnectionManager:
    def __init__(self):
        # Stores active WebSocket connections for each game session
        self.active_connections = {}
        self.reconenction_ids = {}
        self.sockets = {}

    async def connect(self, game_code: str, player_name: str, websocket):
        if game_code not in self.active_connections:
            self.active_connections[game_code] = {}
            self.reconenction_ids[game_code] = {}
            self.sockets[game_code] = []
        self.active_connections[game_code][player_name] = 0 
        if not player_name in self.reconenction_ids[game_code]:
            self.reconenction_ids[game_code][player_name] =  uuid4()
        self.sockets[game_code].append(websocket) # Initialize choice to 0 or any default value
        print(self.active_connections[game_code])
        
    def disconnect(self, game_code: str, websocket):
        if game_code in self.sockets:
            self.sockets[game_code].remove(websocket)

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
        pass
    
    async def store_choice(self, game_code: str, player_name: str):
        """
        Store the player's choice for the current round.
        """
        if game_code in self.active_connections:
            print(f"Set the choice to 1 for: {player_name}")
            self.active_connections[game_code][player_name] = 1

    async def has_choice(self, game_code: str):
        """
        Check if a player has made a choice in the current round.
        """
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                if self.active_connections[game_code][connection] == 0:
                    #print(f"Connection: {connection.client} : {self.active_connections[game_code][connection]}")
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