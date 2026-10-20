"""
=============================================================================
SMART TRAVEL PLANNER — PHASE 1 AUTOMATED VERIFICATION SUITE
Tests:
1. Health-check endpoint (GET /api/health & GET /health)
2. User Registration (POST /api/users/register)
3. Duplicate Registration rejection (HTTP 400 with readable error)
4. Valid Login (POST /api/users/login -> HTTP 200 & JWT Token)
5. Invalid Login rejection (wrong password -> HTTP 401)
6. Invalid Login rejection (unknown email -> HTTP 401)
7. Protected endpoint access (GET /api/users/me) & 401 rejection without token
8. SQLite Database Persistence & Bcrypt Hash Verification (No plaintext password)
=============================================================================
"""

import os
import sys
import sqlite3
import bcrypt
from datetime import datetime
from fastapi.testclient import TestClient

# Ensure workspace is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.main import app
from app.database import SessionLocal
from app.models import User

client = TestClient(app)

def run_phase1_tests():
    print("=" * 60)
    print("SMART TRAVEL PLANNER — PHASE 1 TEST SUITE")
    print("=" * 60)

    # ---------------------------------------------------------
    # 1. Health-check Endpoint
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing Health-check Endpoints (/api/health and /health)...")
    r1 = client.get("/api/health")
    assert r1.status_code == 200, f"Expected 200 on /api/health, got {r1.status_code}: {r1.text}"
    data1 = r1.json()
    assert data1.get("status") == "ok", f"Expected status 'ok', got {data1}"
    print(f"  [PASS] GET /api/health returned HTTP 200: {data1}")

    r2 = client.get("/health")
    assert r2.status_code == 200, f"Expected 200 on /health, got {r2.status_code}"
    print("  [PASS] GET /health returned HTTP 200")

    # ---------------------------------------------------------
    # 2. User Registration
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing User Registration (POST /api/users/register)...")
    test_email = f"explorer_{int(datetime.now().timestamp())}@example.com"
    test_name = "Priya Sharma"
    test_password = "PriyaSecretPassword123!"

    reg_payload = {
        "name": test_name,
        "email": test_email,
        "password": test_password
    }

    r_reg = client.post("/api/users/register", json=reg_payload)
    assert r_reg.status_code == 201, f"Expected 201 Created, got {r_reg.status_code}: {r_reg.text}"
    reg_data = r_reg.json()
    assert "access_token" in reg_data, "Response missing access_token"
    assert reg_data["user"]["email"] == test_email.lower(), "User email mismatch"
    assert reg_data["user"]["name"] == test_name, "User name mismatch"
    user_id = reg_data["user"]["user_id"]
    token = reg_data["access_token"]
    print(f"  [PASS] User successfully registered: ID {user_id}, Name '{test_name}', Email '{test_email}'")
    print(f"  [PASS] Received valid JWT Bearer access token: {token[:25]}...")

    # ---------------------------------------------------------
    # 3. Duplicate Registration
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing Duplicate Registration Prevention...")
    r_dup = client.post("/api/users/register", json=reg_payload)
    assert r_dup.status_code == 400, f"Expected 400 Bad Request for duplicate, got {r_dup.status_code}"
    dup_err = r_dup.json()
    assert "already exists" in dup_err.get("detail", "").lower(), f"Unexpected error message: {dup_err}"
    print(f"  [PASS] Duplicate registration rejected with HTTP 400: '{dup_err['detail']}'")

    # ---------------------------------------------------------
    # 4. Valid Login
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing Valid Login (POST /api/users/login)...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    r_login = client.post("/api/users/login", json=login_payload)
    assert r_login.status_code == 200, f"Expected 200 OK, got {r_login.status_code}: {r_login.text}"
    login_data = r_login.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == test_email.lower()
    login_token = login_data["access_token"]
    print(f"  [PASS] Valid login succeeded for {test_email}")
    print(f"  [PASS] Received JWT token: {login_token[:25]}...")

    # ---------------------------------------------------------
    # 5. Invalid Login: Wrong Password
    # ---------------------------------------------------------
    print("\n[TEST 5] Testing Invalid Login (Wrong Password)...")
    bad_pass_payload = {
        "email": test_email,
        "password": "WrongPassword999!"
    }
    r_bad_pass = client.post("/api/users/login", json=bad_pass_payload)
    assert r_bad_pass.status_code == 401, f"Expected 401 Unauthorized, got {r_bad_pass.status_code}"
    bad_pass_err = r_bad_pass.json()
    assert "invalid" in bad_pass_err.get("detail", "").lower(), f"Unexpected detail: {bad_pass_err}"
    print(f"  [PASS] Wrong password rejected with HTTP 401: '{bad_pass_err['detail']}'")

    # ---------------------------------------------------------
    # 6. Invalid Login: Non-existent Email
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing Invalid Login (Non-existent Email)...")
    bad_email_payload = {
        "email": "nonexistent.user.999@randomdomain.xyz",
        "password": "AnyPassword123!"
    }
    r_bad_email = client.post("/api/users/login", json=bad_email_payload)
    assert r_bad_email.status_code == 401, f"Expected 401 Unauthorized, got {r_bad_email.status_code}"
    print("  [PASS] Non-existent email rejected with HTTP 401")

    # ---------------------------------------------------------
    # 7. Protected Endpoint & Token Authentication
    # ---------------------------------------------------------
    print("\n[TEST 7] Testing Protected Endpoint (GET /api/users/me)...")
    # Clear session cookies to simulate fresh unauthenticated client
    client.cookies.clear()
    r_unauth = client.get("/api/users/me")
    assert r_unauth.status_code == 401, f"Expected 401 without token, got {r_unauth.status_code}"
    print("  [PASS] Unauthenticated request to /api/users/me correctly rejected with HTTP 401")

    # Authenticated request with Bearer token
    headers = {"Authorization": f"Bearer {login_token}"}
    r_auth = client.get("/api/users/me", headers=headers)
    assert r_auth.status_code == 200, f"Expected 200 with valid token, got {r_auth.status_code}"
    auth_profile = r_auth.json()
    assert auth_profile["user_id"] == user_id
    assert auth_profile["email"] == test_email.lower()
    assert auth_profile["name"] == test_name
    print(f"  [PASS] Authenticated request to /api/users/me succeeded: {auth_profile['name']} ({auth_profile['email']})")

    # ---------------------------------------------------------
    # 8. SQLite Database Persistence & Bcrypt Hash Verification
    # ---------------------------------------------------------
    print("\n[TEST 8] Testing SQLite Database Persistence & Bcrypt Security...")
    db_path = os.path.join(BASE_DIR, "travel_planner.db")
    assert os.path.exists(db_path), f"SQLite database file does not exist at {db_path}"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, email, password_hash FROM users WHERE email = ?", (test_email.lower(),))
    row = cursor.fetchone()
    conn.close()

    assert row is not None, f"User {test_email} was not found in SQLite database on disk!"
    db_user_id, db_name, db_email, db_hash = row
    assert db_user_id == user_id
    assert db_name == test_name
    assert db_email == test_email.lower()
    
    # Verify password is NOT stored as plaintext
    assert db_hash != test_password, "SECURITY VIOLATION: Plaintext password found in database!"
    assert db_hash.startswith("$2b$") or db_hash.startswith("$2a$"), f"Expected bcrypt hash, got: {db_hash[:10]}..."

    # Verify bcrypt verification function against stored hash
    is_valid = bcrypt.checkpw(test_password.encode("utf-8"), db_hash.encode("utf-8"))
    assert is_valid, "Bcrypt verification failed against stored hash"
    print(f"  [PASS] Stored in SQLite 'travel_planner.db': User ID {db_user_id}")
    print(f"  [PASS] Stored password hash: {db_hash[:30]}... (Bcrypt salted)")
    print("  [PASS] Plaintext password is NEVER stored on disk")
    print("  [PASS] Bcrypt verification succeeded against on-disk SQLite record")

    # ---------------------------------------------------------
    # 9. HTML Template Pages Rendering Check
    # ---------------------------------------------------------
    print("\n[TEST 9] Testing Phase 1 Public HTML Template Pages...")
    for path, expected_text in [
        ("/", "Smart Travel Planner"),
        ("/login", "Sign In"),
        ("/register", "Start Planning Today")
    ]:
        res = client.get(path)
        assert res.status_code == 200, f"Expected 200 on {path}, got {res.status_code}"
        assert expected_text in res.text, f"Expected '{expected_text}' in {path}"
        print(f"  [PASS] GET {path} served HTTP 200 with expected content")

    print("\n" + "=" * 60)
    print("ALL PHASE 1 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_phase1_tests()
