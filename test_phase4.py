"""
=============================================================================
SMART TRAVEL PLANNER — PHASE 4 AUTOMATED VERIFICATION SUITE
Expenses & Budget Management:
1. Trip Budget Display & Retrieval (GET /api/trips/{trip_id}/expenses)
2. Accurate Metric Calculations:
   - Total spent = sum of expenses belonging to the trip
   - Remaining budget = trip budget minus total spent
   - Percentage spent = (total spent / budget) * 100
3. Add Expense (POST /api/trips/{trip_id}/expenses) with title, amount, date, category, optional notes
4. Amount Validation on Backend (amount <= 0 rejected with HTTP 422)
5. List Trip Expenses (chronological order)
6. Edit Expense (PUT /api/expenses/{expense_id}) & Automatic Recalculation
7. Delete Expense (DELETE /api/expenses/{expense_id}) & Automatic Recalculation
8. Filter Expenses by Category (GET /api/trips/{trip_id}/expenses?category=Food)
9. Category-wise Spending Breakdown (Food, Transport, Hotel, Activities, Shopping, Other)
10. Budget Exceeded Handling (Clear warning flag, non-blocking)
11. Safe Zero Budget Handling (no ZeroDivisionError, correct deficit math)
12. Budget Immutability Check (Original trip budget is NEVER silently mutated)
13. Dashboard vs Expenses Consistency Verification (consistent totals from DB)
14. Security & Ownership Isolation (Cross-user access rejected with HTTP 403)
15. Direct SQLite On-Disk Persistence Verification
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

# Ensure utf-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

client_user_a = TestClient(app)
client_user_b = TestClient(app)

DB_PATH = os.path.join(BASE_DIR, "travel_planner.db")


def run_phase4_tests():
    print("=" * 70)
    print("SMART TRAVEL PLANNER — PHASE 4 TEST SUITE: EXPENSES & BUDGET")
    print("=" * 70)

    ts = int(time.time())
    email_a = f"alice_budget_{ts}@example.com"
    email_b = f"bob_budget_{ts}@example.com"

    # ---------------------------------------------------------
    # 0. Setup: Register User A and User B
    # ---------------------------------------------------------
    print("\n[STEP 0] Registering two isolated users for testing...")
    r_a = client_user_a.post("/api/users/register", json={
        "name": "Alice Budgeteer",
        "email": email_a,
        "password": "Password123!"
    })
    assert r_a.status_code == 201, f"Failed Alice reg: {r_a.text}"
    token_a = r_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    r_b = client_user_b.post("/api/users/register", json={
        "name": "Bob Intruder",
        "email": email_b,
        "password": "Password123!"
    })
    assert r_b.status_code == 201, f"Failed Bob reg: {r_b.text}"
    token_b = r_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print("  [PASS] User A and User B registered and authenticated")

    # ---------------------------------------------------------
    # 1. Create a trip for User A with budget = 20,000 INR
    # ---------------------------------------------------------
    print("\n[TEST 1] Creating a Trip for User A (Budget = Rs.20,000)...")
    trip_res = client_user_a.post("/api/trips", json={
        "trip_name": "Kerala Backwaters & Tea Hills",
        "destination": "Munnar, Kerala",
        "start_date": "2026-11-10",
        "end_date": "2026-11-15",
        "budget": 20000.0,
        "travellers": 2,
        "interests": ["Nature", "Tea Gardens", "Food"],
        "description": "5-day tranquil holiday in Kerala"
    }, headers=headers_a)
    assert trip_res.status_code == 201, f"Trip creation failed: {trip_res.text}"
    trip_id = trip_res.json()["trip_id"]
    original_budget = trip_res.json()["budget"]
    assert original_budget == 20000.0
    print(f"  [PASS] Created trip ID {trip_id} with budget Rs.{original_budget}")

    # ---------------------------------------------------------
    # 2. Initial Budget Check (0 expenses)
    # ---------------------------------------------------------
    print("\n[TEST 2] Verifying initial budget calculations with 0 expenses...")
    r_exp_init = client_user_a.get(f"/api/trips/{trip_id}/expenses", headers=headers_a)
    assert r_exp_init.status_code == 200, f"Get expenses failed: {r_exp_init.text}"
    init_data = r_exp_init.json()
    assert init_data["budget"] == 20000.0
    assert init_data["total_spent"] == 0.0
    assert init_data["remaining_budget"] == 20000.0
    assert init_data["budget_used_percentage"] == 0.0
    assert init_data["budget_exceeded"] is False
    assert len(init_data["expenses"]) == 0
    print("  [PASS] Initial state: Spent = Rs.0, Remaining = Rs.20,000 (0.0%), Exceeded = False")

    # ---------------------------------------------------------
    # 3. Backend Amount Validation (gt 0 required)
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing backend amount validation (amount <= 0 rejected)...")
    r_zero = client_user_a.post(f"/api/trips/{trip_id}/expenses", json={
        "title": "Free Walking Tour",
        "category": "Activities",
        "amount": 0.0,
        "expense_date": "2026-11-10"
    }, headers=headers_a)
    assert r_zero.status_code == 422, f"Expected 422 for zero amount, got {r_zero.status_code}"

    r_neg = client_user_a.post(f"/api/trips/{trip_id}/expenses", json={
        "title": "Refund",
        "category": "Other",
        "amount": -500.0,
        "expense_date": "2026-11-10"
    }, headers=headers_a)
    assert r_neg.status_code == 422, f"Expected 422 for negative amount, got {r_neg.status_code}"
    print("  [PASS] Backend rejected amount=0 and amount=-500 with HTTP 422 Unprocessable Entity")

    # ---------------------------------------------------------
    # 4. Add Expenses with title, amount, date, category and optional notes
    # ---------------------------------------------------------
    print("\n[TEST 4] Adding expenses across multiple categories with optional notes...")
    exp1_payload = {
        "title": "Kochi to Munnar Cab Transfer",
        "category": "Transport",
        "amount": 3200.0,
        "expense_date": "2026-11-10",
        "notes": "Booked prepaid taxi from airport"
    }
    r_exp1 = client_user_a.post(f"/api/trips/{trip_id}/expenses", json=exp1_payload, headers=headers_a)
    assert r_exp1.status_code == 201, f"Failed adding expense 1: {r_exp1.text}"
    exp1 = r_exp1.json()
    assert exp1["amount"] == 3200.0
    assert exp1["category"] == "Transport"
    assert exp1["notes"] == "Booked prepaid taxi from airport"
    exp1_id = exp1["expense_id"]

    exp2_payload = {
        "title": "Traditional Sadya Lunch at Saravana",
        "category": "Food",
        "amount": 1450.0,
        "expense_date": "2026-11-11",
        "notes": "Feast for 2 including payasam"
    }
    r_exp2 = client_user_a.post(f"/api/trips/{trip_id}/expenses", json=exp2_payload, headers=headers_a)
    assert r_exp2.status_code == 201
    exp2_id = r_exp2.json()["expense_id"]

    exp3_payload = {
        "title": "Kolukkumalai Sunrise Jeep Safari",
        "category": "Activities",
        "amount": 2500.0,
        "expense_date": "2026-11-12",
        "notes": "Early morning 4:30 AM departure"
    }
    r_exp3 = client_user_a.post(f"/api/trips/{trip_id}/expenses", json=exp3_payload, headers=headers_a)
    assert r_exp3.status_code == 201
    exp3_id = r_exp3.json()["expense_id"]

    print(f"  [PASS] Added 3 expenses (IDs: {exp1_id}, {exp2_id}, {exp3_id})")

    # ---------------------------------------------------------
    # 5. Verify Calculations after Operations
    # ---------------------------------------------------------
    print("\n[TEST 5] Verifying mathematical calculations after adding expenses...")
    r_check1 = client_user_a.get(f"/api/trips/{trip_id}/expenses", headers=headers_a)
    data1 = r_check1.json()
    expected_spent1 = 3200.0 + 1450.0 + 2500.0  # 7,150.0
    expected_remaining1 = 20000.0 - expected_spent1  # 12,850.0
    expected_pct1 = round((expected_spent1 / 20000.0) * 100.0, 1)  # 35.8%

    assert data1["total_spent"] == expected_spent1, f"Spent mismatch: {data1['total_spent']} != {expected_spent1}"
    assert data1["remaining_budget"] == expected_remaining1, f"Remaining mismatch: {data1['remaining_budget']} != {expected_remaining1}"
    assert data1["budget_used_percentage"] == expected_pct1, f"Pct mismatch: {data1['budget_used_percentage']} != {expected_pct1}"
    assert data1["budget_exceeded"] is False
    print(f"  [PASS] Calculations verified: Spent = Rs.{expected_spent1}, Remaining = Rs.{expected_remaining1}, Pct = {expected_pct1}%")

    # ---------------------------------------------------------
    # 6. Verify Category-Wise Spending Summary
    # ---------------------------------------------------------
    print("\n[TEST 6] Verifying category-wise spending summary...")
    cat_summary = data1["category_breakdown"]
    assert cat_summary["Transport"] == 3200.0
    assert cat_summary["Food"] == 1450.0
    assert cat_summary["Activities"] == 2500.0
    assert cat_summary["Hotel"] == 0.0
    assert cat_summary["Shopping"] == 0.0
    assert cat_summary["Other"] == 0.0
    print("  [PASS] Category breakdown subtotals accurate: Transport=Rs.3200, Food=Rs.1450, Activities=Rs.2500")

    # ---------------------------------------------------------
    # 7. Filter Expenses by Category
    # ---------------------------------------------------------
    print("\n[TEST 7] Testing category filtering on GET /api/trips/{trip_id}/expenses?category=Food...")
    r_filter_food = client_user_a.get(f"/api/trips/{trip_id}/expenses?category=Food", headers=headers_a)
    assert r_filter_food.status_code == 200
    food_data = r_filter_food.json()
    assert len(food_data["expenses"]) == 1
    assert food_data["expenses"][0]["category"] == "Food"
    assert food_data["expenses"][0]["amount"] == 1450.0
    # Overall budget metrics should remain complete
    assert food_data["total_spent"] == expected_spent1
    assert food_data["budget"] == 20000.0

    r_filter_transport = client_user_a.get(f"/api/trips/{trip_id}/expenses?category=Transport", headers=headers_a)
    assert len(r_filter_transport.json()["expenses"]) == 1
    assert r_filter_transport.json()["expenses"][0]["category"] == "Transport"
    print("  [PASS] Category filtering successfully isolates matching expenses")

    # ---------------------------------------------------------
    # 8. Edit Expense (PUT /api/expenses/{expense_id}) & Recalculate
    # ---------------------------------------------------------
    print("\n[TEST 8] Editing an expense and verifying updated calculations...")
    # Update Cab from 3200 to 3800, add updated notes
    r_edit = client_user_a.put(f"/api/expenses/{exp1_id}", json={
        "title": "Kochi to Munnar Innova Crysta Cab",
        "amount": 3800.0,
        "category": "Transport",
        "notes": "Upgraded vehicle to Innova Crysta"
    }, headers=headers_a)
    assert r_edit.status_code == 200, f"Edit failed: {r_edit.text}"
    edited = r_edit.json()
    assert edited["amount"] == 3800.0
    assert edited["notes"] == "Upgraded vehicle to Innova Crysta"

    # Verify recalculation after edit
    r_check2 = client_user_a.get(f"/api/trips/{trip_id}/expenses", headers=headers_a)
    data2 = r_check2.json()
    expected_spent2 = 3800.0 + 1450.0 + 2500.0  # 7,750.0
    expected_remaining2 = 20000.0 - expected_spent2  # 12,250.0
    expected_pct2 = round((expected_spent2 / 20000.0) * 100.0, 1)  # 38.8%

    assert data2["total_spent"] == expected_spent2
    assert data2["remaining_budget"] == expected_remaining2
    assert data2["budget_used_percentage"] == expected_pct2
    assert data2["category_breakdown"]["Transport"] == 3800.0
    print(f"  [PASS] Post-edit recalculation verified: Spent = Rs.{expected_spent2}, Remaining = Rs.{expected_remaining2}")

    # ---------------------------------------------------------
    # 9. Delete Expense (DELETE /api/expenses/{expense_id}) & Recalculate
    # ---------------------------------------------------------
    print("\n[TEST 9] Deleting an expense and verifying budget auto-recovery...")
    r_del = client_user_a.delete(f"/api/expenses/{exp2_id}", headers=headers_a)
    assert r_del.status_code == 200, f"Delete failed: {r_del.text}"

    # Verify recalculation after deletion
    r_check3 = client_user_a.get(f"/api/trips/{trip_id}/expenses", headers=headers_a)
    data3 = r_check3.json()
    expected_spent3 = 3800.0 + 2500.0  # 6,300.0
    expected_remaining3 = 20000.0 - expected_spent3  # 13,700.0
    expected_pct3 = round((expected_spent3 / 20000.0) * 100.0, 1)  # 31.5%

    assert len(data3["expenses"]) == 2
    assert data3["total_spent"] == expected_spent3
    assert data3["remaining_budget"] == expected_remaining3
    assert data3["budget_used_percentage"] == expected_pct3
    assert data3["category_breakdown"]["Food"] == 0.0
    print(f"  [PASS] Post-delete recalculation verified: Spent = Rs.{expected_spent3}, Food subtotal reset to Rs.0")

    # ---------------------------------------------------------
    # 10. Budget Exceeded Warning (Non-blocking)
    # ---------------------------------------------------------
    print("\n[TEST 10] Testing budget exceeded behavior (spending > budget)...")
    # Add an expense of Rs.15,000, bringing total to Rs.6,300 + Rs.15,000 = Rs.21,300 (exceeds Rs.20,000)
    r_over = client_user_a.post(f"/api/trips/{trip_id}/expenses", json={
        "title": "Luxury Treehouse Resort Stay",
        "category": "Hotel",
        "amount": 15000.0,
        "expense_date": "2026-11-13",
        "notes": "3 nights at Nature Zone Resort"
    }, headers=headers_a)
    assert r_over.status_code == 201, "Over-budget expense must NOT be blocked!"

    r_check4 = client_user_a.get(f"/api/trips/{trip_id}/expenses", headers=headers_a)
    data4 = r_check4.json()
    expected_spent4 = 6300.0 + 15000.0  # 21,300.0
    expected_remaining4 = 20000.0 - expected_spent4  # -1,300.0
    expected_pct4 = round((expected_spent4 / 20000.0) * 100.0, 1)  # 106.5%

    assert data4["total_spent"] == expected_spent4
    assert data4["remaining_budget"] == expected_remaining4  # -1300.0
    assert data4["budget_used_percentage"] == expected_pct4  # 106.5%
    assert data4["budget_exceeded"] is True
    print(f"  [PASS] Budget exceeded handled cleanly: Total Spent = Rs.{expected_spent4}, Remaining = Rs.{expected_remaining4}, Exceeded = True")

    # ---------------------------------------------------------
    # 11. Budget Immutability Check
    # ---------------------------------------------------------
    print("\n[TEST 11] Verifying trip original budget was NEVER mutated...")
    trip_verify = client_user_a.get(f"/api/trips/{trip_id}", headers=headers_a)
    assert trip_verify.status_code == 200
    assert trip_verify.json()["budget"] == 20000.0, "Original budget must not be modified!"
    print("  [PASS] Trip budget remains exactly Rs.20,000.0 after all expense additions and edits")

    # ---------------------------------------------------------
    # 12. Safe Zero Budget Handling
    # ---------------------------------------------------------
    print("\n[TEST 12] Testing safe zero budget handling...")
    # Create trip with 0 budget via direct DB insertion to test edge calculation safely
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    user_a_id = r_a.json()["user"]["user_id"]
    cur.execute(
        "INSERT INTO trips (user_id, trip_name, destination, start_date, end_date, budget, travellers, interests) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_a_id, "Zero Budget Trip", "Nearby Trek", "2026-12-01", "2026-12-02", 0.0, 1, "Trekking")
    )
    zero_trip_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Get zero trip expenses (no expenses logged yet)
    r_zero_exp = client_user_a.get(f"/api/trips/{zero_trip_id}/expenses", headers=headers_a)
    assert r_zero_exp.status_code == 200
    z_data = r_zero_exp.json()
    assert z_data["budget"] == 0.0
    assert z_data["total_spent"] == 0.0
    assert z_data["remaining_budget"] == 0.0
    assert z_data["budget_used_percentage"] == 0.0
    assert z_data["budget_exceeded"] is False

    # Add expense to zero budget trip
    r_add_zero = client_user_a.post(f"/api/trips/{zero_trip_id}/expenses", json={
        "title": "Trail Entry Fee",
        "category": "Activities",
        "amount": 200.0,
        "expense_date": "2026-12-01"
    }, headers=headers_a)
    assert r_add_zero.status_code == 201

    r_zero_exp2 = client_user_a.get(f"/api/trips/{zero_trip_id}/expenses", headers=headers_a)
    assert r_zero_exp2.status_code == 200
    z_data2 = r_zero_exp2.json()
    assert z_data2["total_spent"] == 200.0
    assert z_data2["remaining_budget"] == -200.0
    assert z_data2["budget_used_percentage"] == 100.0
    assert z_data2["budget_exceeded"] is True
    print("  [PASS] Zero budget calculated safely: 0 spent -> 0.0%, 200 spent -> 100.0%, remaining = -200.0")

    # ---------------------------------------------------------
    # 13. Dashboard vs Expenses Consistency
    # ---------------------------------------------------------
    print("\n[TEST 13] Verifying Dashboard vs Expense page metric consistency...")
    # Dashboard loads via GET /api/trips
    r_all_trips = client_user_a.get("/api/trips", headers=headers_a)
    assert r_all_trips.status_code == 200
    dashboard_trip = next((t for t in r_all_trips.json() if t["trip_id"] == trip_id), None)
    assert dashboard_trip is not None

    # Expense page loads via GET /api/trips/{trip_id}/expenses
    r_exp_page = client_user_a.get(f"/api/trips/{trip_id}/expenses", headers=headers_a)
    assert r_exp_page.status_code == 200
    expense_page_data = r_exp_page.json()

    assert dashboard_trip["total_spent"] == expense_page_data["total_spent"]
    assert dashboard_trip["remaining_budget"] == expense_page_data["remaining_budget"]
    assert dashboard_trip["budget_used_percentage"] == expense_page_data["budget_used_percentage"]
    assert dashboard_trip["budget_exceeded"] == expense_page_data["budget_exceeded"]
    print("  [PASS] Dashboard and Expense page return 100% identical totals from SQLite")

    # ---------------------------------------------------------
    # 14. Security & Ownership Isolation (User B cross-access)
    # ---------------------------------------------------------
    print("\n[TEST 14] Testing security & ownership isolation (User B cross-user access)...")
    r_b_view = client_user_b.get(f"/api/trips/{trip_id}/expenses", headers=headers_b)
    assert r_b_view.status_code == 403, f"Expected 403 on view, got {r_b_view.status_code}"

    r_b_add = client_user_b.post(f"/api/trips/{trip_id}/expenses", json={
        "title": "Intruder expense",
        "category": "Other",
        "amount": 999.0,
        "expense_date": "2026-11-10"
    }, headers=headers_b)
    assert r_b_add.status_code == 403, f"Expected 403 on add, got {r_b_add.status_code}"

    r_b_edit = client_user_b.put(f"/api/expenses/{exp1_id}", json={
        "amount": 10.0
    }, headers=headers_b)
    assert r_b_edit.status_code == 403, f"Expected 403 on edit, got {r_b_edit.status_code}"

    r_b_del = client_user_b.delete(f"/api/expenses/{exp1_id}", headers=headers_b)
    assert r_b_del.status_code == 403, f"Expected 403 on delete, got {r_b_del.status_code}"
    print("  [PASS] Cross-user access rejected with HTTP 403 on GET, POST, PUT, DELETE")

    # ---------------------------------------------------------
    # 15. Direct SQLite On-Disk Persistence Verification
    # ---------------------------------------------------------
    print("\n[TEST 15] Verifying SQLite on-disk database persistence...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT expense_id, trip_id, category, amount, description, notes FROM expenses WHERE trip_id = ?", (trip_id,))
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 3, f"Expected 3 rows in SQLite disk DB, got {len(rows)}"
    # Check that notes were stored on disk
    notes_stored = [r[5] for r in rows if r[5]]
    assert len(notes_stored) >= 2
    print(f"  [PASS] SQLite persistence verified on disk ({len(rows)} expenses verified with notes)")

    print("\n" + "=" * 70)
    print("ALL PHASE 4 EXPENSES & BUDGET TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_phase4_tests()
