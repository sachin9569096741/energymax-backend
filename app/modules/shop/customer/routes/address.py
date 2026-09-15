from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.repositories.customer_address import (
    CustomerAddressRepository,
)
from app.modules.shop.customer.schemas.address import (
    CustomerAddressCreateRequest,
    CustomerAddressListResponse,
    CustomerAddressResponse,
    CustomerAddressUpdateRequest,
)
from app.modules.shop.customer.security.dependencies import get_current_customer
from app.modules.shop.customer.services.customer_address import (
    CustomerAddressService,
)

router = APIRouter(
    prefix="/customer/addresses",
    tags=["Shop - Customer Addresses"],
)


@router.get(
    "",
    response_model=CustomerAddressListResponse,
)
def list_addresses(
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerAddressRepository(db)
    service = CustomerAddressService(repository)

    addresses = service.list_addresses(current_customer)

    return CustomerAddressListResponse(
        addresses=[
            CustomerAddressResponse.model_validate(address)
            for address in addresses
        ]
    )


@router.post(
    "",
    response_model=CustomerAddressResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_address(
    data: CustomerAddressCreateRequest,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerAddressRepository(db)
    service = CustomerAddressService(repository)

    address = service.create_address(
        customer=current_customer,
        data=data,
    )

    db.commit()
    db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


@router.patch(
    "/{public_id}",
    response_model=CustomerAddressResponse,
)
def update_address(
    public_id: str,
    data: CustomerAddressUpdateRequest,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerAddressRepository(db)
    service = CustomerAddressService(repository)

    address = service.update_address(
        customer=current_customer,
        public_id=public_id,
        data=data,
    )

    db.commit()
    db.refresh(address)

    return CustomerAddressResponse.model_validate(address)


@router.delete(
    "/{public_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_address(
    public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerAddressRepository(db)
    service = CustomerAddressService(repository)

    service.delete_address(
        customer=current_customer,
        public_id=public_id,
    )

    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{public_id}/default",
    response_model=CustomerAddressResponse,
)
def set_default_address(
    public_id: str,
    current_customer=Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerAddressRepository(db)
    service = CustomerAddressService(repository)

    address = service.set_default_address(
        customer=current_customer,
        public_id=public_id,
    )

    db.commit()
    db.refresh(address)

    return CustomerAddressResponse.model_validate(address)