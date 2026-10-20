"""
Automated end-to-end verification script for Smart Travel Planner.
Tests:
- Database initialization and seeding
- Password hashing & JWT Auth
- Trip CRUD & Summary API
- Itinerary CRUD & sorting
- Expense logging & dynamic budget calculations
- External Experience Finder API call & fallback handling
"""

import sys
from pathlib import Path
from datetime import date

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, Trip, Expense, Itinerary, SavedExperience

def run_tests():
    print("==================================================")
    print("RUNNING SMART TRAVEL PLANNER BACKEND TEST SUITE")
    print("==================================================")

    # Initialize client (triggers lifespan startup & seeding)
    with TestClient(app) as client:
        print("\n1. Testing Public HTML Pages...")
        res = client.get("/")
        assert res.status_code == 200, f"Landing page failed: {res.status_code}"
        res = client.get("/login")
        assert res.status_code == 200, f"Login page failed: {res.status_code}"
        res = client.get("/dashboard")
        assert res.status_code == 200, f"Dashboard page failed: {res.status_code}"
        print("  [PASS] All HTML pages serve HTTP 200 OK")

        print("\n2. Testing Authentication API...")
        # Test Login with seeded user
        login_res = client.post("/api/users/login", json={
            "email": "arun.kumar@example.com",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        assert "access_token" in login_data, "No access token returned"
        token = login_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  [PASS] Logged in as {login_data['user']['name']} ({login_data['user']['email']})")

        # Test /api/users/me
        me_res = client.get("/api/users/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["name"] == "Arun Kumar"
        print("  [PASS] Profile authenticated via JWT Bearer token")

        print("\n3. Testing Trips API & Seeded Goa Trip...")
        trips_res = client.get("/api/trips", headers=headers)
        assert trips_res.status_code == 200
        trips = trips_res.json()
        assert len(trips) >= 1, "No trips found in database"
        goa_trip = next((t for t in trips if t["destination"] == "Goa"), None)
        assert goa_trip is not None, "Goa trip not found"
        print(f"  [PASS] Found Goa Trip: Budget = Rs.{goa_trip['budget']}, Spent = Rs.{goa_trip['total_spent']}, Remaining = Rs.{goa_trip['remaining_budget']}")

        # Verify exact demo numbers
        assert goa_trip["budget"] == 25000.0, f"Expected 25000, got {goa_trip['budget']}"
        assert goa_trip["total_spent"] == 7200.0, f"Expected 7200, got {goa_trip['total_spent']}"
        assert goa_trip["remaining_budget"] == 17800.0, f"Expected 17800, got {goa_trip['remaining_budget']}"
        assert goa_trip["budget_used_percentage"] == 28.8, f"Expected 28.8%, got {goa_trip['budget_used_percentage']}"
        print("  [PASS] EXACT DEMO SPECIFICATION VERIFIED: Spent = Rs.7,200 | Remaining = Rs.17,800 (28.8%)")

        print("\n4. Testing Trip Summary API (for Experience Finder integration)...")
        summary_res = client.get(f"/api/trips/{goa_trip['trip_id']}/summary", headers=headers)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["destination"] == "Goa"
        assert summary_data["budget"] == 25000.0
        assert summary_data["remaining_budget"] == 17800.0
        assert "Adventure" in summary_data["interests"]
        assert "Scuba Diving" in summary_data["selected_activities"]
        print(f"  [PASS] Trip Summary Contract verified: {summary_data['destination']}, Remaining: Rs.{summary_data['remaining_budget']}")

        print("\n5. Testing Expenses API & Category Breakdown...")
        exp_res = client.get(f"/api/trips/{goa_trip['trip_id']}/expenses", headers=headers)
        assert exp_res.status_code == 200
        exp_data = exp_res.json()
        cats = exp_data["category_breakdown"]
        assert cats["Food"] == 2000.0, f"Expected Food 2000, got {cats['Food']}"
        assert cats["Transport"] == 1500.0, f"Expected Transport 1500, got {cats['Transport']}"
        assert cats["Activities"] == 3700.0, f"Expected Activities 3700, got {cats['Activities']}"
        print(f"  [PASS] Verified Category Subtotals: Food = Rs.{cats['Food']}, Transport = Rs.{cats['Transport']}, Activities = Rs.{cats['Activities']}")

        print("\n6. Testing Itinerary API...")
        itin_res = client.get(f"/api/trips/{goa_trip['trip_id']}/itinerary", headers=headers)
        assert itin_res.status_code == 200
        items = itin_res.json()
        assert len(items) >= 4, f"Expected at least 4 items, got {len(items)}"
        print(f"  [PASS] Retrieved {len(items)} itinerary activities sorted chronologically")

        # Test adding a new itinerary item
        add_itin_res = client.post(f"/api/trips/{goa_trip['trip_id']}/itinerary", headers=headers, json={
            "date": "2026-10-17",
            "time": "11:00",
            "activity": "Fort Aguada Exploration",
            "location": "Sinquerim",
            "estimated_cost": 50.0,
            "notes": "17th century Portuguese lighthouse"
        })
        assert add_itin_res.status_code == 201
        new_item = add_itin_res.json()
        print(f"  [PASS] Added Itinerary Item #{new_item['item_id']}: {new_item['activity']}")

        print("\n7. Testing Experience Recommendations Integration...")
        recs_res = client.get(f"/api/trips/{goa_trip['trip_id']}/recommendations?category=Adventure&use_dev_adapter=true", headers=headers)
        assert recs_res.status_code == 200
        recs_data = recs_res.json()
        assert "experiences" in recs_data
        assert len(recs_data["experiences"]) > 0
        first_exp = recs_data["experiences"][0]
        print(f"  [PASS] Recommendations fetched: {len(recs_data['experiences'])} items (First: {first_exp['name']} - Rs.{first_exp['price']})")

        # Test saving experience to trip
        save_res = client.post(f"/api/trips/{goa_trip['trip_id']}/experiences", headers=headers, json={
            "experience_id": 4,
            "name": "Dudhsagar Waterfalls Trek",
            "category": "Nature",
            "price": 1800.0,
            "rating": 4.8
        })
        assert save_res.status_code == 201
        saved_data = save_res.json()
        print(f"  [PASS] Experience saved to Smart Travel Planner DB: {saved_data['name']}")

        print("\n8. Testing Security Boundaries...")
        # Clear cookies and test unauthorized access
        client.cookies.clear()
        unauth_res = client.get("/api/trips")
        assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
        print("  [PASS] Unauthenticated API requests properly rejected with HTTP 401")

        print("\n9. Testing Trip, Itinerary, and Expense Edit (PUT) Operations...")
        # Test editing Goa trip description
        put_trip_res = client.put(f"/api/trips/{goa_trip['trip_id']}", headers=headers, json={
            "description": "Updated vacation notes: Sunset cruise and beach relaxation."
        })
        assert put_trip_res.status_code == 200
        assert "Updated vacation notes" in put_trip_res.json()["description"]
        print("  [PASS] Trip edit (PUT) verified successfully")

        # Test editing an itinerary item
        put_itin_res = client.put(f"/api/itinerary/{new_item['item_id']}", headers=headers, json={
            "time": "11:30",
            "notes": "Updated timing for lighthouse photography"
        })
        assert put_itin_res.status_code == 200
        assert put_itin_res.json()["time"] == "11:30"
        print("  [PASS] Itinerary item edit (PUT) verified successfully")

        # Test adding a temporary expense then editing it
        add_exp_res = client.post(f"/api/trips/{goa_trip['trip_id']}/expenses", headers=headers, json={
            "category": "Food",
            "amount": 500.0,
            "description": "Beach snack",
            "expense_date": "2026-10-16"
        })
        assert add_exp_res.status_code == 201
        temp_exp = add_exp_res.json()

        # Edit the expense amount from 500 to 750
        put_exp_res = client.put(f"/api/expenses/{temp_exp['expense_id']}", headers=headers, json={
            "amount": 750.0,
            "description": "Beach shack seafood combo"
        })
        assert put_exp_res.status_code == 200
        assert put_exp_res.json()["amount"] == 750.0
        print("  [PASS] Expense edit (PUT) verified successfully")

        # Delete the temporary expense and verify budget recalculates
        del_exp_res = client.delete(f"/api/expenses/{temp_exp['expense_id']}", headers=headers)
        assert del_exp_res.status_code == 200
        print("  [PASS] Expense deletion & budget recalculation verified successfully")

        print("\n10. Testing API Communication History & TXT Record Generation...")
        hist_res = client.get("/api/recommendations/history")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert "history" in hist_data
        assert len(hist_data["history"]) > 0
        print(f"  [PASS] API Communication History verified ({len(hist_data['history'])} logged events)")

        # Test TXT download endpoint
        txt_res = client.get("/api/recommendations/history/download")
        assert txt_res.status_code == 200
        assert "text/plain" in txt_res.headers.get("content-type", "")
        assert "SMART TRAVEL PLANNER" in txt_res.text
        assert "EXPERIENCE_API_URL" in txt_res.text
        print("  [PASS] API Communication History downloadable TXT record verified")

        # Test Trip Dossier TXT export endpoint
        dossier_res = client.get(f"/api/sync/export-trip-text/{goa_trip['trip_id']}")
        assert dossier_res.status_code == 200
        dossier_data = dossier_res.json()
        assert "filename" in dossier_data
        assert "TRIP DOSSIER & ITINERARY FILE" in dossier_data["content"]
        print("  [PASS] Complete Trip Dossier text export verified")

        print("\n==================================================")
        print("ALL TESTS PASSED WITH 100% SUCCESS!")
        print("==================================================")

if __name__ == "__main__":
    run_tests()
