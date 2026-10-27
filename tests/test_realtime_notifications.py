
import asyncio
import json
import os

import httpx
import websockets


BASE_URL = os.getenv(
    "ENERGYMAX_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

WS_URL = BASE_URL.replace("https://", "wss://").replace(
    "http://", "ws://"
)

ADMIN_TOKEN = os.getenv("ENERGYMAX_ADMIN_TOKEN", "")


async def main():
    if not ADMIN_TOKEN:
        print("ERROR: Set ENERGYMAX_ADMIN_TOKEN first.")
        return

    ws_url = f"{WS_URL}/api/v1/admin/notifications/ws"
    test_url = (
        f"{BASE_URL}/api/v1/admin/notifications/test-realtime"
    )

    print("\n1. Connecting to admin WebSocket...")

    try:
        async with websockets.connect(
            ws_url,
            subprotocols=["energymax-admin", ADMIN_TOKEN],
            open_timeout=10,
            close_timeout=5,
        ) as websocket:

            print("PASS: WebSocket connected.")
            print("2. Waiting for connection confirmation...")

            confirmation = json.loads(
                await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5,
                )
            )

            print("Received:", confirmation)

            if confirmation.get("event") != "connection.established":
                print("FAIL: Unexpected connection confirmation.")
                return

            print("PASS: Connection confirmed.")

            print("3. Triggering backend test notification...")

            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    test_url,
                    headers={
                        "Authorization": f"Bearer {ADMIN_TOKEN}",
                    },
                )

            print("HTTP status:", response.status_code)
            print("API response:", response.text)

            if response.status_code != 200:
                print("FAIL: Test endpoint returned an error.")
                return

            try:
                result = response.json()
            except ValueError:
                print("FAIL: API returned invalid JSON.")
                return

            # Match the field actually returned by the API.
            delivered = result.get("delivered", 0)

            if delivered < 1:
                print(
                    "FAIL: Backend did not report a successful "
                    "WebSocket send."
                )
                return

            print(
                f"PASS: Backend reports {delivered} "
                "successful WebSocket send(s)."
            )

            print("4. Waiting for the live notification...")

            event = json.loads(
                await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5,
                )
            )

            print("Received event:", json.dumps(event, indent=2))

            if event.get("event") == "notification.test":
                print(
                    "\nSUCCESS: Real-time notification delivered!"
                )
            else:
                print(
                    "\nFAIL: Received an unexpected event: "
                    f"{event.get('event')}"
                )

    except asyncio.TimeoutError:
        print(
            "FAIL: Timed out waiting for a WebSocket message. "
            "Check the server logs and connection state."
        )

    except websockets.exceptions.WebSocketException as exc:
        print(f"FAIL: WebSocket error: {exc}")

    except httpx.HTTPError as exc:
        print(f"FAIL: HTTP request error: {exc}")

    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
