from fastapi import WebSocket
from typing import List, Dict

class ConnectionManager:
    def __init__(self):
        # Stores active WebSocket connections for each game session
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, game_code: str, websocket: WebSocket):
        await websocket.accept()
        if game_code not in self.active_connections:
            self.active_connections[game_code] = []
        self.active_connections[game_code].append(websocket)

    def disconnect(self, game_code: str, websocket: WebSocket):
        if game_code in self.active_connections:
            self.active_connections[game_code].remove(websocket)
            if not self.active_connections[game_code]:
                del self.active_connections[game_code]

    async def broadcast(self, game_code: str, message: dict):
        """Broadcast a message to all connections in a given game session."""
        if game_code in self.active_connections:
            for connection in self.active_connections[game_code]:
                await connection.send_json(message)