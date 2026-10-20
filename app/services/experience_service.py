import logging
import json
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx

from app.config import EXPERIENCE_FINDER_API_URL

logger = logging.getLogger(__name__)

# =============================================================================
# LOCAL DEVELOPMENT MOCK ADAPTER CATALOG (STRICTLY FOR LOCAL TESTING ONLY)
# =============================================================================
DEV_MOCK_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "Goa": [
        {
            "id": 1,
            "name": "Scuba Diving at Grande Island",
            "category": "Adventure",
            "price": 2500.0,
            "rating": 4.7,
            "description": "Explore the underwater marine life of Grande Island with certified PADI dive instructors."
        },
        {
            "id": 2,
            "name": "Dolphin Watching Boat Safari",
            "category": "Adventure",
            "price": 1200.0,
            "rating": 4.5,
            "description": "Scenic morning boat excursion in the Arabian Sea watching dolphins leap in their natural habitat."
        },
        {
            "id": 3,
            "name": "Baga Beach Seaside Walk & Sports",
            "category": "Beach",
            "price": 0.0,
            "rating": 4.6,
            "description": "Iconic Goan coastline famous for relaxing shacks, parasailing, and sunset views."
        },
        {
            "id": 4,
            "name": "Dudhsagar Waterfalls Trek",
            "category": "Nature",
            "price": 1800.0,
            "rating": 4.8,
            "description": "Four-tiered majestic waterfall in the Western Ghats with guided jungle jeep trail."
        },
        {
            "id": 5,
            "name": "Old Goa UNESCO Heritage Walk",
            "category": "Culture",
            "price": 600.0,
            "rating": 4.4,
            "description": "Explore historic churches including Basilica of Bom Jesus and Se Cathedral."
        },
        {
            "id": 6,
            "name": "Mandovi River Twilight Cruise",
            "category": "Leisure",
            "price": 950.0,
            "rating": None,  # Rating omitted to verify graceful handling when API does not supply rating
            "description": "Relaxing twilight river cruise with Konkani folk music and cultural dance performances."
        }
    ],
    "Chennai": [
        {
            "id": 101,
            "name": "Marina Beach Promenade Walk",
            "category": "Beach",
            "price": 0.0,
            "rating": 4.5,
            "description": "Early morning coastal stroll along India's longest natural urban beach."
        },
        {
            "id": 102,
            "name": "Mylapore Kapaleeshwarar Temple Tour",
            "category": "Culture",
            "price": 300.0,
            "rating": 4.8,
            "description": "Vibrant 7th-century Dravidian temple complex celebrating traditional Carnatic culture."
        },
        {
            "id": 103,
            "name": "Mahabalipuram Shore Temples Excursion",
            "category": "Culture",
            "price": 1500.0,
            "rating": 4.9,
            "description": "UNESCO World Heritage monolithic rock carvings and ancient structural stone temples."
        },
        {
            "id": 104,
            "name": "Guindy National Park Nature Trail",
            "category": "Nature",
            "price": 100.0,
            "rating": None,
            "description": "Unique urban protected forest harboring spotted deer, blackbucks, and migratory birds."
        }
    ],
    "Munnar": [
        {
            "id": 201,
            "name": "Kolukkumalai Sunrise Jeep Safari",
            "category": "Adventure",
            "price": 2500.0,
            "rating": 4.9,
            "description": "Thrilling 4x4 off-road journey to the world's highest organic tea estate at 7,900 ft."
        },
        {
            "id": 202,
            "name": "Tata Tea Museum & Heritage Trail",
            "category": "Culture",
            "price": 200.0,
            "rating": 4.3,
            "description": "Historical exhibition of tea manufacturing artifacts and orthodox tea tasting sessions."
        },
        {
            "id": 203,
            "name": "Eravikulam National Park Safari",
            "category": "Nature",
            "price": 500.0,
            "rating": 4.7,
            "description": "Scenic rolling hills sanctuary preserving the endangered Nilgiri Tahr mountain goat."
        }
    ]
}

# In-memory log of all API communication requests & responses
API_CALL_HISTORY: List[Dict[str, Any]] = []
_history_id_counter = 1

def add_api_history_record(
    destination: str,
    category: Optional[str],
    target_url: str,
    status: str,
    status_code: str,
    source: str,
    details: str,
    experiences_count: int,
    is_external: bool,
    direction: str = "OUTBOUND (Planner -> Experience Finder)",
    method: str = "GET",
    endpoint: str = "/api/experiences",
    search: Optional[str] = None
) -> Dict[str, Any]:
    global _history_id_counter
    record = {
        "id": _history_id_counter,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "direction": direction,
        "method": method,
        "endpoint": endpoint,
        "destination": destination,
        "category": category or "All",
        "search": search or "",
        "target_url": target_url,
        "status": status,
        "status_code": status_code,
        "source": source,
        "details": details,
        "experiences_count": experiences_count,
        "is_external": is_external
    }
    API_CALL_HISTORY.insert(0, record)
    _history_id_counter += 1
    if len(API_CALL_HISTORY) > 100:
        API_CALL_HISTORY.pop()
    return record

