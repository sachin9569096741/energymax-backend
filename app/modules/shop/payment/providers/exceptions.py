class PaymentProviderError(Exception):
    """
    Base exception for all payment provider errors.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        code: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.code = code


class PaymentProviderConnectionError(PaymentProviderError):
    """
    Provider could not be reached or the request failed at network level.
    """

    pass


class PaymentProviderAuthenticationError(PaymentProviderError):
    """
    Provider rejected our credentials or authentication.
    """

    pass


class PaymentProviderValidationError(PaymentProviderError):
    """
    Provider rejected the request because of invalid parameters.
    """

    pass


class PaymentProviderSignatureError(PaymentProviderError):
    """
    Provider webhook/payment signature verification failed.
    """

    pass


class PaymentProviderTimeoutError(PaymentProviderError):
    """
    Provider request timed out.
    """

    pass


class PaymentProviderResponseError(PaymentProviderError):
    """
    Provider returned an unexpected or unusable response.
    """

    pass