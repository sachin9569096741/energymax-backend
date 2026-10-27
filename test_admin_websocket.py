
import asyncio
import os
import websockets

WS_URL = "ws://127.0.0.1:8000/api/v1/admin/notifications/ws"


async def main():
    token = os.getenv("ADMIN_ACCESS_TOKEN")

    if not token:
        print("ERROR: ADMIN_ACCESS_TOKEN environment variable is missing.")
        return

    try:
        async with websockets.connect(
            WS_URL,
            subprotocols=["energymax-admin", token],
        ) as websocket:

            print("WebSocket connected successfully!")

            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=10,
            )
            print("Server response:", response)

            print("\nWaiting for real-time notifications...")
            print("Now execute the test endpoint in Swagger.")

            while True:
                message = await websocket.recv()
                print("\nNotification received:")
                print(message)

    except Exception as exc:
        print(f"\nWebSocket error: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())