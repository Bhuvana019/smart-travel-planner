import sys
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_sidebar_and_trip_sync():
    print("=" * 70)
    print("VERIFYING SIDEBAR MODULES & ACTIVE TRIP ALIGNMENT")
    print("=" * 70)

    # 1. Check server health
    res = requests.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200, f"Planner health failed: {res.status_code}"
    print("[PASS] Planner server is healthy on :8000")

    # 2. Test Login
    login_payload = {"email": "arun.kumar@example.com", "password": "password123"}
    res = requests.post(f"{BASE_URL}/api/users/login", json=login_payload)
    assert res.status_code == 200, f"Login failed: {res.text}"
    token = res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authenticated user Arun Kumar successfully")

    # 3. Create a new trip (e.g. Ooty)
    trip_payload = {
        "trip_name": "Ooty Hills Retreat",
        "destination": "Ooty",
        "start_date": "2026-11-10",
        "end_date": "2026-11-15",
        "budget": 35000,
        "travellers": 3,
        "description": "Scenic hill station with tea estates and lake boat rides"
    }
    res = requests.post(f"{BASE_URL}/api/trips", json=trip_payload, headers=headers)
    assert res.status_code == 201, f"Failed to create trip: {res.text}"
    new_trip = res.json()
    trip_id = new_trip["trip_id"]
    print(f"[PASS] Successfully created trip #{trip_id} for {new_trip['destination']}")
    assert new_trip["destination"] == "Ooty"
    assert new_trip["budget"] == 35000
    assert new_trip["travellers"] == 3
    assert new_trip["trip_name"] == "Ooty Hills Retreat"

    # 4. Fetch trip details directly
    res = requests.get(f"{BASE_URL}/api/trips/{trip_id}", headers=headers)
    assert res.status_code == 200, f"Failed to fetch trip details: {res.text}"
    trip_data = res.json()
    assert trip_data["trip_id"] == trip_id
    assert trip_data["destination"] == "Ooty"
    print(f"[PASS] Direct GET /api/trips/{trip_id} returned active trip metadata")

    # 5. Verify static JS files contain required dynamic sidebar logic
    main_js_res = requests.get(f"{BASE_URL}/static/js/main.js")
    assert main_js_res.status_code == 200
    main_js_text = main_js_res.text
    assert "sidebar-active-trip-card" in main_js_text
    assert "updateActiveTripNavigation" in main_js_text
    assert "setActiveTrip" in main_js_text
    assert "Overview" in main_js_text
    assert "Itinerary" in main_js_text
    assert "Expenses" in main_js_text
    assert "Recommendations" in main_js_text
    print("[PASS] main.js contains dynamic sidebar widget and module re-labeling logic")

    trips_js_res = requests.get(f"{BASE_URL}/static/js/trips.js")
    assert trips_js_res.status_code == 200
    trips_js_text = trips_js_res.text
    assert "setActiveTrip(newTrip.trip_id, newTrip.destination, newTrip)" in trips_js_text
    assert "setActiveTrip(trip.trip_id, trip.destination, trip)" in trips_js_text
    print("[PASS] trips.js synchronizes full metadata to setActiveTrip upon creation and viewing")

    itinerary_js_res = requests.get(f"{BASE_URL}/static/js/itinerary.js")
    assert itinerary_js_res.status_code == 200
    itinerary_js_text = itinerary_js_res.text
    assert "setActiveTrip(trip.trip_id, trip.destination, trip)" in itinerary_js_text
    print("[PASS] itinerary.js synchronizes full metadata to setActiveTrip")

    expenses_js_res = requests.get(f"{BASE_URL}/static/js/expenses.js")
    assert expenses_js_res.status_code == 200
    expenses_js_text = expenses_js_res.text
    assert "setActiveTrip(data.trip_id || currentTripId, data.destination, data)" in expenses_js_text
    print("[PASS] expenses.js synchronizes full metadata to setActiveTrip")

    recommendations_js_res = requests.get(f"{BASE_URL}/static/js/recommendations.js")
    assert recommendations_js_res.status_code == 200
    recommendations_js_text = recommendations_js_res.text
    assert "setActiveTrip(currentTrip.trip_id, currentTrip.destination, currentTrip)" in recommendations_js_text
    print("[PASS] recommendations.js synchronizes full metadata to setActiveTrip")

    # 6. Verify HTML pages are served correctly
    for page in ["dashboard.html", "trip.html", "itinerary.html", "expenses.html", "recommendations.html"]:
        p_res = requests.get(f"{BASE_URL}/{page}")
        assert p_res.status_code == 200, f"Page {page} failed to load"
        assert "app-sidebar" in p_res.text
        assert "Active Trip" in p_res.text
        print(f"[PASS] Template {page} serves app-sidebar and Active Trip section")

    print("=" * 70)
    print("ALL SIDEBAR AND ACTIVE TRIP ALIGNMENT CHECKS PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    test_sidebar_and_trip_sync()
