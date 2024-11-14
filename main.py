from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.users = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.users[websocket] = username
        await self.broadcast_user_list()

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        del self.users[websocket]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_user_list(self):
        user_list = list(self.users.values())
        for connection in self.active_connections:
            await connection.send_json({"type": "user_list", "users": user_list})

    async def send_private_message(self, message: str, sender: str, recipient_username: str):
        recipient_socket = next(
            (ws for ws, user in self.users.items() if user == recipient_username), None
        )
        if recipient_socket:
            await recipient_socket.send_json({"type": "private_message", "sender": sender, "message": message})

manager = ConnectionManager()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    try:
        while True:
            try:
                data = await websocket.receive_json()
                if "type" not in data:
                    continue  # Ignorar mensajes sin el tipo adecuado
                if data["type"] == "private_message":
                    await manager.send_private_message(data["message"], username, data["recipient"])
            except (ValueError, KeyError) as e:
                await websocket.send_json({"type": "error", "message": "Invalid data format."})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_user_list()

#python -m uvicorn main:app --reload