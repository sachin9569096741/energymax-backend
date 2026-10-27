
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manage authenticated WebSocket connections.

    Connections are isolated by audience and user ID.

    Examples:
        admin:1
        customer:1

    An admin and customer with the same numeric ID are
    treated as different users.

    Important:
        This manager uses in-memory connections and is suitable
        for a single application process. Multiple workers or
        application instances require a shared messaging layer
        such as Redis Pub/Sub.
    """

    ALLOWED_AUDIENCES = {"admin", "customer"}

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    @classmethod
    def _user_key(cls, audience: str, user_id: int) -> str:
        """
        Validate audience and user ID and return a connection key.
        """
        if audience not in cls.ALLOWED_AUDIENCES:
            raise ValueError(
                f"Unsupported WebSocket audience: {audience}"
            )

        if isinstance(user_id, bool) or not isinstance(user_id, int):
            raise ValueError("User ID must be an integer.")

        if user_id <= 0:
            raise ValueError("User ID must be positive.")

        return f"{audience}:{user_id}"

    # ---------------------------------------------------------
    # CONNECTION MANAGEMENT
    # ---------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        *,
        audience: str,
        user_id: int,
    ) -> None:
        """
        Accept and register a WebSocket connection.

        Authentication must happen before calling this method.
        """
        key = self._user_key(audience, user_id)

        await websocket.accept()

        async with self._lock:
            self._connections[key].add(websocket)

            active_connections = len(self._connections[key])

        logger.info(
            "WebSocket connected: audience=%s user_id=%s "
            "active_connections=%s",
            audience,
            user_id,
            active_connections,
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        *,
        audience: str,
        user_id: int,
    ) -> None:
        """
        Remove one WebSocket connection without affecting
        other connections belonging to the same user.
        """
        key = self._user_key(audience, user_id)

        async with self._lock:
            sockets = self._connections.get(key)

            if sockets is not None:
                sockets.discard(websocket)

                if not sockets:
                    self._connections.pop(key, None)

                remaining_connections = len(sockets)
            else:
                remaining_connections = 0

        logger.info(
            "WebSocket disconnected: audience=%s user_id=%s "
            "remaining_connections=%s",
            audience,
            user_id,
            remaining_connections,
        )

    # ---------------------------------------------------------
    # SEND TO ONE USER
    # ---------------------------------------------------------

    async def send_to_user(
        self,
        *,
        audience: str,
        user_id: int,
        message: dict[str, Any],
    ) -> int:
        """
        Send a JSON event to every active connection belonging
        to a specific user.

        Returns:
            Number of successful server-side send operations.

        Note:
            A successful send does not prove that the client
            processed or displayed the message.
        """
        key = self._user_key(audience, user_id)

        # Copy the connection list while holding the lock.
        # Do not hold the lock while sending network messages.
        async with self._lock:
            sockets = list(self._connections.get(key, set()))

        event_name = message.get("event", "unknown")

        logger.info(
            "Attempting WebSocket delivery: audience=%s "
            "user_id=%s active_sockets=%s event=%s",
            audience,
            user_id,
            len(sockets),
            event_name,
        )

        if not sockets:
            logger.warning(
                "No active WebSocket connections: "
                "audience=%s user_id=%s event=%s",
                audience,
                user_id,
                event_name,
            )
            return 0

        delivered = 0
        failed: list[WebSocket] = []

        for websocket in sockets:
            try:
                await websocket.send_json(message)
                delivered += 1

                logger.info(
                    "WebSocket message sent successfully: "
                    "audience=%s user_id=%s event=%s",
                    audience,
                    user_id,
                    event_name,
                )

            except WebSocketDisconnect:
                logger.warning(
                    "WebSocket disconnected during delivery: "
                    "audience=%s user_id=%s",
                    audience,
                    user_id,
                )
                failed.append(websocket)

            except (RuntimeError, OSError):
                logger.warning(
                    "WebSocket send failed: audience=%s user_id=%s",
                    audience,
                    user_id,
                    exc_info=True,
                )
                failed.append(websocket)

            except Exception:
                logger.exception(
                    "Unexpected WebSocket delivery failure: "
                    "audience=%s user_id=%s event=%s",
                    audience,
                    user_id,
                    event_name,
                )
                failed.append(websocket)

        # Clean up failed connections.
        for websocket in failed:
            await self.disconnect(
                websocket,
                audience=audience,
                user_id=user_id,
            )

        logger.info(
            "WebSocket delivery completed: audience=%s "
            "user_id=%s event=%s delivered=%s failed=%s",
            audience,
            user_id,
            event_name,
            delivered,
            len(failed),
        )

        return delivered

    # ---------------------------------------------------------
    # BROADCAST TO AN AUDIENCE
    # ---------------------------------------------------------

    async def broadcast(
        self,
        *,
        audience: str,
        message: dict[str, Any],
    ) -> int:
        """
        Broadcast an event to every connection in one audience.

        Use this only for events intended for every connected
        user in that audience.

        Returns:
            Number of successful server-side send operations.
        """
        if audience not in self.ALLOWED_AUDIENCES:
            raise ValueError(
                f"Unsupported WebSocket audience: {audience}"
            )

        prefix = f"{audience}:"
        event_name = message.get("event", "unknown")

        async with self._lock:
            recipients = [
                (key, list(sockets))
                for key, sockets in self._connections.items()
                if key.startswith(prefix)
            ]

        total_connections = sum(
            len(sockets) for _, sockets in recipients
        )

        logger.info(
            "Starting WebSocket broadcast: audience=%s "
            "connections=%s event=%s",
            audience,
            total_connections,
            event_name,
        )

        delivered = 0
        failed: list[tuple[str, WebSocket]] = []

        for key, sockets in recipients:
            for websocket in sockets:
                try:
                    await websocket.send_json(message)
                    delivered += 1

                except Exception:
                    logger.warning(
                        "Broadcast delivery failed: "
                        "connection_key=%s event=%s",
                        key,
                        event_name,
                        exc_info=True,
                    )
                    failed.append((key, websocket))

        # Remove failed connections.
        for key, websocket in failed:
            try:
                user_id = int(key.split(":", maxsplit=1)[1])

                await self.disconnect(
                    websocket,
                    audience=audience,
                    user_id=user_id,
                )

            except (ValueError, IndexError):
                logger.exception(
                    "Could not clean up failed WebSocket: key=%s",
                    key,
                )

        logger.info(
            "WebSocket broadcast completed: audience=%s "
            "event=%s delivered=%s failed=%s",
            audience,
            event_name,
            delivered,
            len(failed),
        )

        return delivered

    # ---------------------------------------------------------
    # CONNECTION STATUS
    # ---------------------------------------------------------

    async def is_connected(
        self,
        *,
        audience: str,
        user_id: int,
    ) -> bool:
        """
        Return True if the user has at least one registered socket.
        """
        key = self._user_key(audience, user_id)

        async with self._lock:
            return bool(self._connections.get(key))

    async def connection_count(
        self,
        *,
        audience: str,
        user_id: int,
    ) -> int:
        """
        Return the number of registered WebSocket connections
        for a specific user.
        """
        key = self._user_key(audience, user_id)

        async with self._lock:
            return len(self._connections.get(key, set()))


# -------------------------------------------------------------
# SHARED MANAGER INSTANCE
# -------------------------------------------------------------

websocket_manager = WebSocketManager()
