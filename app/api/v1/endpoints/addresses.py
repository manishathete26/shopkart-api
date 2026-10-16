from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....api.deps import get_current_user
from ....db.session import get_db
from ....models.address import Address
from ....models.auth import User
from ....schemas.address import AddressCreate, AddressRead, AddressUpdate

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressRead])
def get_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Address]:
    """Return only the authenticated user's saved addresses."""
    return db.scalars(
        select(Address)
        .where(Address.user_id == current_user.id)
        .order_by(Address.id.desc())
    ).all()


@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Address:
    street = payload.street.strip() if payload.street else None
    city = payload.city.strip() if payload.city else None
    state = payload.state.strip() if payload.state else None
    address_text = (
        payload.address.strip()
        if payload.address
        else ", ".join((street, city, state))
    )
    address = Address(
        user_id=current_user.id,
        address=address_text,
        street=street,
        city=city,
        state=state,
        pin=payload.pin.strip() if payload.pin else None,
        label=payload.label.strip() if payload.label else None,
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.patch("/{address_id}", response_model=AddressRead)
def update_address(
    address_id: int,
    payload: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Address:
    address = db.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
        )
    )
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No address fields provided")
    if "address" in updates and updates["address"] is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Address cannot be null")

    structured_fields = ("street", "city", "state")
    if any(field in updates for field in structured_fields):
        street = updates.get("street", address.street)
        city = updates.get("city", address.city)
        state = updates.get("state", address.state)
        if street is None or city is None or state is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Structured addresses require street, city, and state",
            )
        address.address = ", ".join((street, city, state))
    elif "address" in updates:
        address.street = None
        address.city = None
        address.state = None

    for field, value in updates.items():
        if field == "address" and any(part in updates for part in structured_fields):
            continue
        setattr(address, field, value.strip() if isinstance(value, str) else value)

    db.commit()
    db.refresh(address)
    return address


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    address = db.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
        )
    )
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    db.delete(address)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
