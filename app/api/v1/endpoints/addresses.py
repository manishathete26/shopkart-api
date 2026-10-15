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
    address = Address(
        user_id=current_user.id,
        address=payload.address.strip(),
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
        raise HTTPException(status_code=404, detail="Address not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No address fields provided")
    if "address" in updates and updates["address"] is None:
        raise HTTPException(status_code=422, detail="Address cannot be null")

    for field, value in updates.items():
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
        raise HTTPException(status_code=404, detail="Address not found")

    db.delete(address)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
