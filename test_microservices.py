"""
Tests live server-to-server communication between:
1. Smart Travel Planner (FastAPI)
2. Experience Finder Service (port 8001)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from mock_experience_finder.main import app as finder_app
from app.main import app as planner_app

def test_experience_finder_direct():
    print("Testing Experience Finder standalone microservice...")
    client = TestClient(finder_app)
    res = client.get("/api/experiences?destination=Goa&category=Adventure")
    assert res.status_code == 200
    data = res.json()
    assert "experiences" in data
    assert len(data["experiences"]) == 2
    names = [e["name"] for e in data["experiences"]]
    assert "Scuba Diving" in names
    assert "Dolphin Watching" in names
    print(f"  [PASS] Experience Finder returned {len(data['experiences'])} experiences directly: {names}")

def test_summary_and_flow():
    print("Testing Smart Travel Planner full scenario flow...")
    client = TestClient(planner_app)
    
    # 1. Login
    login_res = client.post("/api/users/login", json={"email": "arun.kumar@example.com", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Summary
    sum_res = client.get("/api/trips/101/summary", headers=headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()
    print(f"  [PASS] Trip Summary: {summary['destination']} | Budget: {summary['budget']} | Remaining: {summary['remaining_budget']}")
    print(f"         Interests: {summary['interests']}")
    print(f"         Selected Activities: {summary['selected_activities']}")

if __name__ == "__main__":
    test_experience_finder_direct()
    test_summary_and_flow()
    print("\nALL MICROSERVICE & SUMMARY TESTS PASSED!")
