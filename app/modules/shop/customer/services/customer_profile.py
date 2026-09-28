from fastapi import HTTPException, status

from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.repositories.customer_profile import (
    CustomerProfileRepository,
)
from app.modules.shop.customer.schemas.profile import (
    CustomerProfileUpdateRequest,
)


class CustomerProfileService:
    def __init__(self, repository: CustomerProfileRepository):
        self.repository = repository

    def update_profile(
        self,
        customer: Customer,
        data: CustomerProfileUpdateRequest,
    ) -> Customer:

        # Normalize incoming values
        first_name = (
            data.first_name.strip()
            if data.first_name is not None
            else None
        )

        last_name = (
            data.last_name.strip()
            if data.last_name is not None
            else None
        )

        email = (
            str(data.email).strip().lower()
            if data.email is not None
            else None
        )

        phone = (
            data.phone.strip()
            if data.phone is not None
            else None
        )

        # Validate first name
        if first_name == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First name cannot be empty.",
            )

        # Validate last name
        if last_name == "":
            last_name = None

        # Check email uniqueness
        if email is not None and email != customer.email:
            existing_customer = self.repository.get_customer_by_email(
                email=email,
                exclude_customer_id=customer.id,
            )

            if existing_customer:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email is already registered.",
                )

            customer.email_verified = False

        # Check phone uniqueness
        if phone is not None and phone != customer.phone:
            existing_customer = self.repository.get_customer_by_phone(
                phone=phone,
                exclude_customer_id=customer.id,
            )

            if existing_customer:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number is already registered.",
                )

            customer.phone_verified = False

        # Apply changes
        if first_name is not None:
            customer.first_name = first_name

        if data.last_name is not None:
            customer.last_name = last_name

        if data.email is not None:
            customer.email = email

        if data.phone is not None:
            customer.phone = phone

        return self.repository.save(customer)