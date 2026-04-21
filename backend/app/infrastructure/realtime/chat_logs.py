from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState


@dataclass(frozen=True)
class ChatProcessingEvent:
    conversation_id: str
    category: str
    stage: str
    status: str
    payload: dict[str, Any]
    workspace_id: str | None = None
    message_id: str | None = None
    event_id: str | None = None
    timestamp: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id or str(uuid4()),
            "conversation_id": self.conversation_id,
            "workspace_id": self.workspace_id,
            "message_id": self.message_id,
            "category": self.category,
            "stage": self.stage,
            "status": self.status,
            "event": f"{self.category}.{self.stage}",
            "timestamp": self.timestamp or datetime.now(UTC).isoformat(),
            "payload": self.payload,
        }


class ChatLogConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, *, conversation_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(conversation_id, set()).add(websocket)

    def disconnect(self, *, conversation_id: str, websocket: WebSocket) -> None:
        sockets = self._connections.get(conversation_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(conversation_id, None)

    async def keepalive(self, *, conversation_id: str, websocket: WebSocket) -> None:
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            self.disconnect(conversation_id=conversation_id, websocket=websocket)

    async def publish(self, event: ChatProcessingEvent) -> None:
        payload = event.as_dict()
        sockets = list(self._connections.get(event.conversation_id, set()))
        stale: list[WebSocket] = []

        for socket in sockets:
            if socket.client_state != WebSocketState.CONNECTED:
                stale.append(socket)
                continue
            try:
                await socket.send_json(payload)
            except RuntimeError:
                stale.append(socket)

        for socket in stale:
            self.disconnect(conversation_id=event.conversation_id, websocket=socket)


chat_log_manager = ChatLogConnectionManager()
