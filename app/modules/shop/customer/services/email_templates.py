from html import escape


def build_order_confirmation_email(order, payment) -> str:
    """Build the EnergyMaxGlobal order confirmation email."""

    def safe(value, default="—"):
        return escape(str(value if value is not None else default))

    items_html = ""

    for item in order.items:
        items_html += f"""
        <tr>
            <td style="padding:12px;border-bottom:1px solid #e5eee8;">
                {safe(item.product_name)}
            </td>
            <td style="padding:12px;text-align:center;border-bottom:1px solid #e5eee8;">
                {safe(item.quantity)}
            </td>
            <td style="padding:12px;text-align:right;border-bottom:1px solid #e5eee8;">
                ₹{safe(item.unit_price)}
            </td>
            <td style="padding:12px;text-align:right;border-bottom:1px solid #e5eee8;">
                ₹{safe(item.subtotal)}
            </td>
        </tr>
        """

    address = order.shipping_address_snapshot or {}

    address_parts = [
        address.get("recipient_name"),
        address.get("address_line1"),
        address.get("address_line2"),
        address.get("landmark"),
        ", ".join(
            str(value)
            for value in (
                address.get("city"),
                address.get("state"),
                address.get("postal_code"),
            )
            if value
        ),
        address.get("country"),
        f"Phone: {address['phone']}" if address.get("phone") else None,
    ]

    address_html = "<br>".join(
        safe(part) for part in address_parts if part
    )

    customer_name = safe(order.customer_name, "Customer")
    order_number = safe(order.order_number)
    payment_reference = safe(
        payment.provider_payment_id or payment.public_id
    )
    provider = safe(payment.provider, "Online payment")
    currency = safe(payment.currency, "INR")

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Order Confirmed | EnergyMaxGlobal</title>
</head>
<body style="margin:0;padding:24px 8px;background:#f2f6f3;
             font-family:Arial,Helvetica,sans-serif;color:#172b22;">

<table role="presentation" width="100%" cellspacing="0" cellpadding="0">
<tr><td align="center">

<table role="presentation" width="100%" cellspacing="0" cellpadding="0"
       style="max-width:680px;background:#ffffff;border-radius:12px;
              overflow:hidden;">

    <tr>
        <td style="padding:28px 30px;">
            <div style="font-size:28px;font-weight:800;color:#064b35;">
                EnergyMax<span style="color:#36a852;">Global</span>
            </div>
            <div style="font-size:11px;letter-spacing:3px;color:#54836b;
                        margin-top:5px;">
                FUEL YOUR BETTER YOU
            </div>
        </td>
    </tr>

    <tr>
        <td style="padding:28px 30px;background:#eaf7ed;">
            <div style="font-size:28px;font-weight:700;color:#075637;">
                ✓ Your Order is Confirmed!
            </div>
            <p>Hi {customer_name},</p>
            <p style="line-height:1.7;">
                Thank you for shopping with EnergyMaxGlobal.
                Your payment was successful and your order is confirmed.
                We'll keep you updated on your order.
            </p>
        </td>
    </tr>

    <tr>
        <td style="padding:24px 30px;">
            <p style="margin:0 0 8px;color:#66756c;">ORDER NUMBER</p>
            <div style="font-size:20px;font-weight:700;">
                {order_number}
            </div>

            <p style="margin:20px 0 6px;color:#66756c;">PAYMENT STATUS</p>
            <span style="color:#16803c;font-weight:700;">
                Successful
            </span>

            <p style="margin:20px 0 6px;color:#66756c;">PAYMENT METHOD</p>
            <div>{provider}</div>

            <p style="margin:20px 0 6px;color:#66756c;">
                PAYMENT REFERENCE
            </p>
            <div>{payment_reference}</div>
        </td>
    </tr>

    <tr>
        <td style="padding:0 30px 24px;">
            <h2 style="font-size:20px;">Order Items</h2>

            <table role="presentation" width="100%" cellspacing="0"
                   cellpadding="0"
                   style="border-collapse:collapse;font-size:13px;">
                <thead>
                    <tr style="background:#edf2ef;">
                        <th align="left" style="padding:12px;">Product</th>
                        <th align="center" style="padding:12px;">Qty</th>
                        <th align="right" style="padding:12px;">Price</th>
                        <th align="right" style="padding:12px;">Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <table role="presentation" width="100%" cellspacing="0"
                   cellpadding="0"
                   style="margin-top:20px;line-height:2;">
                <tr>
                    <td>Subtotal</td>
                    <td align="right">₹{safe(order.subtotal)}</td>
                </tr>
                <tr>
                    <td>Discount</td>
                    <td align="right">₹{safe(order.discount_amount)}</td>
                </tr>
                <tr>
                    <td>Shipping</td>
                    <td align="right">₹{safe(order.shipping_amount)}</td>
                </tr>
                <tr>
                    <td>Tax</td>
                    <td align="right">₹{safe(order.tax_amount)}</td>
                </tr>
                <tr>
                    <td style="padding-top:12px;border-top:1px solid #dce8df;
                               font-size:18px;font-weight:700;">
                        Total Paid
                    </td>
                    <td align="right"
                        style="padding-top:12px;border-top:1px solid #dce8df;
                               font-size:20px;font-weight:700;color:#087443;">
                        {currency} {safe(payment.amount)}
                    </td>
                </tr>
            </table>
        </td>
    </tr>

    <tr>
        <td style="padding:0 30px 28px;">
            <h2 style="font-size:20px;">Shipping Address</h2>
            <div style="line-height:1.8;">{address_html}</div>
        </td>
    </tr>

    <tr>
        <td style="padding:24px 30px;background:#eaf5ed;">
            <strong style="font-size:18px;">Need Help?</strong>
            <p style="line-height:1.7;">
                If you have questions about your order, please contact
                our support team.
            </p>
            <div>EnergyMaxGlobal Support</div>
        </td>
    </tr>

    <tr>
        <td style="padding:24px 30px;background:#063e2d;color:#ffffff;">
            <div style="font-size:23px;font-weight:800;">
                EnergyMaxGlobal
            </div>
            <p style="font-size:12px;line-height:1.7;">
                Fuel Your Better You<br>
                Thank you for choosing EnergyMaxGroup.
            </p>
            <div style="font-size:11px;color:#c9dfd1;">
                © 2026 EnergyMaxGroup. All rights reserved.
            </div>
        </td>
    </tr>

