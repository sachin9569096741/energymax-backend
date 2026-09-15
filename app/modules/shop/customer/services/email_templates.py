def build_customer_otp_email(otp_code: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>EnergyMax OTP</title>
    </head>
    <body>
        <div>
            <h2>EnergyMax Verification Code</h2>

            <p>Your verification code is:</p>

            <h1>{otp_code}</h1>

            <p>
                This OTP is valid for 10 minutes.
            </p>

            <p>
                If you did not request this code, please ignore this email.
            </p>

            <p>
                Regards,<br>
                EnergyMax Team
            </p>
        </div>
    </body>
    </html>
    """