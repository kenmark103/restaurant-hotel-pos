from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # room_id -> set of connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # user_id -> set of connections (for targeted messages)
        self.user_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room: str, user_id: int = None):
        await websocket.accept()
        
        if room not in self.active_connections:
            self.active_connections[room] = set()
        self.active_connections[room].add(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, room: str, user_id: int = None):
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
    
    async def broadcast_to_room(self, room: str, message: dict):
        if room in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[room]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)
            
            # Cleanup disconnected
            for conn in disconnected:
                self.active_connections[room].discard(conn)
    
    async def notify_user(self, user_id: int, message: dict):
        """Send to specific user (e.g., cashier notification)"""
        if user_id in self.user_connections:
            for conn in self.user_connections[user_id]:
                await conn.send_json(message)
    
    # POS-specific helpers
    async def notify_order_update(self, order_id: int, data: dict):
        await self.broadcast_to_room(f"order_{order_id}", data)
        await self.broadcast_to_room("pos_floor", {"type": "order_changed", "order_id": order_id})
    
    async def notify_table_status(self, branch_id: int, table_id: int, status: str):
        await self.broadcast_to_room(
            f"branch_{branch_id}_floor", 
            {"type": "table_status", "table_id": table_id, "status": status}
        )
    
    async def notify_kitchen(self, branch_id: int, station_id: str, ticket_data: dict):
        await self.broadcast_to_room(
            f"branch_{branch_id}_kitchen_{station_id}",
            {"type": "new_ticket", "data": ticket_data}
        )

websocket_manager = ConnectionManager()