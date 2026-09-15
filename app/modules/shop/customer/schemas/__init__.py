from app.modules.shop.customer.schemas.auth import (
    CustomerAuthResponse,
    CustomerLoginRequest,
    CustomerOTPRequest,
    CustomerOTPResponse,
    CustomerOTPVerifyRequest,
    CustomerRegisterRequest,
    CustomerResponse,
)
from app.modules.shop.customer.schemas.address import (
    CustomerAddressCreateRequest,
    CustomerAddressUpdateRequest,
    CustomerAddressResponse,
    CustomerAddressListResponse,
)

__all__ = [
    "CustomerRegisterRequest",
    "CustomerLoginRequest",
    "CustomerOTPRequest",
    "CustomerOTPVerifyRequest",
    "CustomerResponse",
    "CustomerAuthResponse",
    "CustomerOTPResponse",
    "CustomerAddressCreateRequest",
    "CustomerAddressUpdateRequest",
    "CustomerAddressResponse",
    "CustomerAddressListResponse",
]