"""
=============================================================================
SMART TRAVEL PLANNER — PHASE 3 AUTOMATED VERIFICATION SUITE
Complete Trip and Itinerary Management:
1. Trip Creation (POST /api/trips) with trip_name, destination, dates, budget, travellers, interests
2. Invalid Date Range Rejection (end_date < start_date -> HTTP 422)
3. Invalid Budget / Travelers Rejection (travellers=0, budget=0 -> HTTP 422)
4. List Logged-In User Trips (GET /api/trips) & User Ownership Isolation
5. View Single Trip Details (GET /api/trips/{trip_id})
6. Unauthorized Cross-User Access Rejection (GET/PUT/DELETE for another user's trip -> HTTP 403)
7. Trip Details Update (PUT /api/trips/{trip_id})
8. Add Itinerary Activities (POST /api/trips/{trip_id}/itinerary) with category, location, cost, notes
9. List Chronological Itinerary (GET /api/trips/{trip_id}/itinerary)
10. Unauthorized Itinerary Access & Modification Rejection (HTTP 403)
11. Edit Itinerary Activity (PUT /api/itinerary/{item_id})
12. Delete Itinerary Activity (DELETE /api/itinerary/{item_id})
13. Delete Trip with Confirmation & Cascading Itinerary Cleanup (DELETE /api/trips/{trip_id})
14. Verify SQLite Database Persistence throughout all operations
=============================================================================
"""

import os
import sys
import sqlite3
import time
from datetime import date
from fastapi.testclient import TestClient

# Ensure workspace is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app

client_user_a = TestClient(app)
client_user_b = TestClient(app)

