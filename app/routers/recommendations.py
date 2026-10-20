from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trip, SavedExperience, User
from app.schemas import SavedExperienceCreate, SavedExperienceOut, ExperienceListResponse
from app.auth import get_current_user
from app.services.experience_service import (
    fetch_experiences_from_finder,
    get_local_dev_mock_experiences,
    get_api_history,
    generate_api_history_txt,
    clear_api_history
)

router = APIRouter(tags=["Recommendations & Experiences"])

@router.get("/api/trips/{trip_id}/recommendations", response_model=ExperienceListResponse)
async def get_trip_recommendations(
    trip_id: int,
    category: Optional[str] = Query(None, description="Optional category filter, e.g. Adventure, Beach, Nature, Culture"),
    search: Optional[str] = Query(None, description="Optional search keyword for places, e.g. scuba, temple, fort"),
    destination: Optional[str] = Query(None, description="Optional destination override to explore"),
    use_dev_adapter: bool = Query(False, description="Explicitly use clearly labelled local development adapter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Integration endpoint:
    Communicates with the independent external Experience Finder REST API via HTTPX.
    Uses the trip destination (e.g. Goa, Chennai) or custom destination and user interest/category/search filters.
    If use_dev_adapter=True, uses the clearly labelled local development mock adapter.
    """
    trip = db.query(Trip).filter(Trip.trip_id == trip_id, Trip.user_id == current_user.user_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    target_destination = destination.strip() if (destination and destination.strip()) else trip.destination

    if use_dev_adapter:
        result = get_local_dev_mock_experiences(
            destination=target_destination,
            category=category,
            search=search
        )
    else:
        result = await fetch_experiences_from_finder(
            destination=target_destination,
            category=category,
            search=search,
            travellers=trip.travellers,
            budget=trip.budget,
            trip_id=trip.trip_id,
            client="Smart Travel Planner (:8000)"
        )

    return result

@router.get("/api/experiences/recommendations", response_model=ExperienceListResponse)
async def get_destination_recommendations(
    destination: Optional[str] = Query(None, description="Destination city, e.g. Chennai, Goa, Munnar, or None for all"),
    category: Optional[str] = Query(None, description="Optional category filter, e.g. Culture, Adventure"),
    search: Optional[str] = Query(None, description="Optional keyword search, e.g. Scuba, Temple, Beach"),
    use_dev_adapter: bool = Query(False, description="Explicitly use clearly labelled local development adapter")
):
    """
    Direct destination recommendation query endpoint:
    Allows querying recommendations directly by destination, category, and keyword search.
    """
    target_destination = destination.strip() if (destination and destination.strip()) else "All"
    if use_dev_adapter:
        return get_local_dev_mock_experiences(destination=target_destination, category=category, search=search)
    return await fetch_experiences_from_finder(
        destination=target_destination, 
        category=category, 
        search=search,
        client="Smart Travel Planner (:8000)"
    )

@router.get("/api/recommendations/history")
def get_recommendation_history():
    """Returns the logged history of all recommendation requests and responses or failures."""
    return {"history": get_api_history()}

@router.get("/api/recommendations/history/download")
def download_recommendation_history():
    """Downloads the full API communication history as a formatted TXT record."""
    txt_content = generate_api_history_txt()
    return Response(
        content=txt_content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="API_Communication_History.txt"'
        }
    )

@router.post("/api/recommendations/history/clear")
def clear_recommendation_history():
    """Clears the recorded API communication history."""
    clear_api_history()
    return {"status": "success", "message": "API communication history cleared"}

@router.post("/api/trips/{trip_id}/experiences", response_model=SavedExperienceOut, status_code=status.HTTP_201_CREATED)
def save_experience_to_trip(
    trip_id: int,
    exp_data: SavedExperienceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves an experience discovered from Experience Finder into the Smart Travel Planner database.
    """
    trip = db.query(Trip).filter(Trip.trip_id == trip_id, Trip.user_id == current_user.user_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    # Check if already saved
    existing = db.query(SavedExperience).filter(
        SavedExperience.trip_id == trip_id,
        SavedExperience.experience_id == exp_data.experience_id
    ).first()

    if existing:
        return SavedExperienceOut.model_validate(existing)

    saved_exp = SavedExperience(
        trip_id=trip.trip_id,
        experience_id=exp_data.experience_id,
        name=exp_data.name.strip(),
        category=exp_data.category.strip(),
        price=float(exp_data.price),
        rating=float(exp_data.rating) if exp_data.rating is not None else None
    )
    db.add(saved_exp)
    db.commit()
    db.refresh(saved_exp)
    return SavedExperienceOut.model_validate(saved_exp)

@router.get("/api/trips/{trip_id}/experiences", response_model=List[SavedExperienceOut])
def get_saved_experiences(
    trip_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all experiences saved to this trip."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id, Trip.user_id == current_user.user_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    saved = db.query(SavedExperience).filter(SavedExperience.trip_id == trip_id).order_by(SavedExperience.saved_at.desc()).all()
    return [SavedExperienceOut.model_validate(s) for s in saved]

@router.delete("/api/experiences/{saved_id}", status_code=status.HTTP_200_OK)
def remove_saved_experience(
    saved_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes a saved experience from a trip."""
    saved_exp = db.query(SavedExperience).join(Trip).filter(
        SavedExperience.saved_id == saved_id,
        Trip.user_id == current_user.user_id
    ).first()

    if not saved_exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved experience not found")

    db.delete(saved_exp)
    db.commit()
    return {"message": "Saved experience removed", "saved_id": saved_id}
