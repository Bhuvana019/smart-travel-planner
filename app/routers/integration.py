from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Trip, Itinerary
from app.schemas import TripIntegrationSummaryOut, ItinerarySummaryItem
from app.config import INTEGRATION_API_KEY, DEMO_PERMITTED_TRIP_IDS
from app.services.experience_service import add_api_history_record

router = APIRouter(prefix="/api/integration", tags=["Partner Integration & Reverse API"])

@router.get("/trips/{trip_id}/summary", response_model=TripIntegrationSummaryOut)
def get_authorized_trip_summary(
    trip_id: int,
    request: Request,
    x_integration_key: Optional[str] = Header(None, alias="X-Integration-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
):
    """
    Dedicated Reverse API Integration Endpoint:
    Allows partner service 'Experience Finder' (:8001) to request an authorized trip summary.
    
    Security & Privacy Controls:
    1. Server-to-Server Authentication: Validates secret integration key.
    2. Scope & Trip Restriction: Limits access to permitted demo trips (DEMO_PERMITTED_TRIP_IDS).
    3. Privacy Guarantee: Returns ONLY permitted fields (Trip ID, destination, dates, budget, itinerary).
       Never exposes passwords, password hashes, JWT tokens, or personal user information.
    4. Full Audit Logging: Logs every inbound request (including 401, 403, 404, 200) to API history.
    """
    endpoint_path = f"/api/integration/trips/{trip_id}/summary"
    client_ip = request.client.host if request.client else "unknown"

    # 1. Resolve supplied integration credential
    provided_key = None
    if x_integration_key:
        provided_key = x_integration_key.strip()
    elif x_api_key:
        provided_key = x_api_key.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()
    elif authorization:
        provided_key = authorization.strip()

    # 2. Authenticate Server-to-Server credential
    if not provided_key or provided_key != INTEGRATION_API_KEY:
        err_msg = f"Inbound request from {client_ip} rejected: Invalid or missing server-to-server integration credential"
        add_api_history_record(
            destination=f"Trip #{trip_id}",
            category="Partner Integration",
            target_url=endpoint_path,
            status="UNAUTHORIZED",
            status_code="HTTP 401 Unauthorized",
            source=f"Experience Finder Peer ({client_ip})",
            details=err_msg,
            experiences_count=0,
            is_external=False,
            direction="INBOUND (Experience Finder -> Planner)",
            method="GET",
            endpoint=endpoint_path
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing server-to-server integration credential"
        )

    # 3. Check Trip Authorization Permission (Restricted to explicitly permitted demo trips)
    if trip_id not in DEMO_PERMITTED_TRIP_IDS:
        err_msg = f"Trip ID {trip_id} is not authorized for partner access. Only permitted demo trips {DEMO_PERMITTED_TRIP_IDS} are accessible."
        add_api_history_record(
            destination=f"Trip #{trip_id}",
            category="Partner Integration",
            target_url=endpoint_path,
            status="FORBIDDEN",
            status_code="HTTP 403 Forbidden",
            source=f"Experience Finder Peer ({client_ip})",
            details=err_msg,
            experiences_count=0,
            is_external=False,
            direction="INBOUND (Experience Finder -> Planner)",
            method="GET",
            endpoint=endpoint_path
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Access to Trip ID {trip_id} is not permitted for partner integration"
        )

    # 4. Check Trip Existence
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        err_msg = f"Trip ID {trip_id} not found in database"
        add_api_history_record(
            destination=f"Trip #{trip_id}",
            category="Partner Integration",
            target_url=endpoint_path,
            status="NOT_FOUND",
            status_code="HTTP 404 Not Found",
            source=f"Experience Finder Peer ({client_ip})",
            details=err_msg,
            experiences_count=0,
            is_external=False,
            direction="INBOUND (Experience Finder -> Planner)",
            method="GET",
            endpoint=endpoint_path
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )

    # 5. Extract ONLY permitted fields
    itinerary_items = db.query(Itinerary).filter(Itinerary.trip_id == trip.trip_id).order_by(Itinerary.date.asc(), Itinerary.time.asc()).all()

    selected_activities = [
        ItinerarySummaryItem(
            item_id=it.item_id,
            activity=it.activity,
            date=it.date,
            time=it.time,
            location=it.location or "",
            category=it.category or "General",
            estimated_cost=float(it.estimated_cost),
            notes=it.notes or ""
        )
        for it in itinerary_items
    ]

    response_payload = TripIntegrationSummaryOut(
        trip_id=trip.trip_id,
        destination=trip.destination,
        start_date=trip.start_date,
        end_date=trip.end_date,
        budget=float(trip.budget),
        selected_itinerary_activities=selected_activities
    )

    # 6. Audit Log Successful Inbound Request
    add_api_history_record(
        destination=trip.destination,
        category="Partner Integration",
        target_url=endpoint_path,
        status="SUCCESS",
        status_code="HTTP 200 OK",
        source=f"Experience Finder Peer ({client_ip})",
        details=f"Authorized trip summary returned for '{trip.destination}' with {len(selected_activities)} itinerary items. No sensitive data exposed.",
        experiences_count=len(selected_activities),
        is_external=True,
        direction="INBOUND (Experience Finder -> Planner)",
        method="GET",
        endpoint=endpoint_path
    )

    return response_payload
