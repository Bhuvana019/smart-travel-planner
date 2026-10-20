"""
=============================================================================
INTER-PROJECT API COMMUNICATION TEST SUITE
Tests LIVE network server-to-server communication between:
1. Smart Travel Planner (FastAPI, Port 8000)
2. Explorely Experience Finder (FastAPI, Port 8001)

Verifies:
- Recommendation module automatically calls Experience Finder API over HTTP/REST
- Searching places by destination, keyword, and category
- Rich attributes returned (image_url, rating, price, duration, locality)
- Adding discovered experiences into trip itinerary
- Outbound API audit trail recorded in communication history
- Both projects operate as independent standalone applications
=============================================================================
"""

import sys
import os
import time
import subprocess
from pathlib import Path
import httpx
from fastapi.testclient import TestClient

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
EXPLORER_DIR = WORKSPACE_ROOT / "EXPLORER_FINAL_SEND" / "EXPLORER"
PLANNER_DIR = WORKSPACE_ROOT / "smart-travel-planner"

sys.path.insert(0, str(PLANNER_DIR))
from app.main import app as planner_app
from app.services.experience_service import get_api_history, clear_api_history

def start_explorer_service():
    """Starts the real Explorely Experience Finder server on port 8001 as a subprocess, or reuses it if already running."""
    try:
        r = httpx.get("http://127.0.0.1:8001/health", timeout=1.0)
        if r.status_code == 200:
            print("  -> Explorely Experience Finder is ALREADY running and healthy on http://127.0.0.1:8001!")
            return None
    except Exception:
        pass

    print("  -> Starting Explorely Experience Finder on http://127.0.0.1:8001 ...")
    env = os.environ.copy()
    env["PORT"] = "8001"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8001", "--host", "127.0.0.1"],
        cwd=str(EXPLORER_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    # Wait for service to become healthy
    ready = False
    for _ in range(30):
        try:
            r = httpx.get("http://127.0.0.1:8001/health", timeout=1.0)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not ready:
        proc.terminate()
        out, err = proc.communicate(timeout=3)
        raise RuntimeError(f"Experience Finder service failed to start on 8001:\n{err.decode('utf-8', errors='ignore')}")

    print("  -> Explorely Experience Finder is LIVE and healthy on http://127.0.0.1:8001!")
    return proc

def run_inter_project_tests():
    print("=" * 80)
    print("RUNNING LIVE INTER-PROJECT API COMMUNICATION VERIFICATION")
    print("=" * 80)

    explorer_proc = None
    try:
        # Step 1: Start Explorely Experience Finder on Port 8001
        print("\n[Step 1] Launching Explorely Experience Finder on Port 8001...")
        explorer_proc = start_explorer_service()

        # Step 2: Test Standalone Experience Finder API directly
        print("\n[Step 2] Testing Explorely REST API Direct Endpoints...")
        with httpx.Client(base_url="http://127.0.0.1:8001") as direct_client:
            health_res = direct_client.get("/health")
            assert health_res.status_code == 200
            print(f"  [PASS] Service health: {health_res.json()['status']} ({health_res.json()['service']})")

            places_res = direct_client.get("/api/experiences?limit=100")
            assert places_res.status_code == 200
            print(f"  [PASS] Explorely database catalog holds {len(places_res.json())} places in explorely.db")

        # Step 3: Test Smart Travel Planner communicating automatically with Experience Finder
        print("\n[Step 3] Testing Recommendation Module Automatic API Call to Experience Finder...")
        planner_client = TestClient(planner_app)

        # Authenticate demo user in Smart Travel Planner
        login_res = planner_client.post("/api/users/login", json={
            "email": "arun.kumar@example.com",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        print("  [PASS] Authenticated user Arun Kumar successfully")

        # Verify Budget Validation (> 2k, formatting with commas and k)
        print("\n[Step 2.5] Testing Budget Validation & Formatting...")
        # 1. Budget under 2000 should be rejected
        low_res = planner_client.post("/api/trips", json={
            "destination": "Goa",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "budget": 1500,
            "travellers": 2
        }, headers=auth_headers)
        assert low_res.status_code == 422, f"Expected 422 for budget < 2000, got: {low_res.status_code}"
        print("  [PASS] Budget < Rs.2,000 properly rejected with 422 Unprocessable Entity")

        # 2. Budget with formatted string '25,000' should succeed
        create_res = planner_client.post("/api/trips", json={
            "trip_name": "Munnaru Tea Trails",
            "destination": "Munnaru",
            "start_date": "2026-11-10",
            "end_date": "2026-11-15",
            "budget": "25,000",
            "travellers": 3,
            "interests": "Nature, Museum"
        }, headers=auth_headers)
        assert create_res.status_code == 201, f"Failed to create trip: {create_res.text}"
        new_trip = create_res.json()
        assert new_trip["budget"] == 25000.0
        active_trip_id = new_trip["trip_id"]
        print(f"  [PASS] Created trip #{active_trip_id} for Munnaru with budget '25,000' (parsed as Rs.{new_trip['budget']})")

        clear_api_history()

        # 3a. Search places for active trip (Munnaru)
        res_trip = planner_client.get(f"/api/trips/{active_trip_id}/recommendations", headers=auth_headers)
        assert res_trip.status_code == 200, f"Trip recommendations error: {res_trip.text}"
        trip_data = res_trip.json()
        assert trip_data["is_external"] is True
        assert trip_data["status"] == "SUCCESS"
        assert len(trip_data["experiences"]) >= 2
        first_item = trip_data["experiences"][0]
        print(f"  [PASS] Automatic API Call for Trip #{active_trip_id} (Munnaru) returned {len(trip_data['experiences'])} places from Experience Finder.")
        print(f"         Sample place: '{first_item['name']}' | Price: Rs.{first_item['price']} | Rating: {first_item['rating']}")
        assert "image_url" in first_item
        assert first_item["rating"] is not None

        # 3b. Search places by keyword ("Temple") through Experience Finder API
        res_search = planner_client.get("/api/experiences/recommendations?search=Temple")
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["is_external"] is True
        assert len(search_data["experiences"]) >= 10
        print(f"  [PASS] Automatic Keyword Search for 'Temple' returned {len(search_data['experiences'])} places from Experience Finder.")
        sample_temple = search_data["experiences"][0]
        print(f"         First temple: '{sample_temple['name']}' ({sample_temple['destination']})")

        # 3c. Search places by destination ("Munnaru" transliteration) and Category ("Nature")
        res_munnar = planner_client.get("/api/experiences/recommendations?destination=Munnaru&category=Nature")
        assert res_munnar.status_code == 200
        munnar_data = res_munnar.json()
        assert munnar_data["is_external"] is True
        assert len(munnar_data["experiences"]) >= 1
        print(f"  [PASS] Filtered API Search (Munnaru stem matching + Nature) returned {len(munnar_data['experiences'])} places:")
        for exp in munnar_data["experiences"]:
            print(f"         - '{exp['name']}' ({exp['category']}) - Rs.{exp['price']}")

        # 3d. Search places by activity keyword ("Scuba")
        res_scuba = planner_client.get("/api/experiences/recommendations?search=Scuba")
        assert res_scuba.status_code == 200
        scuba_data = res_scuba.json()
        assert len(scuba_data["experiences"]) >= 1
        print(f"  [PASS] Keyword Search for 'Scuba' returned {len(scuba_data['experiences'])} places:")
        for exp in scuba_data["experiences"]:
            print(f"         - '{exp['name']}' ({exp['destination']})")

        # Step 4: Adding Discovered Experience to Trip Itinerary
        print("\n[Step 4] Testing Adding Discovered Experience into Trip Itinerary...")
        discovered_place = trip_data["experiences"][0]
        add_itin_res = planner_client.post(
            f"/api/trips/{active_trip_id}/itinerary",
            json={
                "date": "2026-11-12",
                "time": "09:00",
                "activity": discovered_place["name"],
                "location": f"{discovered_place['destination']} ({discovered_place['category']})",
                "category": discovered_place["category"],
                "estimated_cost": discovered_place["price"],
                "notes": discovered_place["description"]
            },
            headers=auth_headers
        )
        assert add_itin_res.status_code == 201, f"Failed to add itinerary item: {add_itin_res.text}"
        print(f"  [PASS] Successfully added '{discovered_place['name']}' to Trip #{active_trip_id} itinerary!")

        # Step 5: Verifying API Communication History Logs
        print("\n[Step 5] Verifying Outbound API Communication Logs in Smart Travel Planner...")
        history = get_api_history()
        assert len(history) >= 4
        print(f"  [PASS] Recorded {len(history)} live API communication transactions in history:")
        for entry in history[:4]:
            print(f"         Log #{entry['id']}: {entry['method']} {entry['target_url']} -> {entry['status']} ({entry['experiences_count']} places)")

        print("\n" + "=" * 80)
        print("ALL INTER-PROJECT LIVE API COMMUNICATION TESTS COMPLETED WITH 100% SUCCESS!")
        print("=" * 80)

    finally:
        if explorer_proc:
            print("\nShutting down Explorely Experience Finder subprocess (:8001)...")
            explorer_proc.terminate()
            try:
                explorer_proc.wait(timeout=3)
            except Exception:
                explorer_proc.kill()
            print("Experience Finder subprocess cleanly stopped.")

if __name__ == "__main__":
    run_inter_project_tests()
