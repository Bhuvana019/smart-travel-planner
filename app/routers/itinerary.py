from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Itinerary, Trip, User
from app.schemas import ItineraryCreate, ItineraryUpdate, ItineraryOut
from app.auth import get_current_user

router = APIRouter(tags=["Itinerary"])

@router.post("/api/trips/{trip_id}/itinerary", response_model=ItineraryOut, status_code=status.HTTP_201_CREATED)
def add_itinerary_item(
    trip_id: int,
    item_data: ItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a new activity to the specified trip itinerary."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to add activities to this trip")

    # Avoid duplicate itinerary entries when a user adds the same experience repeatedly
    existing_item = db.query(Itinerary).filter(
        Itinerary.trip_id == trip.trip_id,
        Itinerary.activity == item_data.activity.strip()
    ).first()
    if existing_item:
        return ItineraryOut.model_validate(existing_item)

    cat = item_data.category.strip() if item_data.category else "General"

    new_item = Itinerary(
        trip_id=trip.trip_id,
        date=item_data.date,
        time=item_data.time.strip(),
        activity=item_data.activity.strip(),
        location=item_data.location.strip() if item_data.location else "",
        category=cat,
        estimated_cost=float(item_data.estimated_cost),
        notes=item_data.notes.strip() if item_data.notes else ""
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return ItineraryOut.model_validate(new_item)

@router.get("/api/trips/{trip_id}/itinerary", response_model=List[ItineraryOut])
def get_trip_itinerary(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all activities for a trip, sorted chronologically by date and time."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view this trip's itinerary")

    items = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).order_by(Itinerary.date.asc(), Itinerary.time.asc()).all()
    return [ItineraryOut.model_validate(i) for i in items]

@router.put("/api/itinerary/{item_id}", response_model=ItineraryOut)
def update_itinerary_item(
    item_id: int,
    item_update: ItineraryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an existing itinerary activity."""
    item = db.query(Itinerary).filter(Itinerary.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found")
    if item.trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this itinerary item")

    if item_update.date is not None:
        item.date = item_update.date
    if item_update.time is not None:
        item.time = item_update.time.strip()
    if item_update.activity is not None:
        item.activity = item_update.activity.strip()
    if item_update.location is not None:
        item.location = item_update.location.strip()
    if item_update.category is not None:
        item.category = item_update.category.strip()
    if item_update.estimated_cost is not None:
        item.estimated_cost = float(item_update.estimated_cost)
    if item_update.notes is not None:
        item.notes = item_update.notes.strip()

    db.commit()
    db.refresh(item)
    return ItineraryOut.model_validate(item)

@router.delete("/api/itinerary/{item_id}", status_code=status.HTTP_200_OK)
def delete_itinerary_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an activity from the itinerary."""
    item = db.query(Itinerary).filter(Itinerary.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found")
    if item.trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this itinerary item")

    db.delete(item)
    db.commit()
    return {"message": "Itinerary item deleted successfully", "item_id": item_id}
