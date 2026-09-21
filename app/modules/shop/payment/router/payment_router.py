from fastapi import HTTPException

from app.core.config import settings
from app.modules.shop.payment.providers.base import PaymentProvider
from app.modules.shop.payment.providers.cashfree.adapter import CashfreeAdapter
from app.modules.shop.payment.providers.cashfree.client import CashfreeClient


class PaymentRouter:
    """
    Selects the configured payment provider.

    Provider-specific construction is kept inside this class so that
    the rest of the payment system remains provider-agnostic.
    """

    def __init__(self):
        self._providers: dict[str, PaymentProvider] = {}

        self._register_providers()

    def _register_providers(self) -> None:
        """
        Register the Cashfree payment provider.
        """

        self._providers["cashfree"] = CashfreeAdapter(
            client=CashfreeClient(
                app_id=settings.cashfree_app_id,
                secret_key=settings.cashfree_secret_key,
                environment=settings.cashfree_environment,
                api_version=settings.cashfree_api_version,
            ),
        )

    def get_provider(self, provider_name: str) -> PaymentProvider:
        """
        Return a configured payment provider by name.
        """

        provider = self._providers.get(provider_name)

        if provider is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Payment provider '{provider_name}' "
                    "is not available."
                ),
            )

        return provider