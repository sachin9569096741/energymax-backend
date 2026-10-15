
from app.core.shiprocket import ShiprocketClient, ShiprocketError

try:
    client = ShiprocketClient()
    token = client._get_token()

    print("Shiprocket authentication: SUCCESS")
    print("Bearer token received:", bool(token))
    print("Token value: [HIDDEN]")

except ShiprocketError as exc:
    print("Shiprocket authentication: FAILED")
    print("Reason:", exc)
