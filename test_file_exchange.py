"""
Test suite for Bidirectional Text File Upload, Download, and Inter-service Transfer
between Smart Travel Planner (:8000) and Experience Finder (:8001).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app as planner_app
from mock_experience_finder.main import app as finder_app

planner_client = TestClient(planner_app)
finder_client = TestClient(finder_app)

def test_peer_health():
    print("\n--- 1. Testing Health Endpoints ---")
    resp_planner = planner_client.get("/health")
    assert resp_planner.status_code == 200
    assert resp_planner.json()["status"] == "ok"
    print("  [PASS] Smart Travel Planner /health is OK")

    resp_finder = finder_client.get("/health")
    assert resp_finder.status_code == 200
    assert resp_finder.json()["status"] == "ok"
    print("  [PASS] Experience Finder /health is OK")


def test_export_trip_text():
    print("\n--- 2. Testing Trip Dossier Text Export ---")
    resp = planner_client.get("/api/sync/export-trip-text/101")
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    text = data["content"]
    assert "SMART TRAVEL PLANNER - TRIP DOSSIER" in text
    assert "Goa" in text
    assert "BUDGET & FINANCIAL METRICS" in text
    assert "SCHEDULED ACTIVITIES / ITINERARY" in text
    print("  [PASS] Generated trip dossier .txt with length:", len(text), "chars")


def test_planner_to_finder_file_transfer():
    print("\n--- 3. Testing File Transfer: Planner -> Experience Finder ---")
    # Simulate Planner sending a trip dossier .txt file to Experience Finder
    sample_trip_file = (
        "TRIP DOSSIER: Goa Holiday 2026\n"
        "Traveler: Arun Kumar\n"
        "Budget: INR 25,000\n"
        "Days: 4 Days / 3 Nights\n"
        "Special Requests: Scuba Diving certification booking\n"
    )

    files = {
        "file": ("goa_trip_dossier.txt", sample_trip_file.encode("utf-8"), "text/plain")
    }
    data = {
        "filename": "goa_trip_dossier.txt",
        "sender": "Smart Travel Planner (:8000)"
    }

    # Send to Experience Finder
    post_resp = finder_client.post("/api/sync/receive-file", files=files, data=data)
    assert post_resp.status_code == 200
    result = post_resp.json()
    assert result["status"] == "success"
    file_id = result["file_id"]
    print(f"  [PASS] Experience Finder received file with ID #{file_id} ({result['filename']})")

    # Verify Experience Finder received files listing
    list_resp = finder_client.get("/api/sync/received-files")
    assert list_resp.status_code == 200
    files_list = list_resp.json()["files"]
    assert any(f["id"] == file_id for f in files_list)
    print(f"  [PASS] File #{file_id} visible in Experience Finder inbox")

    # Verify Preview endpoint
    preview_resp = finder_client.get(f"/api/sync/preview/{file_id}")
    assert preview_resp.status_code == 200
    assert "TRIP DOSSIER: Goa Holiday 2026" in preview_resp.json()["content"]
    print(f"  [PASS] File preview verified in Experience Finder")

    # Verify File Download endpoint
    download_resp = finder_client.get(f"/api/sync/download/{file_id}")
    assert download_resp.status_code == 200
    assert download_resp.text == sample_trip_file
    assert "attachment" in download_resp.headers.get("content-disposition", "")
    print(f"  [PASS] File download returns exact original text content from Experience Finder")


def test_finder_to_planner_file_transfer():
    print("\n--- 4. Testing File Transfer: Experience Finder -> Planner ---")
    # Simulate Experience Finder sending confirmed booking vouchers to Planner
    sample_voucher_file = (
        "CONFIRMED ACTIVITY VOUCHER PACK\n"
        "Issuer: Experience Finder Partner Services (:8001)\n"
        "Destination: Goa\n"
        "Activities:\n"
        "  - Scuba Diving (Grande Island) | PADI Certified\n"
        "  - Dolphin Watching Safari | Mandovi Bay\n"
        "Voucher Code: EXP-GOA-2026-9912\n"
    )

    files = {
        "file": ("experience_vouchers_goa.txt", sample_voucher_file.encode("utf-8"), "text/plain")
    }
    data = {
        "filename": "experience_vouchers_goa.txt",
        "sender": "Experience Finder (:8001)"
    }

    # Send to Smart Travel Planner
    post_resp = planner_client.post("/api/sync/receive-file", files=files, data=data)
    assert post_resp.status_code == 200
    result = post_resp.json()
    assert result["status"] == "success"
    file_id = result["file_id"]
    print(f"  [PASS] Planner received file with ID #{file_id} ({result['filename']})")

    # Verify Planner received files listing
    list_resp = planner_client.get("/api/sync/received-files")
    assert list_resp.status_code == 200
    files_list = list_resp.json()["files"]
    assert any(f["id"] == file_id for f in files_list)
    print(f"  [PASS] File #{file_id} visible in Planner inbox")

    # Verify Preview endpoint
    preview_resp = planner_client.get(f"/api/sync/preview/{file_id}")
    assert preview_resp.status_code == 200
    assert "CONFIRMED ACTIVITY VOUCHER PACK" in preview_resp.json()["content"]
    print(f"  [PASS] File preview verified in Planner")

    # Verify File Download endpoint
    download_resp = planner_client.get(f"/api/sync/download/{file_id}")
    assert download_resp.status_code == 200
    assert download_resp.text == sample_voucher_file
    assert "attachment" in download_resp.headers.get("content-disposition", "")
    print(f"  [PASS] File download returns exact original text content from Planner")


def test_custom_text_upload():
    print("\n--- 5. Testing Custom Text Payload Form Upload ---")
    custom_content = "Custom notes uploaded via form field\nLine 2: Demonstration for faculty viva."
    resp = planner_client.post(
        "/api/sync/receive-file",
        data={
            "content": custom_content,
            "filename": "viva_demo_notes.txt",
            "sender": "Viva Examiner Demo"
        }
    )
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]
    dl = planner_client.get(f"/api/sync/download/{file_id}")
    assert dl.status_code == 200
    assert "viva_demo_notes.txt" in dl.headers.get("content-disposition", "")
    assert dl.text == custom_content
    print("  [PASS] Custom form-based text upload and download verified")


if __name__ == "__main__":
    test_peer_health()
    test_export_trip_text()
    test_planner_to_finder_file_transfer()
    test_finder_to_planner_file_transfer()
    test_custom_text_upload()
    print("\n=======================================================")
    print("SUCCESS: ALL BIDIRECTIONAL FILE TRANSFER TESTS PASSED!")
    print("=======================================================\n")