def get_api_history() -> List[Dict[str, Any]]:
    return API_CALL_HISTORY

def clear_api_history():
    global API_CALL_HISTORY
    API_CALL_HISTORY.clear()

def generate_api_history_txt() -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_calls = len(API_CALL_HISTORY)
    ext_calls = sum(1 for r in API_CALL_HISTORY if r.get("is_external"))
    inbound_calls = sum(1 for r in API_CALL_HISTORY if "INBOUND" in str(r.get("direction", "")))
    outbound_calls = total_calls - inbound_calls

    lines = [
        "=" * 80,
        "SMART TRAVEL PLANNER — API COMMUNICATION HISTORY RECORD",
        f"Generated At    : {now_str}",
        f"Configured URL  : {EXPERIENCE_FINDER_API_URL}",
        f"Environment Var : EXPERIENCE_FINDER_API_URL / EXPERIENCE_API_URL (default: http://localhost:8001)",
        "=" * 80,
        "",
        "SUMMARY METRICS:",
        f"  * Total API Events Recorded    : {total_calls}",
        f"  * Outbound Calls (To Finder)   : {outbound_calls}",
        f"  * Inbound Calls (From Finder)  : {inbound_calls}",
        f"  * Live External Successes      : {ext_calls}",
        "",
        "COMMUNICATION LOG ENTRIES (Most Recent First):",
        "-" * 80
    ]

    if not API_CALL_HISTORY:
        lines.append("  (No API recommendation or integration requests recorded yet)")
    else:
        for r in API_CALL_HISTORY:
            dir_str = r.get("direction", "OUTBOUND")
            lines.extend([
                f"[LOG #{r['id']}] {r['timestamp']} | {dir_str} | {r['status']} ({r['status_code']})",
                f"  Endpoint      : {r.get('method', 'GET')} {r.get('endpoint', '')}",
                f"  Destination   : {r['destination']}",
                f"  Category      : {r['category']}",
                f"  Target URL    : {r['target_url']}",
                f"  Data Source   : {r['source']}",
                f"  Items/Count   : {r['experiences_count']}",
                f"  Details       : {r['details']}",
                "-" * 80
            ])

    lines.extend([
        "",
        "=" * 80,
        "END OF API COMMUNICATION HISTORY RECORD",
        "=" * 80
    ])

    return "\n".join(lines)



# =============================================================================
# REAL EXTERNAL HTTPX INTEGRATION
# =============================================================================
async def fetch_experiences_from_finder(
    destination: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    travellers: Optional[int] = None,
    budget: Optional[float] = None,
    trip_id: Optional[int] = None,
    client: Optional[str] = None
) -> Dict[str, Any]:
    """
    Communicates with the independent Experience Finder REST API service via HTTPX.
    Endpoint called:
      GET {EXPERIENCE_FINDER_API_URL}/api/experiences?destination={destination}&category={category}&search={search}&travellers={travellers}&budget={budget}

    Contract & Robustness:
    - Enforces connection timeouts (connect=3.0s, read=5.0s).
    - Validates returned JSON strictly.
    - If the external API fails (connection error, timeout, HTTP 4xx/5xx, invalid JSON),
      it returns an honest ERROR response with Retry action and NEVER pretends it succeeded.
    """
    url = f"{EXPERIENCE_FINDER_API_URL}/api/experiences"
    params = {}
    dest_str = (destination or "").strip()
    if dest_str and dest_str.lower() not in ("all", "all india", "any"):
        params["destination"] = dest_str

    if category and category.strip().lower() not in ("all", "all categories", "any"):
        params["category"] = category.strip()

    if search and search.strip():
        params["search"] = search.strip()

    if limit:
        params["limit"] = limit

    if travellers is not None:
        params["travellers"] = travellers

    if budget is not None:
        params["budget"] = budget

    if trip_id is not None:
        params["trip_id"] = trip_id

    params["client"] = client or "Smart Travel Planner (:8000)"

    query_str = urllib.parse.urlencode(params)
    full_target_url = f"{url}?{query_str}" if query_str else url

    timeout_config = httpx.Timeout(connect=3.0, read=5.0, write=3.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout_config) as http_client:
            logger.info("Calling Experience Finder API: %s with params %s", url, params)
            response = await http_client.get(url, params=params)

            if response.status_code == 200:
                try:
                    raw_data = response.json()
                except Exception as json_err:
                    err_msg = f"External service returned invalid non-JSON payload: {str(json_err)}"
                    logger.error(err_msg)
                    add_api_history_record(
                        destination=dest_str or "All",
                        category=category,
                        target_url=full_target_url,
                        status="INVALID_JSON",
                        status_code="HTTP 200 (Invalid JSON)",
                        source=f"External Experience Finder ({EXPERIENCE_FINDER_API_URL})",
                        details=err_msg,
                        experiences_count=0,
                        is_external=False,
                        search=search
                    )
                    return {
                        "experiences": [],
                        "source": f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
                        "is_external": False,
                        "status": "ERROR",
                        "status_message": "External API returned invalid JSON. Please try again.",
                        "error_detail": err_msg,
                        "retry_available": True,
                        "target_url": full_target_url
                    }

                # Parse experiences list from response
                raw_items = []
                if isinstance(raw_data, dict):
                    raw_items = raw_data.get("experiences", [])
                    if not raw_items and "results" in raw_data:
                        raw_items = raw_data.get("results", [])
                elif isinstance(raw_data, list):
                    raw_items = raw_data

                validated_experiences = []
                for item in raw_items:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    cat = str(item.get("category") or "General").strip()
                    try:
                        price = float(item.get("price") or 0.0)
                    except (ValueError, TypeError):
                        price = 0.0

                    raw_rating = item.get("rating")
                    if raw_rating is not None:
                        try:
                            rating = float(raw_rating)
                        except (ValueError, TypeError):
                            rating = None
                    else:
                        rating = None

                    desc = str(item.get("description") or "").strip()
                    exp_id = item.get("experience_id") or item.get("id") or (len(validated_experiences) + 1)
                    item_dest = str(item.get("destination") or dest_str or "").strip()
                    dur = str(item.get("duration") or "").strip()
                    img = str(item.get("image_url") or "").strip()
                    loc = str(item.get("locality") or "").strip()
                    rev_count = int(item.get("review_count") or 0)

                    validated_experiences.append({
                        "id": exp_id,
                        "name": name,
                        "category": cat,
                        "price": price,
                        "rating": rating,
                        "description": desc,
                        "destination": item_dest,
                        "duration": dur,
                        "image_url": img,
                        "locality": loc,
                        "review_count": rev_count
                    })

                logger.info("Successfully fetched %d experiences from external API", len(validated_experiences))

                status_name = "EMPTY" if len(validated_experiences) == 0 else "SUCCESS"
                query_info = dest_str or "all places"
                if search:
                    query_info += f" matching '{search}'"
                if category and category.lower() != "all":
                    query_info += f" in '{category}'"

                status_msg = (
                    f"Live data from external Experience Finder ({len(validated_experiences)} experiences received)"
                    if len(validated_experiences) > 0
                    else f"No experiences found for {query_info}"
                )

                add_api_history_record(
                    destination=dest_str or "All",
                    category=category,
                    target_url=full_target_url,
                    status=status_name,
                    status_code="HTTP 200 OK",
                    source=f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
                    details=f"Live response received with {len(validated_experiences)} experiences for {query_info}.",
                    experiences_count=len(validated_experiences),
                    is_external=True,
                    search=search
                )

                return {
                    "experiences": validated_experiences,
                    "source": f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
                    "is_external": True,
                    "status": status_name,
                    "status_message": status_msg,
                    "target_url": full_target_url,
                    "retry_available": False,
                    "count": len(validated_experiences),
                    "request_summary": {
                        "destination": dest_str or "All India",
                        "category": category or "All",
                        "search": search or "",
                        "travellers": travellers,
                        "budget": budget,
                        "trip_id": trip_id,
                        "target_url": full_target_url,
                        "client": client or "Smart Travel Planner (:8000)"
                    },
                    "response_summary": {
                        "status_code": 200,
                        "status_text": "HTTP 200 OK",
                        "database": "explorely.db",
                        "peer_service": "Explorely Experience Finder Microservice (:8001)",
                        "places_received": len(validated_experiences)
                    }
                }
            else:
                err_detail = f"External service responded with HTTP error status {response.status_code} ({response.reason_phrase})."
                logger.warning(err_detail)

                add_api_history_record(
                    destination=dest_str or "All",
                    category=category,
                    target_url=full_target_url,
                    status="HTTP_ERROR",
                    status_code=f"HTTP {response.status_code}",
                    source=f"External Experience Finder ({EXPERIENCE_FINDER_API_URL})",
                    details=err_detail,
                    experiences_count=0,
                    is_external=False,
                    search=search
                )

                return {
                    "experiences": [],
                    "source": f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
                    "is_external": False,
                    "status": "ERROR",
                    "status_message": f"External Experience Finder returned error {response.status_code}. Please retry.",
                    "error_detail": err_detail,
                    "retry_available": True,
                    "target_url": full_target_url
                }

    except httpx.TimeoutException as exc:
        err_detail = f"Connection to {EXPERIENCE_FINDER_API_URL} timed out after 3.0 seconds."
        logger.warning(err_detail)
        add_api_history_record(
            destination=dest_str or "All",
            category=category,
            target_url=full_target_url,
            status="TIMEOUT",
            status_code="Connection Timed Out",
            source=f"External Experience Finder ({EXPERIENCE_FINDER_API_URL})",
            details=err_detail,
            experiences_count=0,
            is_external=False,
            search=search
        )
        return {
            "experiences": [],
            "source": f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
            "is_external": False,
            "status": "ERROR",
            "status_message": f"Experience Finder service at {EXPERIENCE_FINDER_API_URL} timed out.",
            "error_detail": err_detail,
            "retry_available": True,
            "target_url": full_target_url
        }

    except httpx.ConnectError as exc:
        err_detail = f"Connection refused or service unreachable at {EXPERIENCE_FINDER_API_URL} ({type(exc).__name__})."
        logger.warning(err_detail)
        add_api_history_record(
            destination=dest_str or "All",
            category=category,
            target_url=full_target_url,
            status="UNAVAILABLE",
            status_code="Connection Refused / Offline",
            source=f"External Experience Finder ({EXPERIENCE_FINDER_API_URL})",
            details=err_detail,
            experiences_count=0,
            is_external=False,
            search=search
        )
        return {
            "experiences": [],
            "source": f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
            "is_external": False,
            "status": "ERROR",
            "status_message": f"Experience Finder service is offline or unreachable at {EXPERIENCE_FINDER_API_URL}.",
            "error_detail": err_detail,
            "retry_available": True,
            "target_url": full_target_url
        }

    except Exception as exc:
        err_detail = f"Unexpected request failure communicating with {EXPERIENCE_FINDER_API_URL}: {str(exc)}"
        logger.warning(err_detail)
        add_api_history_record(
            destination=dest_str or "All",
            category=category,
            target_url=full_target_url,
            status="REQUEST_ERROR",
            status_code="Request Error",
            source=f"External Experience Finder ({EXPERIENCE_FINDER_API_URL})",
            details=err_detail,
            experiences_count=0,
            is_external=False,
            search=search
        )
        return {
            "experiences": [],
            "source": f"External Experience Finder API ({EXPERIENCE_FINDER_API_URL})",
            "is_external": False,
            "status": "ERROR",
            "status_message": f"Could not communicate with Experience Finder at {EXPERIENCE_FINDER_API_URL}.",
            "error_detail": err_detail,
            "retry_available": True,
            "target_url": full_target_url
        }


# =============================================================================
# LOCAL DEVELOPMENT MOCK ADAPTER
# (Kept strictly separate from the real integration. Impossible to mistake for external API)
# =============================================================================
def get_local_dev_mock_experiences(
    destination: str,
    category: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Clearly labelled local development adapter for testing UI and development workflows
    when teammate API is not yet active.
    Returns mock experiences with prominent disclaimer metadata and zero false external claims.
    """
    matched_dest = None
    dest_clean = (destination or "Goa").strip().lower()
    for d in DEV_MOCK_CATALOG.keys():
        if d.lower() in dest_clean or dest_clean in d.lower():
            matched_dest = d
            break

    raw_list = DEV_MOCK_CATALOG.get(matched_dest, []) if matched_dest else []
    results = list(raw_list)

    if category and category.strip().lower() != "all":
        results = [e for e in results if e["category"].lower() == category.strip().lower()]

    if search and search.strip():
        s = search.strip().lower()
        results = [e for e in results if s in e["name"].lower() or s in e.get("description", "").lower() or s in e.get("category", "").lower()]

    full_target_url = f"{EXPERIENCE_FINDER_API_URL}/api/experiences?destination={destination}&category={category or 'All'}"
    if search:
        full_target_url += f"&search={search}"

    add_api_history_record(
        destination=destination,
        category=category,
        target_url=full_target_url,
        status="DEV_MOCK",
        status_code="DEV MOCK ADAPTER",
        source="Local Development Adapter (MOCK DATA - NOT REAL API)",
        details=f"Local mock adapter invoked for '{destination}'. Returned {len(results)} mock items.",
        experiences_count=len(results),
        is_external=False,
        search=search
    )

    return {
        "experiences": results,
        "source": "Local Development Adapter (MOCK DATA - NOT REAL API)",
        "is_external": False,
        "status": "DEV_MOCK",
        "status_message": f"⚠️ LOCAL MOCK DATA: Teammate external service is not active. Loaded {len(results)} mock experiences for testing only.",
        "target_url": full_target_url,
        "retry_available": True
    }
