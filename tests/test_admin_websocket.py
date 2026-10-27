
import asyncio
import os
import websockets

WS_URL = "ws://127.0.0.1:8000/api/v1/admin/notifications/ws"


async def main():
    token = os.getenv("ADMIN_ACCESS_TOKEN")

    if not token:
        print("Set ADMIN_ACCESS_TOKEN to your admin JWT access token.")
        return

    try:
        async with websockets.connect(
            WS_URL,
            subprotocols=["energymax-admin", token],
        ) as websocket:
            print("WebSocket connected successfully.")

            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=10,
            )
            print("Server response:", response)

            print("\nConnection is active.")
            print("Now call POST /api/v1/admin/notifications/test-realtime")
            print("Waiting for the notification...")

            while True:
                message = await websocket.recv()
                print("Received event:", message)

    except Exception as exc:
        print(f"WebSocket test failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
