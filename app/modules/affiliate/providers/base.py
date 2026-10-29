from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class PayoutProviderStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PayoutRequest:
    withdrawal_public_id: str
    amount: Decimal
    currency: str
    beneficiary_reference: str
    idempotency_key: str


@dataclass(frozen=True)
class PayoutResult:
    provider: str
    provider_reference: str | None
    status: PayoutProviderStatus
    message: str | None = None


class PayoutProvider(ABC):
    """
    Contract implemented by Cashfree or another payout provider.

    This interface contains no provider credentials and makes
    no external network requests.
    """

    @abstractmethod
    def initiate_payout(
        self,
        request: PayoutRequest,
    ) -> PayoutResult:
        """Initiate a transfer using the provider's API."""
        raise NotImplementedError

    @abstractmethod
    def get_payout_status(
        self,
        provider_reference: str,
    ) -> PayoutResult:
        """Fetch the latest transfer status from the provider."""
        raise NotImplementedError