import resend

from app.core.config import settings


class EmailService:
    def __init__(self):
        resend.api_key = settings.resend_api_key

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
    ) -> None:
        resend.Emails.send(
            {
                "from": f"{settings.resend_from_name} <{settings.resend_from_email}>",
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )