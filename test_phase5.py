"""
=============================================================================
SMART TRAVEL PLANNER — PHASE 5 AUTOMATED VERIFICATION SUITE
Recommendations Integration:
1. Environment Configuration: Reads EXPERIENCE_FINDER_API_URL dynamically
2. Connection Timeouts & Failure Handling:
   - Gracefully handles unreachable services, connection refusal, timeouts, HTTP errors, invalid JSON
   - Returns clear error state with retry_available=True
   - NEVER pretends a failed request succeeded
3. Clearly Labelled Local Development Adapter:
   - Kept strictly separate from real integration
   - Impossible to mistake mock results for a successful external API response
4. Multi-Destination Testing:
   - Tested with at least two different destinations (e.g. Goa, Chennai, Munnar)
5. Rating Fidelity:
   - Ratings supplied by API are preserved; when not supplied, rating is None (never invent fake ratings)
6. Live External API Simulation:
   - Successful external response (HTTP 200 with experiences)
   - Empty external response (HTTP 200 with 0 experiences)
   - HTTP 500 server error handling
   - Invalid non-JSON payload handling
7. Add to Itinerary & Duplicate Prevention:
   - Adds experience to trip itinerary
   - Prevents duplicate itinerary entries when user adds the same experience repeatedly
8. Direct SQLite on-disk persistence check
=============================================================================
"""

import os
import sys
import json
import time
import sqlite3
import httpx
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Ensure workspace is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ensure utf-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.main import app
from app.config import EXPERIENCE_FINDER_API_URL, EXPERIENCE_API_URL
from app.services.experience_service import (
    fetch_experiences_from_finder,
    get_local_dev_mock_experiences,
    DEV_MOCK_CATALOG
)

client = TestClient(app)
DB_PATH = os.path.join(BASE_DIR, "travel_planner.db")


def run_phase5_tests():
    print("=" * 70)
    print("SMART TRAVEL PLANNER — PHASE 5 TEST SUITE: RECOMMENDATIONS")
    print("=" * 70)

    ts = int(time.time())
    email = f"explorer_recs_{ts}@example.com"

    # ---------------------------------------------------------
    # 0. Setup: Register user & create trip
    # ---------------------------------------------------------
    print("\n[STEP 0] Registering test user and creating trip...")
    reg_res = client.post("/api/users/register", json={
        "name": "Meera Explorer",
        "email": email,
        "password": "Password123!"
    })
    assert reg_res.status_code == 201, f"Failed registration: {reg_res.text}"
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Trip 1: Goa
    trip_goa_res = client.post("/api/trips", json={
        "trip_name": "Goa Beach & Culture Holiday",
        "destination": "Goa",
        "start_date": "2026-11-20",
        "end_date": "2026-11-25",
        "budget": 30000.0,
        "travellers": 3,
        "interests": ["Beach", "Adventure", "Culture"],
        "description": "Goa trip testing recommendations"
    }, headers=headers)
    assert trip_goa_res.status_code == 201
    goa_trip_id = trip_goa_res.json()["trip_id"]

    # Trip 2: Chennai (Second Destination)
    trip_chennai_res = client.post("/api/trips", json={
        "trip_name": "Chennai Heritage Trail",
        "destination": "Chennai",
        "start_date": "2026-12-10",
        "end_date": "2026-12-14",
        "budget": 25000.0,
        "travellers": 2,
        "interests": ["Culture", "Beach", "Food"],
        "description": "Chennai cultural exploration"
    }, headers=headers)
    assert trip_chennai_res.status_code == 201
    chennai_trip_id = trip_chennai_res.json()["trip_id"]

    print(f"  [PASS] Setup complete: Trip 1 ID {goa_trip_id} (Goa), Trip 2 ID {chennai_trip_id} (Chennai)")

    # ---------------------------------------------------------
    # 1. Environment Configuration Verification
    # ---------------------------------------------------------
    print("\n[TEST 1] Verifying EXPERIENCE_FINDER_API_URL environment configuration...")
    assert EXPERIENCE_FINDER_API_URL, "EXPERIENCE_FINDER_API_URL must be defined"
    assert not EXPERIENCE_FINDER_API_URL.endswith("/"), "URL should be normalized without trailing slash"
    print(f"  [PASS] Configuration verified: EXPERIENCE_FINDER_API_URL = '{EXPERIENCE_FINDER_API_URL}'")

    # ---------------------------------------------------------
    # 2. Failed External Request Handling (Service Offline / Connection Refused)
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing failed external request handling when service is offline...")
    # Port 8001 is offline in standard test run
    res_offline = client.get(f"/api/trips/{goa_trip_id}/recommendations", headers=headers)
    assert res_offline.status_code == 200
    offline_data = res_offline.json()

    # Must NEVER pretend a failed request succeeded
    assert offline_data["is_external"] is False, "Must not claim external success on failed request"
    assert offline_data["status"] == "ERROR", f"Expected status ERROR, got {offline_data['status']}"
    assert offline_data["retry_available"] is True, "Retry action must be available"
    assert offline_data["experiences"] == [], "Experiences list must be empty on failure"
    assert "error_detail" in offline_data and offline_data["error_detail"]
    print(f"  [PASS] Failed request handled honestly: Status=ERROR, is_external=False, Retry Available=True")
    print(f"         Error detail: {offline_data['error_detail'][:70]}...")

    # ---------------------------------------------------------
    # 3. Clearly Labelled Local Development Mock Adapter
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing clearly labelled local development mock adapter...")
    res_mock = client.get(f"/api/trips/{goa_trip_id}/recommendations?use_dev_adapter=true", headers=headers)
    assert res_mock.status_code == 200
    mock_data = res_mock.json()

    assert mock_data["is_external"] is False, "Mock adapter must not claim is_external"
    assert mock_data["status"] == "DEV_MOCK", f"Expected DEV_MOCK, got {mock_data['status']}"
    assert "MOCK" in mock_data["source"].upper(), f"Source must explicitly indicate MOCK: {mock_data['source']}"
    assert "MOCK" in mock_data["status_message"].upper(), "Status message must indicate MOCK"
    assert len(mock_data["experiences"]) > 0
    print(f"  [PASS] Local Development Mock Adapter verified: Source='{mock_data['source']}'")
    print(f"         Loaded {len(mock_data['experiences'])} mock items with explicit mock disclaimers")

    # ---------------------------------------------------------
    # 4. Multi-Destination Testing (Destination 1: Goa, Destination 2: Chennai)
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing multiple destinations via Development Adapter...")
    # Destination 1: Goa
    res_goa = client.get(f"/api/trips/{goa_trip_id}/recommendations?use_dev_adapter=true", headers=headers)
    goa_items = res_goa.json()["experiences"]
    assert any("Goa" in item["name"] or "Diving" in item["name"] for item in goa_items)

    # Destination 2: Chennai
    res_chennai = client.get(f"/api/trips/{chennai_trip_id}/recommendations?use_dev_adapter=true", headers=headers)
    chennai_items = res_chennai.json()["experiences"]
    assert len(chennai_items) > 0
    assert any("Marina" in item["name"] or "Kapaleeshwarar" in item["name"] for item in chennai_items)

    # Direct query endpoint for Chennai
    res_direct = client.get("/api/experiences/recommendations?destination=Chennai&category=Culture&use_dev_adapter=true")
    assert res_direct.status_code == 200
    direct_items = res_direct.json()["experiences"]
    assert all(item["category"].lower() == "culture" for item in direct_items)
    print(f"  [PASS] Destination 1 (Goa): {len(goa_items)} experiences returned")
    print(f"  [PASS] Destination 2 (Chennai): {len(chennai_items)} experiences returned (Culture filtered: {len(direct_items)})")

    # ---------------------------------------------------------
    # 5. Rating Fidelity (Preserve rating when supplied, None when omitted)
    # ---------------------------------------------------------
    print("\n[TEST 5] Testing rating fidelity (Never invent ratings)...")
    rated_item = next((i for i in goa_items if i["rating"] is not None), None)
    unrated_item = next((i for i in goa_items if i["rating"] is None), None)

    assert rated_item is not None, "At least one rated item expected"
    assert unrated_item is not None, "At least one unrated item expected for testing fidelity"
    assert isinstance(rated_item["rating"], float) and rated_item["rating"] > 0
    assert unrated_item["rating"] is None, f"Expected unrated item rating to be None, got {unrated_item['rating']}"
    print(f"  [PASS] Rated item ({rated_item['name']}): Rating = {rated_item['rating']}")
    print(f"  [PASS] Unrated item ({unrated_item['name']}): Rating = None (No invented ratings)")

    # ---------------------------------------------------------
    # 6. Live External API Simulation (Successful, Empty, Error, Invalid JSON)
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing simulated external HTTPX API responses...")

    # 6a. Successful External Response
    mock_external_payload = {
        "destination": "Chennai",
        "experiences": [
            {
                "id": 501,
                "name": "DakshinaChitra Heritage Museum Tour",
                "category": "Culture",
                "price": 350.0,
                "rating": 4.6,
                "description": "Living history museum of South Indian heritage and architecture."
            },
            {
                "id": 502,
                "name": "Kalakshetra Classical Dance Performance",
                "category": "Culture",
                "price": 500.0,
                "rating": 4.9,
                "description": "Renowned academy for preservation of Bharatanatyam dance traditions."
            }
        ]
    }

    mock_resp_200 = httpx.Response(
        status_code=200,
        content=json.dumps(mock_external_payload),
        headers={"Content-Type": "application/json"}
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_200
        res_ext_success = client.get(f"/api/trips/{chennai_trip_id}/recommendations", headers=headers)
        assert res_ext_success.status_code == 200
        data_ext_success = res_ext_success.json()

        assert data_ext_success["is_external"] is True
        assert data_ext_success["status"] == "SUCCESS"
        assert len(data_ext_success["experiences"]) == 2
        assert data_ext_success["experiences"][0]["name"] == "DakshinaChitra Heritage Museum Tour"
        print("  [PASS] 6a. Successful External API call verified (is_external=True, status=SUCCESS)")

    # 6b. Empty External Response
    mock_resp_empty = httpx.Response(
        status_code=200,
        content=json.dumps({"destination": "Atlantis", "experiences": []}),
        headers={"Content-Type": "application/json"}
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_empty
        res_ext_empty = client.get(f"/api/trips/{chennai_trip_id}/recommendations", headers=headers)
        assert res_ext_empty.status_code == 200
        data_ext_empty = res_ext_empty.json()

        assert data_ext_empty["is_external"] is True
        assert data_ext_empty["status"] == "EMPTY"
        assert len(data_ext_empty["experiences"]) == 0
        print("  [PASS] 6b. Empty External API response handled cleanly (status=EMPTY, count=0)")

    # 6c. External Server Error (HTTP 500)
    mock_resp_500 = httpx.Response(
        status_code=500,
        content="Internal Server Error on Experience Finder",
        headers={"Content-Type": "text/plain"}
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_500
        res_ext_500 = client.get(f"/api/trips/{chennai_trip_id}/recommendations", headers=headers)
        assert res_ext_500.status_code == 200
        data_ext_500 = res_ext_500.json()

        assert data_ext_500["is_external"] is False
        assert data_ext_500["status"] == "ERROR"
        assert data_ext_500["retry_available"] is True
        assert "error" in data_ext_500["status_message"].lower() or "500" in data_ext_500["error_detail"]
        print("  [PASS] 6c. HTTP 500 external error handled honestly (status=ERROR, retry_available=True)")

    # 6d. Invalid Non-JSON Response
    mock_resp_invalid_json = httpx.Response(
        status_code=200,
        content="<html><body>Bad Gateway</body></html>",
        headers={"Content-Type": "text/html"}
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp_invalid_json
        res_ext_inv = client.get(f"/api/trips/{chennai_trip_id}/recommendations", headers=headers)
        assert res_ext_inv.status_code == 200
        data_ext_inv = res_ext_inv.json()

        assert data_ext_inv["is_external"] is False
        assert data_ext_inv["status"] == "ERROR"
        assert "JSON" in data_ext_inv["error_detail"] or "invalid" in data_ext_inv["status_message"].lower()
        print("  [PASS] 6d. Invalid non-JSON payload handled safely (status=ERROR)")

    # ---------------------------------------------------------
    # 7. Add to Itinerary & Duplicate Entry Prevention
    # ---------------------------------------------------------
    print("\n[TEST 7] Testing Add to Itinerary & Duplicate Entry Prevention...")
    exp_to_add = {
        "date": "2026-11-20",
        "time": "10:00",
        "activity": "Scuba Diving at Grande Island",
        "location": "Grande Island, Goa (Adventure)",
        "category": "Adventure",
        "estimated_cost": 2500.0,
        "notes": "Added from Experience Finder recommendation"
    }

    # First add: should succeed
    res_add1 = client.post(f"/api/trips/{goa_trip_id}/itinerary", json=exp_to_add, headers=headers)
    assert res_add1.status_code == 201
    item1_id = res_add1.json()["item_id"]
    print(f"  [PASS] First Add to Itinerary succeeded (Item ID: {item1_id})")

    # Second add of identical experience: must NOT create a duplicate entry
    res_add2 = client.post(f"/api/trips/{goa_trip_id}/itinerary", json=exp_to_add, headers=headers)
    assert res_add2.status_code in [200, 201]
    item2_id = res_add2.json()["item_id"]
    assert item2_id == item1_id, f"Expected existing item ID {item1_id}, got {item2_id}"

    # Verify directly via GET /api/trips/{trip_id}/itinerary
    res_itin_list = client.get(f"/api/trips/{goa_trip_id}/itinerary", headers=headers)
    assert res_itin_list.status_code == 200
    all_activities = [i["activity"] for i in res_itin_list.json()]
    count_scuba = all_activities.count("Scuba Diving at Grande Island")
    assert count_scuba == 1, f"Expected exactly 1 Scuba Diving entry, found {count_scuba} duplicates!"
    print(f"  [PASS] Repeated Add to Itinerary prevented duplicate entry (Exactly {count_scuba} entry exists)")

    # ---------------------------------------------------------
    # 8. Direct SQLite On-Disk Persistence Verification
    # ---------------------------------------------------------
    print("\n[TEST 8] Verifying SQLite on-disk persistence...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT item_id, trip_id, activity, category, estimated_cost FROM itinerary WHERE trip_id = ? AND activity = ?",
                (goa_trip_id, "Scuba Diving at Grande Island"))
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 1, f"Expected 1 persisted row on SQLite disk, got {len(rows)}"
    assert rows[0][2] == "Scuba Diving at Grande Island"
    assert rows[0][4] == 2500.0
    print(f"  [PASS] SQLite persistence verified on disk (Activity='{rows[0][2]}', Cost=Rs.{rows[0][4]})")

    print("\n" + "=" * 70)
    print("ALL PHASE 5 RECOMMENDATIONS TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_phase5_tests()
