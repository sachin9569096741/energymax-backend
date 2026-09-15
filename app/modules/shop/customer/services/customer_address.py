from uuid import uuid4

from fastapi import HTTPException, status

from app.modules.shop.customer.models.customer import Customer
from app.modules.shop.customer.models.customer_address import CustomerAddress
from app.modules.shop.customer.repositories.customer_address import (
    CustomerAddressRepository,
)
from app.modules.shop.customer.schemas.address import (
    CustomerAddressCreateRequest,
    CustomerAddressUpdateRequest,
)


class CustomerAddressService:
    def __init__(self, repository: CustomerAddressRepository):
        self.repository = repository

    def list_addresses(
        self,
        customer: Customer,
    ) -> list[CustomerAddress]:
        return self.repository.get_customer_addresses(customer.id)

    def create_address(
        self,
        customer: Customer,
        data: CustomerAddressCreateRequest,
    ) -> CustomerAddress:
        if data.is_default:
            self.repository.clear_default_address(customer.id)

        address = CustomerAddress(
            public_id=str(uuid4()),
            customer_id=customer.id,
            label=data.label.strip(),
            recipient_name=data.recipient_name.strip(),
            phone=self._normalize_phone(data.phone),
            address_line1=data.address_line1.strip(),
            address_line2=(
                data.address_line2.strip()
                if data.address_line2
                else None
            ),
            landmark=(
                data.landmark.strip()
                if data.landmark
                else None
            ),
            city=data.city.strip(),
            state=data.state.strip(),
            postal_code=data.postal_code.strip(),
            country=data.country.strip(),
            is_default=data.is_default,
            is_active=True,
        )

        self.repository.create(address)

        return address

    def update_address(
        self,
        customer: Customer,
        public_id: str,
        data: CustomerAddressUpdateRequest,
    ) -> CustomerAddress:
        address = self._get_address(
            customer=customer,
            public_id=public_id,
        )

        update_data = data.model_dump(exclude_unset=True)

        if update_data.get("is_default") is True:
            self.repository.clear_default_address(customer.id)

        if "phone" in update_data:
            update_data["phone"] = self._normalize_phone(
                update_data["phone"]
            )

        string_fields = {
            "label",
            "recipient_name",
            "address_line1",
            "address_line2",
            "landmark",
            "city",
            "state",
            "postal_code",
            "country",
        }

        for field_name in string_fields:
            if field_name in update_data:
                value = update_data[field_name]

                if value is not None:
                    update_data[field_name] = value.strip()

        for field_name, value in update_data.items():
            setattr(address, field_name, value)

        self.repository.save()

        return address

    def delete_address(
        self,
        customer: Customer,
        public_id: str,
    ) -> None:
        address = self._get_address(
            customer=customer,
            public_id=public_id,
        )

        address.is_active = False
        address.is_default = False

        self.repository.save()

    def set_default_address(
        self,
        customer: Customer,
        public_id: str,
    ) -> CustomerAddress:
        address = self._get_address(
            customer=customer,
            public_id=public_id,
        )

        self.repository.clear_default_address(customer.id)

        address.is_default = True

        self.repository.save()

        return address

    def _get_address(
        self,
        customer: Customer,
        public_id: str,
    ) -> CustomerAddress:
        address = self.repository.get_by_public_id(
            public_id=public_id,
            customer_id=customer.id,
        )

        if address is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found.",
            )

        return address

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        return phone.strip().replace(" ", "").replace("-", "")