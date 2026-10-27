import logging
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.admin.auth.models.admin_user import AdminUser
from app.modules.admin.auth.security.dependencies import get_current_admin
from app.modules.admin.notifications.services.notification import (
    NotificationService,
)
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.realtime.websocket_manager import websocket_manager
from app.db.session import SessionLocal
from app.modules.admin.auth.repositories.admin_user_repo import (
    AdminUserRepository,
)
from app.modules.admin.auth.security.jwt import (
    JWTError,
    decode_access_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/notifications",
    tags=["Admin Real-time Notifications"],
)


def authenticate_admin_token(
    token: str,
    db: Session,
):
    """
    Validate an admin access token using the existing JWT logic.
    """
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])

    except (JWTError, KeyError, TypeError, ValueError):
        return None

    user = AdminUserRepository(db).get_by_id(user_id)

    if user is None or not user.is_active:
        return None

    return user


@router.websocket("/ws")
async def admin_notifications_websocket(
    websocket: WebSocket,
):
    """
    WebSocket endpoint:
        /api/v1/admin/notifications/ws

    Authentication:
        Sec-WebSocket-Protocol: energymax-admin, <access-token>

    The server validates the token before accepting the connection.
    """
    offered_protocols = websocket.scope.get(
        "subprotocols",
        [],
    )

    if (
        len(offered_protocols) != 2
        or offered_protocols[0] != "energymax-admin"
    ):
        await websocket.close(code=1008)
        return

    token = offered_protocols[1]

    db = SessionLocal()
    admin = None

    try:
        admin = authenticate_admin_token(
            token=token,
            db=db,
        )

    except Exception:
        logger.exception(
            "Unexpected error authenticating admin WebSocket."
        )

    finally:
        db.close()

    if admin is None:
        await websocket.close(code=1008)
        return

    admin_id = admin.id

    # Accept using the application-specific subprotocol.
    await websocket_manager.connect(
        websocket,
        audience="admin",
        user_id=admin_id,
    )

    try:
        await websocket.send_json(
            {
                "event": "connection.established",
                "message": "Real-time notifications connected.",
            }
        )

        while True:
            # Keep the connection alive and detect disconnections.
            # Notifications are pushed independently by the manager.
            message = await websocket.receive_text()

            if message == "ping":
                await websocket.send_json(
                    {
                        "event": "pong",
                    }
                )

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception(
            "Admin notification WebSocket failed: admin_id=%s",
            admin_id,
        )

    finally:
        await websocket_manager.disconnect(
            websocket,
            audience="admin",
            user_id=admin_id,
        )


from fastapi import Depends, HTTPException, status

# Add the import for your existing get_current_admin dependency
from app.modules.admin.auth.security.dependencies import get_current_admin


from app.modules.admin.notifications.services.realtime_dispatcher import (
    dispatch_admin_notification,
)


@router.post("/test-realtime")
async def test_realtime_notification(
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)

    # 1. Create a persistent notification.
    notification = service.create_notification(
        admin_user_id=current_admin.id,
        notification_type="SYSTEM",
        title="Real-Time Test",
        message="EnergyMax database-backed notification test successful.",
        data={"source": "test-realtime"},
    )

    # 2. Commit before attempting WebSocket delivery.
    try:
        db.commit()
        db.refresh(notification)
    except Exception:
        db.rollback()
        raise

    # 3. Send the saved notification to the connected admin.
    delivered = await dispatch_admin_notification(
        admin_user_id=current_admin.id,
        notification=notification,
    )

    return {
        "success": True,
        "message": "Notification saved successfully.",
        "notification_public_id": notification.public_id,
        "persisted": True,
        "delivered": delivered,
    }