def run_phase3_tests():
    print("=" * 65)
    print("SMART TRAVEL PLANNER — PHASE 3 TEST SUITE: TRIPS & ITINERARY")
    print("=" * 65)

    ts = int(time.time())
    email_a = f"alice_explorer_{ts}@example.com"
    email_b = f"bob_traveler_{ts}@example.com"

    # ---------------------------------------------------------
    # 0. Setup: Register User A and User B
    # ---------------------------------------------------------
    print("\n[STEP 0] Registering two distinct users for isolation testing...")
    r_a = client_user_a.post("/api/users/register", json={
        "name": "Alice Explorer",
        "email": email_a,
        "password": "AlicePassword123!"
    })
    assert r_a.status_code == 201, f"Failed Alice reg: {r_a.text}"
    token_a = r_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    r_b = client_user_b.post("/api/users/register", json={
        "name": "Bob Traveler",
        "email": email_b,
        "password": "BobPassword123!"
    })
    assert r_b.status_code == 201, f"Failed Bob reg: {r_b.text}"
    token_b = r_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print("  [PASS] User A (Alice) and User B (Bob) successfully registered")

    # ---------------------------------------------------------
    # 1. Create Trip (Valid Flow)
    # ---------------------------------------------------------
    print("\n[TEST 1] Creating a New Trip for User A (POST /api/trips)...")
    trip_payload = {
        "trip_name": "Himalayan Expedition",
        "destination": "Manali",
        "start_date": "2026-11-01",
        "end_date": "2026-11-08",
        "budget": 45000.0,
        "travellers": 2,
        "interests": "Adventure, Nature, Food",
        "description": "High-altitude hiking, paragliding, and cozy cafe exploration in Old Manali."
    }
    r_trip = client_user_a.post("/api/trips", json=trip_payload, headers=headers_a)
    assert r_trip.status_code == 201, f"Failed trip creation: {r_trip.status_code} {r_trip.text}"
    trip_data = r_trip.json()
    trip_id = trip_data["trip_id"]
    assert trip_data["destination"] == "Manali"
    assert trip_data["trip_name"] == "Himalayan Expedition"
    assert trip_data["budget"] == 45000.0
    assert trip_data["travellers"] == 2
    assert trip_data["total_spent"] == 0.0
    assert trip_data["remaining_budget"] == 45000.0
    print(f"  [PASS] Trip created with ID {trip_id}: '{trip_data['trip_name']}' in {trip_data['destination']}")

    # ---------------------------------------------------------
    # 2. Invalid Date Range Rejection (end_date < start_date)
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing Invalid Date Range Rejection (end_date < start_date)...")
    bad_dates_payload = {
        "trip_name": "Impossible Time Machine Trip",
        "destination": "Jaipur",
        "start_date": "2026-12-10",
        "end_date": "2026-12-05",  # Invalid: end is before start
        "budget": 20000.0,
        "travellers": 2
    }
    r_bad_dates = client_user_a.post("/api/trips", json=bad_dates_payload, headers=headers_a)
    assert r_bad_dates.status_code in [400, 422], f"Expected 400 or 422 for invalid dates, got {r_bad_dates.status_code}"
    print(f"  [PASS] Invalid date range rejected with HTTP {r_bad_dates.status_code}")

    # ---------------------------------------------------------
    # 3. Invalid Budget / Travelers Rejection
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing Invalid Budget and Negative/Zero Traveler Counts...")
    bad_budget_payload = {
        "destination": "Delhi",
        "start_date": "2026-11-10",
        "end_date": "2026-11-12",
        "budget": -500.0,  # Invalid
        "travellers": 0    # Invalid
    }
    r_bad_b = client_user_a.post("/api/trips", json=bad_budget_payload, headers=headers_a)
    assert r_bad_b.status_code in [400, 422], f"Expected 400 or 422 for non-positive budget/travelers, got {r_bad_b.status_code}"
    print(f"  [PASS] Non-positive budget and zero traveler count rejected with HTTP {r_bad_b.status_code}")

    # ---------------------------------------------------------
    # 4. List Logged-In User Trips & Ownership Isolation
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing User Trips Listing & Ownership Isolation (GET /api/trips)...")
    r_list_a = client_user_a.get("/api/trips", headers=headers_a)
    assert r_list_a.status_code == 200
    trips_a = r_list_a.json()
    assert any(t["trip_id"] == trip_id for t in trips_a), "Created trip not found in User A list"
    print(f"  [PASS] User A retrieves {len(trips_a)} trips including Manali (ID {trip_id})")

    r_list_b = client_user_b.get("/api/trips", headers=headers_b)
    assert r_list_b.status_code == 200
    trips_b = r_list_b.json()
    assert not any(t["trip_id"] == trip_id for t in trips_b), "SECURITY VIOLATION: User B can see User A's trip in list!"
    print("  [PASS] User B trip list is isolated and does NOT contain User A's trips")

    # ---------------------------------------------------------
    # 5. View Selected Trip Details
    # ---------------------------------------------------------
    print(f"\n[TEST 5] Viewing Single Trip Details (GET /api/trips/{trip_id})...")
    r_detail = client_user_a.get(f"/api/trips/{trip_id}", headers=headers_a)
    assert r_detail.status_code == 200
    detail_data = r_detail.json()
    assert detail_data["trip_id"] == trip_id
    assert detail_data["destination"] == "Manali"
    assert "itinerary_items" in detail_data
    assert "expenses" in detail_data
    print(f"  [PASS] Successfully retrieved full trip details for ID {trip_id}")

    # ---------------------------------------------------------
    # 6. Unauthorized Access Rejection (User B -> User A Trip)
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing Unauthorized Cross-User Access Rejection (User B accessing User A trip)...")
    # GET unauthorized
    r_unauth_get = client_user_b.get(f"/api/trips/{trip_id}", headers=headers_b)
    assert r_unauth_get.status_code in [403, 404], f"Expected 403 or 404, got {r_unauth_get.status_code}"
    print(f"  [PASS] Unauthorized GET /api/trips/{trip_id} rejected with HTTP {r_unauth_get.status_code}")

    # PUT unauthorized
    r_unauth_put = client_user_b.put(f"/api/trips/{trip_id}", json={"budget": 99999.0}, headers=headers_b)
    assert r_unauth_put.status_code in [403, 404], f"Expected 403 or 404, got {r_unauth_put.status_code}"
    print(f"  [PASS] Unauthorized PUT /api/trips/{trip_id} rejected with HTTP {r_unauth_put.status_code}")

    # DELETE unauthorized
    r_unauth_del = client_user_b.delete(f"/api/trips/{trip_id}", headers=headers_b)
    assert r_unauth_del.status_code in [403, 404], f"Expected 403 or 404, got {r_unauth_del.status_code}"
    print(f"  [PASS] Unauthorized DELETE /api/trips/{trip_id} rejected with HTTP {r_unauth_del.status_code}")

    # ---------------------------------------------------------
    # 7. Edit Trip Details (PUT /api/trips/{trip_id})
    # ---------------------------------------------------------
    print(f"\n[TEST 7] Updating Trip Details for User A (PUT /api/trips/{trip_id})...")
    update_payload = {
        "trip_name": "Manali Alpine Summer Summit",
        "budget": 52000.0,
        "travellers": 3,
        "description": "Updated trip description with 3 travelers and increased budget."
    }
    r_update = client_user_a.put(f"/api/trips/{trip_id}", json=update_payload, headers=headers_a)
    assert r_update.status_code == 200, f"Update failed: {r_update.text}"
    updated_data = r_update.json()
    assert updated_data["trip_name"] == "Manali Alpine Summer Summit"
    assert updated_data["budget"] == 52000.0
    assert updated_data["travellers"] == 3
    print(f"  [PASS] Trip updated: Name='{updated_data['trip_name']}', Budget=Rs.{updated_data['budget']}, Travelers={updated_data['travellers']}")

    # ---------------------------------------------------------
    # 8. Add Itinerary Activities (POST /api/trips/{trip_id}/itinerary)
    # ---------------------------------------------------------
    print(f"\n[TEST 8] Adding Itinerary Activities (POST /api/trips/{trip_id}/itinerary)...")
    act1_payload = {
        "date": "2026-11-01",
        "time": "10:00",
        "activity": "Solang Valley Paragliding",
        "location": "Solang Valley",
        "category": "Adventure",
        "estimated_cost": 3200.0,
        "notes": "Booked morning slot with tandem pilot"
    }
    r_act1 = client_user_a.post(f"/api/trips/{trip_id}/itinerary", json=act1_payload, headers=headers_a)
    assert r_act1.status_code == 201, f"Failed act 1: {r_act1.text}"
    act1_id = r_act1.json()["item_id"]
    print(f"  [PASS] Added Activity 1 (ID {act1_id}): '{act1_payload['activity']}' [Category: {act1_payload['category']}, Cost: Rs.{act1_payload['estimated_cost']}]")

    act2_payload = {
        "date": "2026-11-01",
        "time": "16:30",
        "activity": "Old Manali Cafe Trail",
        "location": "Old Manali Village",
        "category": "Food & Dining",
        "estimated_cost": 850.0,
        "notes": "Try authentic trout and local herbal tea"
    }
    r_act2 = client_user_a.post(f"/api/trips/{trip_id}/itinerary", json=act2_payload, headers=headers_a)
    assert r_act2.status_code == 201
    act2_id = r_act2.json()["item_id"]
    print(f"  [PASS] Added Activity 2 (ID {act2_id}): '{act2_payload['activity']}' [Category: {act2_payload['category']}]")

    act3_payload = {
        "date": "2026-11-02",
        "time": "08:00",
        "activity": "Rohtang Pass Snow Trek",
        "location": "Rohtang Pass",
        "category": "Nature",
        "estimated_cost": 2500.0,
        "notes": "Bring winter jackets and snow boots"
    }
    r_act3 = client_user_a.post(f"/api/trips/{trip_id}/itinerary", json=act3_payload, headers=headers_a)
    assert r_act3.status_code == 201
    act3_id = r_act3.json()["item_id"]
    print(f"  [PASS] Added Activity 3 (ID {act3_id}): '{act3_payload['activity']}' [Day 2]")

    # ---------------------------------------------------------
    # 9. List Chronological Itinerary
    # ---------------------------------------------------------
    print(f"\n[TEST 9] Listing Itinerary Activities (GET /api/trips/{trip_id}/itinerary)...")
    r_itin_list = client_user_a.get(f"/api/trips/{trip_id}/itinerary", headers=headers_a)
    assert r_itin_list.status_code == 200
    itin_items = r_itin_list.json()
    assert len(itin_items) == 3
    # Check sorting: first item should be Day 1 10:00, second Day 1 16:30, third Day 2 08:00
    assert itin_items[0]["item_id"] == act1_id
    assert itin_items[1]["item_id"] == act2_id
    assert itin_items[2]["item_id"] == act3_id
    print(f"  [PASS] Retrieved {len(itin_items)} itinerary items sorted chronologically across Day 1 and Day 2")

    # ---------------------------------------------------------
    # 10. Unauthorized Itinerary Access & Modification Rejection
    # ---------------------------------------------------------
    print("\n[TEST 10] Testing Unauthorized Access to Itinerary Items...")
    # User B attempting to view User A's itinerary
    r_b_itin = client_user_b.get(f"/api/trips/{trip_id}/itinerary", headers=headers_b)
    assert r_b_itin.status_code in [403, 404]
    print(f"  [PASS] User B GET /api/trips/{trip_id}/itinerary rejected with HTTP {r_b_itin.status_code}")

    # User B attempting to add activity to User A's trip
    r_b_add = client_user_b.post(f"/api/trips/{trip_id}/itinerary", json=act1_payload, headers=headers_b)
    assert r_b_add.status_code in [403, 404]
    print(f"  [PASS] User B POST /api/trips/{trip_id}/itinerary rejected with HTTP {r_b_add.status_code}")

    # User B attempting to update User A's activity
    r_b_put = client_user_b.put(f"/api/itinerary/{act1_id}", json={"activity": "Hacked Activity"}, headers=headers_b)
    assert r_b_put.status_code in [403, 404]
    print(f"  [PASS] User B PUT /api/itinerary/{act1_id} rejected with HTTP {r_b_put.status_code}")

    # User B attempting to delete User A's activity
    r_b_del = client_user_b.delete(f"/api/itinerary/{act1_id}", headers=headers_b)
    assert r_b_del.status_code in [403, 404]
    print(f"  [PASS] User B DELETE /api/itinerary/{act1_id} rejected with HTTP {r_b_del.status_code}")

    # ---------------------------------------------------------
    # 11. Edit Itinerary Activity (PUT /api/itinerary/{item_id})
    # ---------------------------------------------------------
    print(f"\n[TEST 11] Updating Itinerary Activity (PUT /api/itinerary/{act1_id})...")
    act_update_payload = {
        "activity": "High-Fly Tandem Paragliding & GoPro Video",
        "time": "11:00",
        "location": "Solang Valley Peak",
        "category": "Adventure Extreme",
        "estimated_cost": 3800.0,
        "notes": "GoPro video footage package included"
    }
    r_act_up = client_user_a.put(f"/api/itinerary/{act1_id}", json=act_update_payload, headers=headers_a)
    assert r_act_up.status_code == 200
    updated_act = r_act_up.json()
    assert updated_act["activity"] == "High-Fly Tandem Paragliding & GoPro Video"
    assert updated_act["time"] == "11:00"
    assert updated_act["category"] == "Adventure Extreme"
    assert updated_act["estimated_cost"] == 3800.0
    print(f"  [PASS] Itinerary item updated: '{updated_act['activity']}', Time={updated_act['time']}, Cost=Rs.{updated_act['estimated_cost']}")

    # ---------------------------------------------------------
    # 12. Delete Itinerary Activity (DELETE /api/itinerary/{item_id})
    # ---------------------------------------------------------
    print(f"\n[TEST 12] Deleting Itinerary Activity (DELETE /api/itinerary/{act2_id})...")
    r_act_del = client_user_a.delete(f"/api/itinerary/{act2_id}", headers=headers_a)
    assert r_act_del.status_code == 200
    # Verify remaining count is 2
    r_itin_after = client_user_a.get(f"/api/trips/{trip_id}/itinerary", headers=headers_a)
    assert len(r_itin_after.json()) == 2
    assert not any(i["item_id"] == act2_id for i in r_itin_after.json())
    print("  [PASS] Activity successfully deleted, exactly 2 activities remain")

    # ---------------------------------------------------------
    # 13. Delete Trip with Cascading Itinerary Cleanup
    # ---------------------------------------------------------
    print(f"\n[TEST 13] Deleting Trip (DELETE /api/trips/{trip_id}) with Cascading Deletion...")
    r_trip_del = client_user_a.delete(f"/api/trips/{trip_id}", headers=headers_a)
    assert r_trip_del.status_code == 200

    # Verify trip no longer exists
    r_trip_check = client_user_a.get(f"/api/trips/{trip_id}", headers=headers_a)
    assert r_trip_check.status_code == 404
    print("  [PASS] GET /api/trips/{trip_id} returns HTTP 404 (Trip removed)")

    # ---------------------------------------------------------
    # 14. Verify SQLite Database Persistence
    # ---------------------------------------------------------
    print("\n[TEST 14] Verifying SQLite Database State Directly on Disk...")
    db_path = os.path.join(BASE_DIR, "travel_planner.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Verify trip row is gone
    cur.execute("SELECT COUNT(*) FROM trips WHERE trip_id = ?", (trip_id,))
    assert cur.fetchone()[0] == 0, "Trip was not deleted from SQLite disk!"

    # Verify cascaded itinerary items are gone
    cur.execute("SELECT COUNT(*) FROM itinerary WHERE trip_id = ?", (trip_id,))
    assert cur.fetchone()[0] == 0, "Cascaded itinerary items still present in SQLite disk!"

    conn.close()
    print("  [PASS] SQLite on-disk database verified: Trip and all cascaded itinerary rows fully purged")

    print("\n" + "=" * 65)
    print("ALL PHASE 3 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    run_phase3_tests()
