from fastapi import HTTPException

from app.core.config import settings
from app.modules.shop.payment.providers.base import PaymentProvider
from app.modules.shop.payment.providers.razorpay.adapter import RazorpayAdapter
from app.modules.shop.payment.providers.razorpay.client import RazorpayClient


class PaymentRouter:
    """
    Selects the appropriate payment provider.

    Provider-specific construction is kept inside this class so that
    the rest of the payment system remains provider-agnostic.
    """

    def __init__(self):
        self._providers: dict[str, PaymentProvider] = {}

        self._register_providers()

    def _register_providers(self) -> None:
        """
        Register all currently configured payment providers.
        """

        self._providers["razorpay"] = RazorpayAdapter(
            client=RazorpayClient(
                key_id=settings.razorpay_key_id,
                key_secret=settings.razorpay_key_secret,
            ),
            webhook_secret=settings.razorpay_webhook_secret,
        )

    def get_provider(self, provider_name: str) -> PaymentProvider:
        """
        Return a configured payment provider by name.
        """

        provider = self._providers.get(provider_name)

        if provider is None:
            raise HTTPException(
                status_code=400,
                detail=f"Payment provider '{provider_name}' is not available.",
            )

        return provider