import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models import Trip, User, Itinerary, Expense, SavedExperience
from app.config import EXPERIENCE_API_URL
from app.services.budget_service import calculate_trip_budget

router = APIRouter(prefix="/api/sync", tags=["Data Exchange & File Sync"])

BASE_DIR = Path(__file__).resolve().parent.parent
RECEIVED_DIR = BASE_DIR / "received_files"
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

# In-memory stores for received files and logs
RECEIVED_FILES: List[Dict[str, Any]] = []
TRANSFER_LOGS: List[Dict[str, Any]] = []
_file_id_counter = 1
_log_id_counter = 1

def add_log(direction: str, filename: str, status_text: str, details: str):
    global _log_id_counter
    log_entry = {
        "id": _log_id_counter,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "direction": direction,
        "filename": filename,
        "status": status_text,
        "details": details
    }
    TRANSFER_LOGS.insert(0, log_entry)
    _log_id_counter += 1
    # Keep last 50 logs
    if len(TRANSFER_LOGS) > 50:
        TRANSFER_LOGS.pop()

@router.get("/status")
async def check_peer_status():
    """Checks whether the external Experience Finder service (:8001) is reachable."""
    peer_url = f"{EXPERIENCE_API_URL}/health"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(peer_url)
            if resp.status_code == 200:
                return {
                    "online": True,
                    "peer_url": EXPERIENCE_API_URL,
                    "service": "Experience Finder REST API",
                    "status_code": resp.status_code,
                    "message": "Connected successfully to Experience Finder (:8001)"
                }
    except Exception as e:
        return {
            "online": False,
            "peer_url": EXPERIENCE_API_URL,
            "service": "Experience Finder REST API",
            "message": f"Peer service offline or unreachable ({str(e)})"
        }

@router.get("/export-trip-text/{trip_id}")
def export_trip_text(trip_id: int, db: Session = Depends(get_db)):
    """Generates a structured, human-readable text file of a trip."""
    trip = db.query(Trip).filter(Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    budget_info = calculate_trip_budget(trip, trip.expenses)
    itinerary_items = db.query(Itinerary).filter(Itinerary.trip_id == trip_id).order_by(Itinerary.date.asc(), Itinerary.time.asc()).all()
    saved_exps = db.query(SavedExperience).filter(SavedExperience.trip_id == trip_id).all()

    lines = [
        "=" * 70,
        f"SMART TRAVEL PLANNER - TRIP DOSSIER & ITINERARY FILE",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source: Smart Travel Planner Application (Port 8000)",
        "=" * 70,
        "",
        "--- 1. BASIC TRIP DETAILS ---",
        f"Destination   : {trip.destination}",
        f"Trip ID       : {trip.trip_id}",
        f"Dates         : {trip.start_date} to {trip.end_date}",
        f"Travelers     : {trip.travellers} person(s)",
        f"Interests     : {trip.interests or 'None specified'}",
        f"Description   : {trip.description or 'None'}",
        "",
        "--- 2. BUDGET & FINANCIAL METRICS ---",
        f"Allocated Budget       : INR {trip.budget:,.2f}",
        f"Total Spent So Far     : INR {budget_info['total_spent']:,.2f}",
        f"Remaining Balance      : INR {budget_info['remaining_budget']:,.2f}",
        f"Budget Utilization     : {budget_info['budget_used_percentage']}%",
        f"Budget Exceeded Status : {'YES (Warning!)' if budget_info['budget_exceeded'] else 'NO (Safe)'}",
        "",
        "Category Breakdown:",
    ]
    for cat, amt in budget_info["category_breakdown"].items():
        lines.append(f"  * {cat:<12}: INR {amt:,.2f}")

    lines.extend([
        "",
        "--- 3. SCHEDULED ACTIVITIES / ITINERARY ---",
    ])
    if itinerary_items:
        for idx, item in enumerate(itinerary_items, 1):
            lines.append(f"[{idx}] Date: {item.date} | Time: {item.time} | Activity: {item.activity}")
            lines.append(f"    Location: {item.location or 'General'} | Estimated Cost: INR {item.estimated_cost:,.2f}")
            if item.notes:
                lines.append(f"    Notes: {item.notes}")
    else:
        lines.append("  (No activities scheduled yet)")

    lines.extend([
        "",
        "--- 4. SAVED DISCOVERY EXPERIENCES ---",
    ])
    if saved_exps:
        for idx, exp in enumerate(saved_exps, 1):
            lines.append(f"[{idx}] {exp.name} ({exp.category}) - INR {exp.price:,.2f} | Rating: {exp.rating}/5.0")
    else:
        lines.append("  (No experiences saved yet)")

    lines.extend([
        "",
        "=" * 70,
        "END OF FILE - READY FOR REST API TRANSFER TO EXPERIENCE FINDER",
        "=" * 70
    ])

    content = "\n".join(lines)
    filename = f"{trip.destination.replace(' ', '_')}_Trip_Plan_{trip.trip_id}.txt"
    return {
        "trip_id": trip.trip_id,
        "filename": filename,
        "content": content,
        "size_bytes": len(content.encode("utf-8"))
    }

@router.post("/receive-file")
async def receive_file_from_experience_finder(
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    sender: Optional[str] = Form("Experience Finder (:8001)")
):
    """
    Receives a text file sent over REST API from Experience Finder (:8001).
    Saves the file to app/received_files/ and indexes it for download.
    """
    global _file_id_counter

    actual_filename = "received_document.txt"
    file_bytes = b""

    if file:
        actual_filename = file.filename or actual_filename
        file_bytes = await file.read()
    elif content is not None:
        actual_filename = filename or f"partner_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_bytes = content.encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="No file or content provided")

    # Save to disk
    save_path = RECEIVED_DIR / actual_filename
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    text_preview = ""
    try:
        text_preview = file_bytes.decode("utf-8")[:300]
    except Exception:
        text_preview = "(Binary or non-UTF-8 content)"

    file_record = {
        "id": _file_id_counter,
        "filename": actual_filename,
        "sender": sender or "Experience Finder (:8001)",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "size_bytes": len(file_bytes),
        "preview": text_preview,
        "path": str(save_path)
    }
    RECEIVED_FILES.insert(0, file_record)
    file_id = _file_id_counter
    _file_id_counter += 1

    add_log(
        direction="INCOMING (Experience Finder -> Planner)",
        filename=actual_filename,
        status_text="SUCCESS",
        details=f"Received {len(file_bytes)} bytes from {sender}"
    )

    return {
        "status": "success",
        "message": "Text file received and stored successfully by Smart Travel Planner",
        "file_id": file_id,
        "filename": actual_filename,
        "size_bytes": len(file_bytes),
        "timestamp": file_record["timestamp"]
    }

@router.get("/received-files")
def get_received_files():
    """Lists all files received from Experience Finder."""
    return {"files": RECEIVED_FILES}

@router.get("/download/{file_id}")
def download_received_file(file_id: int):
    """Downloads a received text file as an attachment."""
    file_record = next((f for f in RECEIVED_FILES if f["id"] == file_id), None)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_record["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file missing from storage")

    return FileResponse(
        path=str(file_path),
        filename=file_record["filename"],
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_record["filename"]}"'}
    )

