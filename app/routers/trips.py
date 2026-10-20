from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trip, User, Expense, Itinerary, SavedExperience
from app.schemas import TripCreate, TripUpdate, TripOut, TripDetailOut, TripSummaryOut, ItineraryOut, ExpenseOut, SavedExperienceOut
from app.auth import get_current_user
from app.services.budget_service import calculate_trip_budget

router = APIRouter(prefix="/api/trips", tags=["Trips"])

def _format_interests(interests_input: Union[List[str], str, None]) -> str:
    """Standardizes interests as a comma-separated string."""
    if not interests_input:
        return ""
    if isinstance(interests_input, list):
        return ", ".join([i.strip() for i in interests_input if i.strip()])
    return str(interests_input).strip()

def _parse_interests_list(interests_str: str) -> List[str]:
    """Parses a comma-separated interests string into a clean list."""
    if not interests_str:
        return []
    return [i.strip() for i in interests_str.split(",") if i.strip()]

@router.post("", response_model=TripOut, status_code=status.HTTP_201_CREATED)
def create_trip(
    trip_data: TripCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new travel trip for the current user."""
    interests_str = _format_interests(trip_data.interests)
    t_name = trip_data.trip_name.strip() if trip_data.trip_name else trip_data.destination.strip()

    new_trip = Trip(
        user_id=current_user.user_id,
        trip_name=t_name,
        destination=trip_data.destination.strip(),
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        budget=float(trip_data.budget),
        travellers=int(trip_data.travellers),
        interests=interests_str,
        description=trip_data.description.strip() if trip_data.description else ""
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)

    budget_info = calculate_trip_budget(new_trip, [])

    trip_dict = {
        "trip_id": new_trip.trip_id,
        "user_id": new_trip.user_id,
        "trip_name": new_trip.trip_name or new_trip.destination,
        "destination": new_trip.destination,
        "start_date": new_trip.start_date,
        "end_date": new_trip.end_date,
        "budget": new_trip.budget,
        "travellers": new_trip.travellers,
        "interests": new_trip.interests,
        "description": new_trip.description,
        "total_spent": budget_info["total_spent"],
        "remaining_budget": budget_info["remaining_budget"],
        "budget_used_percentage": budget_info["budget_used_percentage"],
        "budget_exceeded": budget_info["budget_exceeded"],
        "created_at": new_trip.created_at
    }
    return TripOut(**trip_dict)

@router.get("", response_model=List[TripOut])
def get_user_trips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all trips belonging to the authenticated user."""
    trips = db.query(Trip).filter(Trip.user_id == current_user.user_id).order_by(Trip.start_date.desc()).all()
    results = []

    for trip in trips:
        budget_info = calculate_trip_budget(trip, trip.expenses)
        results.append(
            TripOut(
                trip_id=trip.trip_id,
                user_id=trip.user_id,
                trip_name=trip.trip_name or trip.destination,
                destination=trip.destination,
                start_date=trip.start_date,
                end_date=trip.end_date,
                budget=trip.budget,
                travellers=trip.travellers,
                interests=trip.interests or "",
                description=trip.description or "",
                total_spent=budget_info["total_spent"],
                remaining_budget=budget_info["remaining_budget"],
                budget_used_percentage=budget_info["budget_used_percentage"],
                budget_exceeded=budget_info["budget_exceeded"],
                created_at=trip.created_at
            )
        )
    return results

@router.get("/{trip_id}", response_model=TripDetailOut)
def get_trip_details(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves full trip details including itinerary, expenses, and saved experiences."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this trip")

    budget_info = calculate_trip_budget(trip, trip.expenses)

    return TripDetailOut(
        trip_id=trip.trip_id,
        user_id=trip.user_id,
        trip_name=trip.trip_name or trip.destination,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        travellers=trip.travellers,
        interests=trip.interests or "",
        description=trip.description or "",
        total_spent=budget_info["total_spent"],
        remaining_budget=budget_info["remaining_budget"],
        budget_used_percentage=budget_info["budget_used_percentage"],
        budget_exceeded=budget_info["budget_exceeded"],
        created_at=trip.created_at,
        itinerary_items=[ItineraryOut.model_validate(i) for i in trip.itinerary_items],
        expenses=[ExpenseOut.model_validate(e) for e in trip.expenses],
        saved_experiences=[SavedExperienceOut.model_validate(s) for s in trip.saved_experiences],
        category_breakdown=budget_info["category_breakdown"]
    )

@router.put("/{trip_id}", response_model=TripOut)
def update_trip(
    trip_id: int,
    trip_update: TripUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an existing trip for the authenticated user."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to edit this trip")

    if trip_update.trip_name is not None:
        trip.trip_name = trip_update.trip_name.strip()
    if trip_update.destination is not None:
        trip.destination = trip_update.destination.strip()
    if trip_update.start_date is not None:
        trip.start_date = trip_update.start_date
    if trip_update.end_date is not None:
        trip.end_date = trip_update.end_date
    if trip_update.budget is not None:
        trip.budget = float(trip_update.budget)
    if trip_update.travellers is not None:
        trip.travellers = int(trip_update.travellers)
    if trip_update.interests is not None:
        trip.interests = _format_interests(trip_update.interests)
    if trip_update.description is not None:
        trip.description = trip_update.description.strip()

    if trip.end_date < trip.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be on or after start_date")

    db.commit()
    db.refresh(trip)

    budget_info = calculate_trip_budget(trip, trip.expenses)

    return TripOut(
        trip_id=trip.trip_id,
        user_id=trip.user_id,
        trip_name=trip.trip_name or trip.destination,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=trip.budget,
        travellers=trip.travellers,
        interests=trip.interests or "",
        description=trip.description or "",
        total_spent=budget_info["total_spent"],
        remaining_budget=budget_info["remaining_budget"],
        budget_used_percentage=budget_info["budget_used_percentage"],
        budget_exceeded=budget_info["budget_exceeded"],
        created_at=trip.created_at
    )

@router.delete("/{trip_id}", status_code=status.HTTP_200_OK)
def delete_trip(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a trip and cascades to itinerary, expenses, and saved experiences."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to delete this trip")

    db.delete(trip)
    db.commit()
    return {"message": "Trip deleted successfully", "trip_id": trip_id}

@router.get("/{trip_id}/summary", response_model=TripSummaryOut)
def get_trip_summary(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns trip summary contract for consumption by external applications."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.user_id != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to access this trip summary")

    budget_info = calculate_trip_budget(trip, trip.expenses)

    # Gather selected activities from saved experiences + itinerary activities
    activities = []
    for exp in trip.saved_experiences:
        if exp.name not in activities:
            activities.append(exp.name)
    for it in trip.itinerary_items:
        if it.activity not in activities:
            activities.append(it.activity)

    return TripSummaryOut(
        destination=trip.destination,
        budget=trip.budget,
        total_spent=budget_info["total_spent"],
        remaining_budget=budget_info["remaining_budget"],
        budget_used_percentage=budget_info["budget_used_percentage"],
        budget_exceeded=budget_info["budget_exceeded"],
        interests=_parse_interests_list(trip.interests),
        selected_activities=activities
    )
