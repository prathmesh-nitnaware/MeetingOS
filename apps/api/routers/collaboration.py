import asyncio
import json
import logging
from typing import Any

from apps.api.auth import UserIdentity, require_viewer
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Real-time Collaboration"])


class ActiveViewer(BaseModel):
    user_id: str
    user_name: str
    email: str | None = None
    joined_at: str


class PresenceManager:
    """In-memory presence and real-time review broadcast manager per meeting."""

    def __init__(self) -> None:
        # room_id (meeting_id) -> dict of websocket -> viewer info
        self._rooms: dict[str, dict[WebSocket, dict[str, Any]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, meeting_id: str, websocket: WebSocket, viewer: dict[str, Any]) -> list[dict[str, Any]]:
        await websocket.accept()
        async with self._lock:
            if meeting_id not in self._rooms:
                self._rooms[meeting_id] = {}
            self._rooms[meeting_id][websocket] = viewer
            viewers = list(self._rooms[meeting_id].values())

        # Broadcast user joined to other viewers
        await self.broadcast(meeting_id, {
            "type": "presence_update",
            "event": "user_joined",
            "user": viewer,
            "active_viewers": viewers,
        }, exclude=websocket)

        return viewers

    async def disconnect(self, meeting_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if meeting_id in self._rooms and websocket in self._rooms[meeting_id]:
                leaving_user = self._rooms[meeting_id].pop(websocket, None)
                if not self._rooms[meeting_id]:
                    del self._rooms[meeting_id]
                viewers = list(self._rooms[meeting_id].values()) if meeting_id in self._rooms else []
            else:
                leaving_user = None
                viewers = []

        if leaving_user:
            await self.broadcast(meeting_id, {
                "type": "presence_update",
                "event": "user_left",
                "user": leaving_user,
                "active_viewers": viewers,
            })

    async def broadcast(self, meeting_id: str, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        async with self._lock:
            room_sockets = list(self._rooms.get(meeting_id, {}).keys())

        payload = json.dumps(message)
        for ws in room_sockets:
            if ws != exclude:
                try:
                    await ws.send_text(payload)
                except Exception as e:
                    logger.debug(f"Failed to send to websocket: {e}")

    def get_viewers(self, meeting_id: str) -> list[dict[str, Any]]:
        return list(self._rooms.get(meeting_id, {}).values())


presence_manager = PresenceManager()


@router.get("/meetings/{meeting_id}/presence", response_model=list[dict[str, Any]])
async def get_meeting_presence(
    meeting_id: str,
    _user: UserIdentity = Depends(require_viewer),
) -> list[dict[str, Any]]:
    """Get list of active live viewers currently in this meeting workspace."""
    return presence_manager.get_viewers(meeting_id)


@router.websocket("/ws/meetings/{meeting_id}")
async def meeting_collaboration_websocket(
    websocket: WebSocket,
    meeting_id: str,
) -> None:
    """WebSocket endpoint providing real-time presence indicators and live human review sync."""
    from datetime import UTC, datetime

    # Query params for user info
    user_name = websocket.query_params.get("user_name", "Team Member")
    user_id = websocket.query_params.get("user_id", "guest")
    email = websocket.query_params.get("email", "")

    viewer_info = {
        "user_id": user_id,
        "user_name": user_name,
        "email": email,
        "joined_at": datetime.now(UTC).isoformat(),
    }

    active_viewers = await presence_manager.connect(meeting_id, websocket, viewer_info)

    # Send initial state to joining user
    await websocket.send_text(json.dumps({
        "type": "initial_presence",
        "active_viewers": active_viewers,
    }))

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                msg_type = data.get("type")

                if msg_type == "review_action":
                    # Broadcast human review action (confirm/reject/edit) in real-time
                    await presence_manager.broadcast(meeting_id, {
                        "type": "review_sync",
                        "entity_type": data.get("entity_type"),
                        "entity_id": data.get("entity_id"),
                        "review_status": data.get("review_status"),
                        "actor_name": user_name,
                    }, exclude=websocket)

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        await presence_manager.disconnect(meeting_id, websocket)
    except Exception as e:
        logger.debug(f"WebSocket error for meeting {meeting_id}: {e}")
        await presence_manager.disconnect(meeting_id, websocket)