@router.get("/preview/{file_id}")
def preview_received_file(file_id: int):
    """Returns the full text content of a received file for UI modal display."""
    file_record = next((f for f in RECEIVED_FILES if f["id"] == file_id), None)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_record["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file missing from storage")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_content = f.read()

    return {
        "id": file_record["id"],
        "filename": file_record["filename"],
        "sender": file_record["sender"],
        "timestamp": file_record["timestamp"],
        "size_bytes": file_record["size_bytes"],
        "content": full_content
    }

@router.post("/send-file")
async def send_file_to_experience_finder(
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None),
    content: Optional[str] = Form(None)
):
    """
    Sends a text file over REST API to Experience Finder (:8001/api/sync/receive-file).
    Demonstrates active inter-process communication between both projects.
    """
    target_url = f"{EXPERIENCE_API_URL}/api/sync/receive-file"
    actual_filename = "travel_plan.txt"
    file_content = ""

    if file:
        actual_filename = file.filename or actual_filename
        file_bytes = await file.read()
        file_content = file_bytes.decode("utf-8", errors="replace")
    elif content is not None:
        actual_filename = filename or f"trip_dossier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_content = content
    else:
        raise HTTPException(status_code=400, detail="No file or text content provided to send")

    # Send file to Experience Finder via HTTPX multipart or form
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            files_payload = {
                "file": (actual_filename, file_content.encode("utf-8"), "text/plain")
            }
            data_payload = {
                "filename": actual_filename,
                "sender": "Smart Travel Planner (:8000)"
            }
            response = await client.post(target_url, files=files_payload, data=data_payload)

            if response.status_code == 200:
                result = response.json()
                add_log(
                    direction="OUTGOING (Planner -> Experience Finder)",
                    filename=actual_filename,
                    status_text="SUCCESS",
                    details=f"Transferred to {target_url} [HTTP 200 OK]"
                )
                return {
                    "status": "success",
                    "message": f'Text file "{actual_filename}" successfully transferred to Experience Finder!',
                    "peer_response": result
                }
            else:
                add_log(
                    direction="OUTGOING (Planner -> Experience Finder)",
                    filename=actual_filename,
                    status_text="FAILED",
                    details=f"Peer returned HTTP {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Experience Finder returned error: {response.text}"
                )
    except httpx.RequestError as exc:
        add_log(
            direction="OUTGOING (Planner -> Experience Finder)",
            filename=actual_filename,
            status_text="FAILED",
            details=f"Connection failed: {str(exc)}"
        )
        raise HTTPException(
            status_code=503,
            detail=f"Experience Finder is not running on {EXPERIENCE_API_URL}. Start it on port 8001 to complete transfer."
        )

@router.post("/transfer-trip/{trip_id}")
async def transfer_trip_direct(trip_id: int, db: Session = Depends(get_db)):
    """One-click action: exports trip plan as text and sends it to Experience Finder."""
    export_result = export_trip_text(trip_id, db)
    return await send_file_to_experience_finder(
        filename=export_result["filename"],
        content=export_result["content"]
    )

@router.get("/logs")
def get_transfer_logs():
    """Returns live transfer activity logs for faculty inspection."""
    return {"logs": TRANSFER_LOGS}
