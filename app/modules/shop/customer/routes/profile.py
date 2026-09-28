from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.repositories.customer_profile import (
    CustomerProfileRepository,
)
from app.modules.shop.customer.schemas.profile import (
    CustomerProfileResponse,
    CustomerProfileUpdateRequest,
)
from app.modules.shop.customer.security.dependencies import (
    get_current_customer,
)
from app.modules.shop.customer.services.customer_profile import (
    CustomerProfileService,
)


router = APIRouter(
    prefix="/customer/profile",
    tags=["Shop - Customer Profile"],
)


@router.get(
    "",
    response_model=CustomerProfileResponse,
)
def get_customer_profile(
    current_customer: Customer = Depends(get_current_customer),
):
    return current_customer


@router.put(
    "",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_200_OK,
)
def update_customer_profile(
    data: CustomerProfileUpdateRequest,
    current_customer: Customer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    repository = CustomerProfileRepository(db)
    service = CustomerProfileService(repository)

    customer = service.update_profile(
        customer=current_customer,
        data=data,
    )

    db.commit()
    db.refresh(customer)

    return customer