</table>
</td></tr>
</table>

</body>
</html>
"""



def build_customer_otp_email(otp_code: str, purpose: str = "registration") -> str:
    """Build the customer email verification OTP template."""

    safe_code = escape(str(otp_code))

    if purpose == "registration":
        heading = "Verify your email address"
        message = "Use this code to verify your email and activate your customer account."
    else:
        heading = "Your verification code"
        message = "Use this code to complete your requested verification."

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading} | EnergyMaxGroup</title>
</head>
<body style="margin:0;padding:24px;background:#f2f6f3;
             font-family:Arial,Helvetica,sans-serif;color:#172b22;">
    <div style="max-width:560px;margin:auto;background:#ffffff;
                padding:32px;border-radius:12px;">
        <h1 style="color:#075637;">EnergyMaxGroup</h1>
        <h2>{heading}</h2>
        <p>{message}</p>
        <div style="padding:20px;text-align:center;background:#eaf7ed;
                    border-radius:8px;font-size:32px;font-weight:bold;
                    letter-spacing:8px;color:#075637;">
            {safe_code}
        </div>
        <p>This code expires in 10 minutes.</p>
        <p>If you did not request this code, you can ignore this email.</p>
        <p style="font-size:12px;color:#66756c;">
            © 2026 EnergyMaxGroup. All rights reserved.
        </p>
    </div>
</body>
</html>
"""


def build_customer_verification_link_email(
    verification_url: str,
) -> str:
    """Build the customer email verification-link template."""

    safe_url = escape(verification_url, quote=True)

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email | EnergyMaxGroup</title>
</head>
<body style="margin:0;padding:24px;background:#f2f6f3;
             font-family:Arial,Helvetica,sans-serif;color:#172b22;">
    <div style="max-width:560px;margin:auto;background:#ffffff;
                padding:32px;border-radius:12px;">
        <h1 style="color:#075637;">EnergyMaxGroup</h1>
        <h2>Verify your email address</h2>
        <p>
            Welcome to EnergyMaxGroup! Confirm your email address
            to activate your customer account.
        </p>
        <p style="text-align:center;margin:32px 0;">
            <a href="{safe_url}"
               style="display:inline-block;padding:14px 28px;
                      background:#087443;color:#ffffff;
                      text-decoration:none;border-radius:8px;
                      font-weight:bold;">
                Verify Email Address
            </a>
        </p>
        <p>This verification link expires in 10 minutes and can only
           be used once.</p>
        <p>If you did not create this account, you can ignore this email.</p>
        <p style="font-size:12px;color:#66756c;">
            &copy; 2026 EnergyMaxGroup. All rights reserved.
        </p>
    </div>
</body>
</html>
"""
