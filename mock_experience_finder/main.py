"""
=============================================================================
EXPERIENCE FINDER - INDEPENDENT REST API & PARTNER PORTAL SERVICE
Simulates the second developer's microservice application.
Communicates strictly via REST / JSON and File Transfer.
Default Port: 8001
=============================================================================
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Query, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

app = FastAPI(
    title="Experience Finder API & Partner Portal",
    description="Independent discovery service providing curated activities, experiences, and bi-directional file synchronization with Smart Travel Planner.",
    version="1.0.0"
)

# CORS enabled
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
RECEIVED_DIR = BASE_DIR / "received_files"
RECEIVED_DIR.mkdir(parents=True, exist_ok=True)

# URL of the primary Smart Travel Planner application
PLANNER_API_URL = os.getenv("PLANNER_API_URL", "http://localhost:8000").rstrip("/")
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "st_partner_secret_key_2026")


CATALOG = [
    {
        "id": 1,
        "destination": "Goa",
        "name": "Scuba Diving",
        "category": "Adventure",
        "price": 2500.0,
        "rating": 4.7,
        "description": "Explore the vibrant underwater marine life around Grande Island with certified PADI dive instructors."
    },
    {
        "id": 2,
        "destination": "Goa",
        "name": "Dolphin Watching",
        "category": "Adventure",
        "price": 1200.0,
        "rating": 4.5,
        "description": "Enjoy a scenic morning boat trip in the Arabian Sea watching wild dolphins leap in the bay."
    },
    {
        "id": 3,
        "destination": "Goa",
        "name": "Baga Beach",
        "category": "Beach",
        "price": 0.0,
        "rating": 4.6,
        "description": "Iconic beach famous for relaxing seaside shacks, water sports, and vibrant sunset views."
    },
    {
        "id": 4,
        "destination": "Goa",
        "name": "Dudhsagar Waterfalls Trek",
        "category": "Nature",
        "price": 1800.0,
        "rating": 4.8,
        "description": "Four-tiered majestic waterfall in the Western Ghats with guided jungle jeep trail."
    },
    {
        "id": 5,
        "destination": "Goa",
        "name": "Old Goa Heritage Walk",
        "category": "Culture",
        "price": 600.0,
        "rating": 4.4,
        "description": "Explore UNESCO World Heritage churches including Basilica of Bom Jesus and Se Cathedral."
    },
    {
        "id": 6,
        "destination": "Goa",
        "name": "Sunset Cruise at Mandovi",
        "category": "Leisure",
        "price": 950.0,
        "rating": 4.6,
        "description": "Relaxing twilight river cruise with Konkani folk music and cultural dance performances."
    },
    {
        "id": 7,
        "destination": "Manali",
        "name": "Solang Valley Paragliding",
        "category": "Adventure",
        "price": 3200.0,
        "rating": 4.8,
        "description": "Tandem paragliding flight over snowy Himalayan pine slopes."
    },
    {
        "id": 8,
        "destination": "Jaipur",
        "name": "Amber Fort Elephant & Light Show",
        "category": "Culture",
        "price": 750.0,
        "rating": 4.6,
        "description": "Historic Rajput fortress tour with evening musical sound-and-light history show."
    }
]

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
    if len(TRANSFER_LOGS) > 50:
        TRANSFER_LOGS.pop()

class ExperienceItem(BaseModel):
    id: int
    name: str
    category: str
    price: float
    rating: float
    description: str

class ExperienceResponse(BaseModel):
    experiences: List[ExperienceItem]

@app.get("/api/experiences", response_model=ExperienceResponse)
def get_experiences(
    destination: Optional[str] = Query(None, description="Destination city, e.g. Goa"),
    category: Optional[str] = Query(None, description="Category filter, e.g. Adventure, Beach, Culture")
):
    """Returns curated experiences matching the destination and optional category."""
    results = CATALOG
    if destination:
        dest_clean = destination.strip().lower()
        results = [e for e in results if e["destination"].lower() == dest_clean]
        if not results:
            results = CATALOG

    if category and category.strip().lower() != "all":
        cat_clean = category.strip().lower()
        results = [e for e in results if e["category"].lower() == cat_clean]

    cleaned_items = [
        ExperienceItem(
            id=e["id"],
            name=e["name"],
            category=e["category"],
            price=e["price"],
            rating=e["rating"],
            description=e["description"]
        )
        for e in results
    ]
    return {"experiences": cleaned_items}

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "Experience Finder REST API",
        "port": 8001,
        "timestamp": datetime.now().isoformat()
    }

# ===================================================================
# FILE SYNCHRONIZATION & TRANSFER ENDPOINTS
# ===================================================================

@app.get("/api/sync/status")
async def check_peer_status():
    """Checks whether the primary Smart Travel Planner (:8000) is reachable."""
    peer_url = f"{PLANNER_API_URL}/health"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(peer_url)
            if resp.status_code == 200:
                return {
                    "online": True,
                    "peer_url": PLANNER_API_URL,
                    "service": "Smart Travel Planner API",
                    "status_code": resp.status_code,
                    "message": "Connected successfully to Smart Travel Planner (:8000)"
                }
    except Exception as e:
        return {
            "online": False,
            "peer_url": PLANNER_API_URL,
            "service": "Smart Travel Planner API",
            "message": f"Smart Travel Planner offline or unreachable ({str(e)})"
        }

@app.post("/api/sync/receive-file")
async def receive_file_from_planner(
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    sender: Optional[str] = Form("Smart Travel Planner (:8000)")
):
    """
    Receives a text file sent over REST API from Smart Travel Planner (:8000).
    Saves the file to mock_experience_finder/received_files/ and allows download.
    """
    global _file_id_counter

    actual_filename = "received_trip_plan.txt"
    file_bytes = b""

    if file:
        actual_filename = file.filename or actual_filename
        file_bytes = await file.read()
    elif content is not None:
        actual_filename = filename or f"trip_dossier_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_bytes = content.encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="No file or content provided")

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
        "sender": sender or "Smart Travel Planner (:8000)",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "size_bytes": len(file_bytes),
        "preview": text_preview,
        "path": str(save_path)
    }
    RECEIVED_FILES.insert(0, file_record)
    file_id = _file_id_counter
    _file_id_counter += 1

    add_log(
        direction="INCOMING (Planner -> Experience Finder)",
        filename=actual_filename,
        status_text="SUCCESS",
        details=f"Received {len(file_bytes)} bytes from {sender}"
    )

    return {
        "status": "success",
        "message": "Text file received and saved successfully by Experience Finder",
        "file_id": file_id,
        "filename": actual_filename,
        "size_bytes": len(file_bytes),
        "timestamp": file_record["timestamp"]
    }

@app.get("/api/sync/received-files")
def get_received_files():
    """Returns list of files received from Smart Travel Planner."""
    return {"files": RECEIVED_FILES}

@app.get("/api/sync/download/{file_id}")
def download_received_file(file_id: int):
    """Downloads a text file received by Experience Finder."""
    file_record = next((f for f in RECEIVED_FILES if f["id"] == file_id), None)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_record["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file missing on server")

    return FileResponse(
        path=str(file_path),
        filename=file_record["filename"],
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_record["filename"]}"'}
    )

@app.get("/api/sync/preview/{file_id}")
def preview_received_file(file_id: int):
    """Returns the full text content of a received file for modal viewing."""
    file_record = next((f for f in RECEIVED_FILES if f["id"] == file_id), None)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = Path(file_record["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file missing on server")

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

@app.post("/api/sync/send-file")
async def send_file_to_planner(
    file: Optional[UploadFile] = File(None),
    filename: Optional[str] = Form(None),
    content: Optional[str] = Form(None)
):
    """
    Sends a text file over REST API to Smart Travel Planner (:8000/api/sync/receive-file).
    """
    target_url = f"{PLANNER_API_URL}/api/sync/receive-file"
    actual_filename = "experience_package.txt"
    file_content = ""

    if file:
        actual_filename = file.filename or actual_filename
        file_bytes = await file.read()
        file_content = file_bytes.decode("utf-8", errors="replace")
    elif content is not None:
        actual_filename = filename or f"voucher_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_content = content
    else:
        raise HTTPException(status_code=400, detail="No file or text content provided to send")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            files_payload = {
                "file": (actual_filename, file_content.encode("utf-8"), "text/plain")
            }
            data_payload = {
                "filename": actual_filename,
                "sender": "Experience Finder (:8001)"
            }
            response = await client.post(target_url, files=files_payload, data=data_payload)

            if response.status_code == 200:
                result = response.json()
                add_log(
                    direction="OUTGOING (Experience Finder -> Planner)",
                    filename=actual_filename,
                    status_text="SUCCESS",
                    details=f"Transferred to {target_url} [HTTP 200 OK]"
                )
                return {
                    "status": "success",
                    "message": f'Text file "{actual_filename}" successfully transferred to Smart Travel Planner!',
                    "peer_response": result
                }
            else:
                add_log(
                    direction="OUTGOING (Experience Finder -> Planner)",
                    filename=actual_filename,
                    status_text="FAILED",
                    details=f"Planner returned HTTP {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Smart Travel Planner returned error: {response.text}"
                )
    except httpx.RequestError as exc:
        add_log(
            direction="OUTGOING (Experience Finder -> Planner)",
            filename=actual_filename,
            status_text="FAILED",
            details=f"Connection failed: {str(exc)}"
        )
        raise HTTPException(
            status_code=503,
            detail=f"Smart Travel Planner is not running on {PLANNER_API_URL}. Start it on port 8000 to complete transfer."
        )

@app.post("/api/sync/generate-and-send-voucher")
async def generate_and_send_voucher():
    """Generates an official curated Experience Voucher Package text file and transfers it to Smart Travel Planner."""
    lines = [
        "=" * 70,
        "EXPERIENCE FINDER - OFFICIAL PARTNER CONFIRMATION & VOUCHER PACK",
        f"Issued Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "Issuer      : Experience Finder Microservice (Port 8001)",
        "Recipient   : Smart Travel Planner (Port 8000)",
        "=" * 70,
        "",
        "--- CONFIRMED EXPERIENCES & BOOKING VOUCHERS ---",
        "",
        "[BOOKING #EXP-GOA-7821] SCUBA DIVING ADVENTURE",
        "  * Location     : Grande Island, North Goa",
        "  * Provider     : Ocean Blue Dive Academy (PADI Certified)",
        "  * Agreed Rate  : INR 2,500.00 / person",
        "  * Voucher Code : VCHR-SCUBA-2026-X99",
        "  * Inclusions   : Equipment rental, safety boat, underwater 4K video",
        "  * Contact Desk : +91 98230 11223 (Capt. Fernandes)",
        "",
        "[BOOKING #EXP-GOA-7822] DOLPHIN WATCHING CRUISE",
        "  * Location     : Sinquerim Beach Bay Jetty",
        "  * Provider     : Arabian Sea Coastal Safaris",
        "  * Agreed Rate  : INR 1,200.00 / person",
        "  * Voucher Code : VCHR-DOLPHIN-GOA-44B",
        "  * Departure    : Morning slot (08:30 AM recommended for clear sightings)",
        "",
        "--- SPECIAL DISCOUNTS & PARTNER BENEFITS ---",
        "  * Free Goan Bebinca dessert tasting at Fisherman's Cove with any booking.",
        "  * 15% discount code on watersports combo at Baga Beach: EXPGOA15",
        "",
        "--- EMERGENCY & SUPPORT HOTLINE ---",
        "  * Experience Finder Helpdesk : 1800-419-7700",
        "  * Goa Tourism Police Helpline : 112 / +91 832 2420821",
        "",
        "=" * 70,
        "END OF VOUCHER FILE - TRANSFERRED VIA REST API TO SMART TRAVEL PLANNER",
        "=" * 70
    ]
    content = "\n".join(lines)
    filename = "Goa_Experience_Guide_and_Vouchers.txt"
    return await send_file_to_planner(filename=filename, content=content)

@app.get("/api/sync/logs")
def get_transfer_logs():
    return {"logs": TRANSFER_LOGS}

# ===================================================================
# REVERSE API INTEGRATION ENDPOINT (Experience Finder -> Planner)
# ===================================================================

@app.get("/api/integration/request-trip-summary/{trip_id}")
async def request_trip_summary_from_planner(
    trip_id: int,
    key: Optional[str] = Query(None, description="Optional override integration key for testing failure cases")
):
    """
    Reverse Integration Flow:
    Experience Finder requests an authorized trip summary from Smart Travel Planner (:8000).
    Calls GET /api/integration/trips/{trip_id}/summary with X-Integration-Key header.
    Logs the outgoing request and received response in Experience Finder's communication logs.
    """
    target_url = f"{PLANNER_API_URL}/api/integration/trips/{trip_id}/summary"
    used_key = key if key is not None else INTEGRATION_API_KEY
    headers = {"X-Integration-Key": used_key}

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(target_url, headers=headers)
            status_code = resp.status_code
            if status_code == 200:
                data = resp.json()
                add_log(
                    direction="OUTGOING (Experience Finder -> Planner /api/integration)",
                    filename=f"Trip_{trip_id}_Summary.json",
                    status_text="SUCCESS",
                    details=f"Retrieved authorized summary for '{data.get('destination')}' [HTTP 200 OK]. {len(data.get('selected_itinerary_activities', []))} activities received."
                )
                return {
                    "status": "success",
                    "http_code": 200,
                    "target_url": target_url,
                    "data": data,
                    "message": "Authorized trip summary retrieved successfully from Smart Travel Planner!"
                }
            else:
                err_detail = resp.text
                try:
                    err_json = resp.json()
                    err_detail = err_json.get("detail", resp.text)
                except Exception:
                    pass
                add_log(
                    direction="OUTGOING (Experience Finder -> Planner /api/integration)",
                    filename=f"Trip_{trip_id}_Summary.json",
                    status_text="FAILED",
                    details=f"Planner returned HTTP {status_code}: {err_detail}"
                )
                return JSONResponse(
                    status_code=status_code,
                    content={
                        "status": "error",
                        "http_code": status_code,
                        "target_url": target_url,
                        "detail": err_detail,
                        "message": f"Smart Travel Planner rejected request with HTTP {status_code}"
                    }
                )
    except httpx.RequestError as exc:
        add_log(
            direction="OUTGOING (Experience Finder -> Planner /api/integration)",
            filename=f"Trip_{trip_id}_Summary.json",
            status_text="FAILED",
            details=f"Connection failed to {target_url}: {str(exc)}"
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "http_code": 503,
                "target_url": target_url,
                "detail": f"Could not reach Smart Travel Planner at {PLANNER_API_URL}. Ensure it is running on port 8000.",
                "message": "Connection refused or timed out"
            }
        )


# ===================================================================
# INTERACTIVE WEB DASHBOARD (PORT 8001)
# ===================================================================

@app.get("/", response_class=HTMLResponse)
def experience_finder_web_portal():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Experience Finder — Partner Discovery &amp; File Exchange Portal (Port 8001)</title>
  <style>
    :root {
      --primary: #0f766e;
      --primary-hover: #115e59;
      --primary-light: #ccfbf1;
      --secondary: #0284c7;
      --bg: #f8fafc;
      --surface: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --border: #e2e8f0;
      --success: #16a34a;
      --danger: #dc2626;
      --radius: 10px;
      --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); line-height: 1.5; padding-bottom: 3rem; }
    header { background: #0f172a; color: white; padding: 1.25rem 2rem; display: flex; align-items: center; justify-content: space-between; border-bottom: 3px solid var(--primary); }
    .brand { display: flex; align-items: center; gap: 0.75rem; font-weight: 700; font-size: 1.25rem; }
    .brand-icon { width: 36px; height: 36px; background: var(--primary); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; }
    .status-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.85rem; border-radius: 9999px; font-size: 0.825rem; font-weight: 600; background: #1e293b; color: #94a3b8; }
    .status-badge.online { background: #064e3b; color: #6ee7b7; border: 1px solid #059669; }
    .status-badge.offline { background: #450a0a; color: #fca5a5; border: 1px solid #b91c1c; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
    
    .container { max-width: 1200px; margin: 2rem auto; padding: 0 1.5rem; }
    .viva-banner { background: linear-gradient(135deg, #0f766e 0%, #0284c7 100%); color: white; border-radius: var(--radius); padding: 1.5rem 2rem; margin-bottom: 2rem; box-shadow: var(--shadow); }
    .viva-banner h2 { font-size: 1.6rem; margin-bottom: 0.4rem; }
    .viva-banner p { font-size: 0.95rem; opacity: 0.95; }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.75rem; margin-bottom: 2rem; }
    @media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
    .card-head { padding: 1.15rem 1.5rem; border-bottom: 1px solid var(--border); background: #fdfdfd; display: flex; align-items: center; justify-content: space-between; }
    .card-head h3 { font-size: 1.15rem; color: var(--text); }
    .card-body { padding: 1.5rem; }

    .btn { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.15rem; border-radius: 6px; font-weight: 600; font-size: 0.9rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; transition: all 0.2s; }
    .btn-primary { background: var(--primary); color: white; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-secondary { background: var(--secondary); color: white; }
    .btn-secondary:hover { background: #0369a1; }
    .btn-outline { background: transparent; border-color: var(--border); color: var(--text); }
    .btn-outline:hover { background: #f1f5f9; }
    .btn-sm { padding: 0.35rem 0.75rem; font-size: 0.8rem; border-radius: 4px; }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }

    .form-group { margin-bottom: 1.25rem; display: flex; flex-direction: column; gap: 0.35rem; }
    .form-group label { font-size: 0.85rem; font-weight: 600; color: var(--text); }
    .form-control { width: 100%; padding: 0.65rem 0.85rem; border: 1px solid var(--border); border-radius: 6px; font-size: 0.9rem; outline: none; }
    .form-control:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.15); }
    textarea.form-control { resize: vertical; min-height: 90px; }

    .file-item { border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem; background: #fafafa; display: flex; flex-direction: column; gap: 0.5rem; }
    .file-item-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
    .file-name { font-weight: 700; color: var(--text); font-size: 0.95rem; }
    .file-meta { font-size: 0.785rem; color: var(--muted); }
    .file-preview { background: #0f172a; color: #f8fafc; font-family: monospace; font-size: 0.78rem; padding: 0.75rem; border-radius: 6px; white-space: pre-wrap; word-break: break-word; max-height: 110px; overflow-y: auto; }
    .file-actions { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem; }

    .empty-box { text-align: center; padding: 2.5rem 1rem; color: var(--muted); }
    .log-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .log-table th { text-align: left; background: #f1f5f9; padding: 0.65rem 1rem; font-weight: 700; color: var(--muted); border-bottom: 1px solid var(--border); }
    .log-table td { padding: 0.65rem 1rem; border-bottom: 1px solid var(--border); }
    .badge { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }
    .badge-success { background: #dcfce7; color: #15803d; }
    .badge-danger { background: #fee2e2; color: #b91c1c; }

    /* Modal */
    .modal-backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; padding: 1rem; z-index: 999; }
    .modal-backdrop.active { display: flex; }
    .modal-box { background: white; border-radius: var(--radius); width: 100%; max-width: 680px; max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2); }
    .modal-header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
    .modal-body { padding: 1.5rem; overflow-y: auto; }
    .modal-content-pre { background: #0f172a; color: #f8fafc; font-family: monospace; font-size: 0.85rem; padding: 1.25rem; border-radius: 6px; white-space: pre-wrap; line-height: 1.5; }
    .modal-close { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--muted); }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">🌟</div>
      <div>
        <span>Experience Finder</span>
        <span style="font-size: 0.75rem; display: block; opacity: 0.8; font-weight: normal;">Partner Microservice Application (Port 8001)</span>
      </div>
    </div>
    <div id="peer-status" class="status-badge">
      <span class="status-dot"></span>
      <span>Checking connection to Smart Travel Planner (:8000)...</span>
    </div>
  </header>

  <div class="container">
    <div class="viva-banner">
      <h2>College Faculty Viva Demonstration</h2>
      <p>
        Visible, active bidirectional file transfer and inter-process communication between <strong>Smart Travel Planner (:8000)</strong> and <strong>Experience Finder (:8001)</strong>. Send text files, inspect live transfers, and download files from both sides!
      </p>
    </div>

    <div class="grid-2">
      <!-- Left Pane: Received from Smart Travel Planner -->
      <div class="card">
        <div class="card-head">
          <h3>📥 Files Received from Smart Travel Planner</h3>
          <button class="btn btn-sm btn-outline" onclick="loadReceivedFiles()">↻ Refresh</button>
        </div>
        <div class="card-body">
          <p style="font-size: 0.85rem; color: var(--muted); margin-bottom: 1rem;">
            When a user in Smart Travel Planner (:8000) sends a trip dossier or text file, it reaches this inbox via <code>POST /api/sync/receive-file</code>.
          </p>
          <div id="received-files-container">
            <div class="empty-box">No files received yet. Click "Transfer Trip Plan" in Smart Travel Planner to send one!</div>
          </div>
        </div>
      </div>

      <!-- Right Pane: Send File to Smart Travel Planner -->
      <div class="card">
        <div class="card-head">
          <h3>📤 Send File to Smart Travel Planner (:8000)</h3>
          <span class="badge badge-success">REST Transfer</span>
        </div>
        <div class="card-body">
          <!-- Quick Action Button -->
          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 1.15rem; margin-bottom: 1.5rem;">
            <strong style="color: #166534; font-size: 0.95rem; display: block; margin-bottom: 0.35rem;">⚡ One-Click Demonstration Action:</strong>
            <p style="font-size: 0.85rem; color: #15803d; margin-bottom: 0.85rem;">
              Generates an official <strong>Goa Experience Guide &amp; Vouchers (.txt)</strong> package and transfers it to Smart Travel Planner (:8000).
            </p>
            <button class="btn btn-primary" id="btn-quick-voucher" onclick="sendQuickVoucher()">
              🚀 Generate &amp; Transfer Voucher Pack (.txt)
            </button>
          </div>

          <div style="text-align: center; margin: 1rem 0; color: var(--muted); font-size: 0.85rem; font-weight: 700;">
            — OR SEND CUSTOM TEXT FILE —
          </div>

          <form id="send-custom-form">
            <div class="form-group">
              <label>Filename</label>
              <input type="text" id="custom-filename" class="form-control" value="Experience_Partner_Update.txt" required>
            </div>
            <div class="form-group">
              <label>Text Content</label>
              <textarea id="custom-content" class="form-control" placeholder="Type instructions, confirmation vouchers, or notes for the traveler...">Hello Smart Travel Planner Team!
Here is the official confirmation from Experience Finder.
Your Goa tour vouchers have been approved and activated.
Enjoy the Scuba Diving and Dolphin cruise adventures!</textarea>
            </div>
            <div class="form-group">
              <label>Or Upload Any .txt File From Computer</label>
              <input type="file" id="custom-file" class="form-control" accept=".txt">
            </div>
            <button type="submit" class="btn btn-secondary" style="width: 100%;">
              📤 Transfer Text File to Smart Travel Planner &rarr;
            </button>
          </form>
          <div id="send-feedback" style="margin-top: 1rem; font-size: 0.85rem; font-weight: 600;"></div>
        </div>
      </div>
    <!-- Reverse Integration Flow Demonstration Card -->
    <div class="card" style="margin-bottom: 2rem; border-left: 4px solid var(--secondary);">
      <div class="card-head">
        <h3>🔄 Reverse Integration Flow: Request Authorized Trip Summary (:8000 &rarr; :8001)</h3>
        <span class="badge badge-success">Phase 7 Reverse API</span>
      </div>
      <div class="card-body">
        <p style="font-size: 0.85rem; color: var(--muted); margin-bottom: 1rem;">
          Experience Finder requests an authorized trip summary from Smart Travel Planner (:8000) using endpoint <code>GET /api/integration/trips/{trip_id}/summary</code> and server-to-server header <code>X-Integration-Key</code>.
          Returns strictly permitted fields (Trip ID, destination, dates, budget, itinerary activities). Passwords, tokens, and personal credentials are never exposed.
        </p>

        <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-bottom: 1.25rem;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <label style="font-size: 0.85rem; font-weight: 600;">Trip ID:</label>
            <select id="rev-trip-id" class="form-control" style="width: 260px;">
              <option value="101" selected>Trip #101 (Goa - Permitted Demo)</option>
              <option value="102">Trip #102 (Kerala - Permitted Demo)</option>
              <option value="999">Trip #999 (Unpermitted / Forbidden Test)</option>
            </select>
          </div>

          <button class="btn btn-primary" onclick="fetchReverseSummary(false)">
            ⚡ Request Trip Summary (Valid Key)
          </button>
          <button class="btn btn-outline" style="border-color: var(--danger); color: var(--danger);" onclick="fetchReverseSummary(true)">
            ⚠ Test Invalid Key (401 Error)
          </button>
        </div>

        <div id="rev-summary-result" style="display: none; background: #0f172a; color: #f8fafc; border-radius: 8px; padding: 1.25rem; font-family: monospace; font-size: 0.85rem; max-height: 250px; overflow-y: auto; white-space: pre-wrap;"></div>
      </div>
    </div>

    <!-- Live Logs -->
    <div class="card">

      <div class="card-head">
        <h3>📊 Live REST Transfer Activity Log</h3>
        <button class="btn btn-sm btn-outline" onclick="loadLogs()">↻ Refresh Logs</button>
      </div>
      <div class="card-body" style="padding: 0; max-height: 250px; overflow-y: auto;">
        <table class="log-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Direction</th>
              <th>Filename</th>
              <th>Status</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody id="logs-tbody">
            <tr><td colspan="5" style="text-align: center; color: var(--muted); padding: 1.5rem;">No transfer events logged yet.</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Content Preview Modal -->
  <div class="modal-backdrop" id="preview-modal">
    <div class="modal-box">
      <div class="modal-header">
        <h3 id="modal-filename">File Content</h3>
        <button class="modal-close" onclick="closePreviewModal()">&times;</button>
      </div>
      <div class="modal-body">
        <pre class="modal-content-pre" id="modal-pre"></pre>
      </div>
    </div>
  </div>

  <script>
    async function checkStatus() {
      try {
        const res = await fetch("/api/sync/status");
        const data = await res.json();
        const badge = document.getElementById("peer-status");
        if (data.online) {
          badge.className = "status-badge online";
          badge.innerHTML = `<span class="status-dot"></span> Connected to Smart Travel Planner (:8000)`;
        } else {
          badge.className = "status-badge offline";
          badge.innerHTML = `<span class="status-dot"></span> Smart Travel Planner (:8000) Offline`;
        }
      } catch (e) {
        document.getElementById("peer-status").className = "status-badge offline";
      }
    }

    async function loadReceivedFiles() {
      try {
        const res = await fetch("/api/sync/received-files");
        const data = await res.json();
        const container = document.getElementById("received-files-container");
        if (!data.files || data.files.length === 0) {
          container.innerHTML = `<div class="empty-box">No files received yet. Send a file from Smart Travel Planner (:8000) to see it appear here!</div>`;
          return;
        }

        container.innerHTML = data.files.map(f => `
          <div class="file-item">
            <div class="file-item-header">
              <span class="file-name">📄 ${escapeHtml(f.filename)}</span>
              <span class="badge badge-success">${f.size_bytes} bytes</span>
            </div>
            <div class="file-meta">
              From: <strong>${escapeHtml(f.sender)}</strong> • Received: ${f.timestamp}
            </div>
            <div class="file-preview">${escapeHtml(f.preview || '(empty)')}</div>
            <div class="file-actions">
              <a href="/api/sync/download/${f.id}" class="btn btn-sm btn-primary" download>
                ⬇ Download Text File
              </a>
              <button class="btn btn-sm btn-outline" onclick="viewFileModal(${f.id})">
                👁 View Full Content
              </button>
            </div>
          </div>
        `).join("");
      } catch (e) {
        console.error("Error loading files", e);
      }
    }

    async function loadLogs() {
      try {
        const res = await fetch("/api/sync/logs");
        const data = await res.json();
        const tbody = document.getElementById("logs-tbody");
        if (!data.logs || data.logs.length === 0) {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--muted); padding: 1.5rem;">No transfer events logged yet.</td></tr>`;
          return;
        }

        tbody.innerHTML = data.logs.map(l => `
          <tr>
            <td>${l.timestamp}</td>
            <td><strong>${escapeHtml(l.direction)}</strong></td>
            <td>${escapeHtml(l.filename)}</td>
            <td><span class="badge ${l.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}">${l.status}</span></td>
            <td>${escapeHtml(l.details)}</td>
          </tr>
        `).join("");
      } catch (e) {
        console.error("Error loading logs", e);
      }
    }

    async function sendQuickVoucher() {
      const btn = document.getElementById("btn-quick-voucher");
      btn.disabled = true;
      btn.innerHTML = `Transferring to :8000...`;
      const feedback = document.getElementById("send-feedback");
      feedback.textContent = "";

      try {
        const res = await fetch("/api/sync/generate-and-send-voucher", { method: "POST" });
        const data = await res.json();
        if (res.ok) {
          feedback.style.color = "var(--success)";
          feedback.innerHTML = `✓ Transferred "Goa_Experience_Guide_and_Vouchers.txt" to Smart Travel Planner (:8000)!`;
        } else {
          feedback.style.color = "var(--danger)";
          feedback.textContent = data.detail || "Transfer failed";
        }
      } catch (err) {
        feedback.style.color = "var(--danger)";
        feedback.textContent = "Error: " + err.message;
      } finally {
        btn.disabled = false;
        btn.innerHTML = `🚀 Generate &amp; Transfer Voucher Pack (.txt)`;
        loadLogs();
      }
    }

    document.getElementById("send-custom-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const feedback = document.getElementById("send-feedback");
      feedback.textContent = "Transferring to Smart Travel Planner (:8000)...";
      feedback.style.color = "var(--text)";

      const fileInput = document.getElementById("custom-file");
      const filename = document.getElementById("custom-filename").value.trim();
      const content = document.getElementById("custom-content").value;

      const formData = new FormData();
      if (fileInput.files.length > 0) {
        formData.append("file", fileInput.files[0]);
      } else {
        formData.append("filename", filename);
        formData.append("content", content);
      }

      try {
        const res = await fetch("/api/sync/send-file", {
          method: "POST",
          body: formData
        });
        const data = await res.json();
        if (res.ok) {
          feedback.style.color = "var(--success)";
          feedback.innerHTML = `✓ ${data.message}`;
          document.getElementById("custom-file").value = "";
        } else {
          feedback.style.color = "var(--danger)";
          feedback.textContent = data.detail || "Transfer failed";
        }
      } catch (err) {
        feedback.style.color = "var(--danger)";
        feedback.textContent = "Error: " + err.message;
      } finally {
        loadLogs();
      }
    });

    async function viewFileModal(fileId) {
      try {
        const res = await fetch(`/api/sync/preview/${fileId}`);
        const data = await res.json();
        document.getElementById("modal-filename").textContent = `📄 ${data.filename} (${data.size_bytes} bytes)`;
        document.getElementById("modal-pre").textContent = data.content;
        document.getElementById("preview-modal").classList.add("active");
      } catch (err) {
        alert("Could not load file preview");
      }
    }

    function closePreviewModal() {
      document.getElementById("preview-modal").classList.remove("active");
    }

    async function fetchReverseSummary(useInvalidKey) {
      const tripId = document.getElementById("rev-trip-id").value;
      const resultBox = document.getElementById("rev-summary-result");
      resultBox.style.display = "block";
      resultBox.textContent = `Connecting to Smart Travel Planner (:8000/api/integration/trips/${tripId}/summary)...`;

      const keyParam = useInvalidKey ? "?key=invalid_bad_secret_key" : "";
      try {
        const res = await fetch(`/api/integration/request-trip-summary/${tripId}${keyParam}`);
        const data = await res.json();
        resultBox.textContent = JSON.stringify(data, null, 2);
        loadLogs();
      } catch (err) {
        resultBox.textContent = "Error: " + err.message;
      }
    }

    function escapeHtml(str) {
      return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }


    // Initialize and poll status
    checkStatus();
    loadReceivedFiles();
    loadLogs();
    setInterval(() => {
      checkStatus();
      loadReceivedFiles();
      loadLogs();
    }, 4000);
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_experience_finder.main:app", host="0.0.0.0", port=8001, reload=True)
