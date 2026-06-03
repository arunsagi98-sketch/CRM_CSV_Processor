import sys
import io
import os
import pandas as pd

# Add backend directory to sys.path
sys.path.append(r"c:\Users\HP\Desktop\CRM\backend")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "min_ctr" in data
    assert "max_ctr" in data
    print("GET /api/settings: OK", data)

def test_list_campaigns():
    response = client.get("/api/campaigns")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print("GET /api/campaigns: OK", len(data), "rules found")

def test_upsert_campaign():
    payload = {
        "line_item_id": "TestCampaign123",
        "campaign_name": "Test Line Item Label",
        "min_vcr": 76.5,
        "max_vcr": 88.5,
        "min_viewability": 80.0,
        "max_viewability": 90.0,
        "enabled": True
    }
    response = client.post("/api/campaigns", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_id"] == "TestCampaign123"
    assert data["min_vcr"] == 76.5
    print("POST /api/campaigns: OK", data)
    
    # Toggle it
    rule_id = data["id"]
    response = client.patch(f"/api/campaigns/by-id/{rule_id}/toggle")
    assert response.status_code == 200
    print("PATCH /api/campaigns/by-id/{id}/toggle: OK", response.json())
    
    # Delete it
    response = client.delete(f"/api/campaigns/by-id/{rule_id}")
    assert response.status_code == 200
    print("DELETE /api/campaigns/by-id/{id}: OK", response.json())

def test_process_file():
    # Create a dummy CSV file content
    data = {
        "Advertiser": ["Adv1", "Adv2"],
        "Advertiser ID": ["111", "222"],
        "Advertiser Currency": ["USD", "USD"],
        "Insertion Order": ["IO1", "IO2"],
        "Insertion Order ID": ["333", "444"],
        "Line Item": ["LI1", "LI2"],
        "Line Item ID": ["55555", "66666"],
        "Date": ["2026-06-01", "02/06/2026"],
        "Campaign": ["TestCampaign123", "OtherCampaign"],
        "Campaign ID": ["777", "888"],
        "Impressions": ["1000", "5000"],
        "Billable Impressions": ["1000", "5000"],
        "Clicks": ["0", "0"],
        "Click Rate (CTR)": ["0.00%", "0.00%"],
        "Revenue (Adv Currency)": ["10.5", "50.0"],
        "Media Cost (Advertiser Currency)": ["8.0", "40.0"],
        "Start Views": ["800", "4000"],
        "1st Quartile Views": ["700", "3500"],
        "Midpoint Views": ["600", "3000"],
        "3rd Quartile Views": ["500", "2500"],
        "Complete Views": ["400", "2000"],
        "Video Completion Rate": ["0.00%", "0.00%"],
        "Viewable Impressions": ["700", "3500"],
        "Measurable Impressions": ["900", "4500"],
        "Viewability": ["0.00%", "0.00%"],
    }
    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")
    
    # Send POST request
    files = {"file": ("test_input.csv", csv_bytes, "text/csv")}
    response = client.post("/api/process", files=files)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    # Parse returned Excel sheet to verify correctness
    out_df = pd.read_excel(io.BytesIO(response.content))
    
    # Check headers
    from processor import OUTPUT_COLUMNS
    for col in OUTPUT_COLUMNS:
        assert col in out_df.columns, f"Missing column: {col}"
        
    # Assert formatting & bounds
    for idx, row in out_df.iterrows():
        # CTR checks: between 0.37% and 0.55%
        ctr = float(row["Click Rate (CTR)"])
        assert 0.0037 <= ctr <= 0.0055, f"CTR out of bounds: {ctr}"
        
        # VCR checks: since no campaign rule exists, should fallback to global defaults (75% to 89%)
        vcr = float(row["Video Completion Rate"])
        assert 0.75 <= vcr <= 0.89, f"VCR out of bounds: {vcr}"
        
        # Viewability checks: should fallback to global defaults (75% to 89%)
        view = float(row["Viewability"])
        assert 0.75 <= view <= 0.89, f"Viewability out of bounds: {view}"

    print("POST /api/process (No Overrides): OK")


def test_process_with_override():
    # 1. Create a campaign override rule
    payload = {
        "line_item_id": "TestCampaign123", # this maps to matching key
        "campaign_name": "Line Item Label",
        "min_vcr": 92.0,
        "max_vcr": 95.0,
        "min_viewability": 90.0,
        "max_viewability": 94.0,
        "enabled": True
    }
    resp = client.post("/api/campaigns", json=payload)
    assert resp.status_code == 200
    rule_data = resp.json()
    rule_id = rule_data["id"]
    
    # 2. Process file
    data = {
        "Campaign": ["TestCampaign123", "OtherCampaign"],
        "Impressions": ["1000", "5000"],
        "Start Views": ["800", "4000"],
        "Complete Views": ["400", "2000"],
        "Viewable Impressions": ["700", "3500"],
        "Measurable Impressions": ["900", "4500"],
    }
    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")
    
    files = {"file": ("test_input.csv", csv_bytes, "text/csv")}
    response = client.post("/api/process", files=files)
    assert response.status_code == 200
    
    # Verify values for overridden vs non-overridden campaign
    out_df = pd.read_excel(io.BytesIO(response.content))
    
    # Check headers
    from processor import OUTPUT_COLUMNS
    for col in OUTPUT_COLUMNS:
        assert col in out_df.columns, f"Missing column: {col}"
        
    row_override = out_df[out_df["Campaign"] == "TestCampaign123"].iloc[0]
    row_fallback = out_df[out_df["Campaign"] == "OtherCampaign"].iloc[0]
    
    # Override checks
    vcr_o = float(row_override["Video Completion Rate"])
    assert 0.92 <= vcr_o <= 0.95, f"Overridden campaign VCR out of bounds: {vcr_o}"
    
    view_o = float(row_override["Viewability"])
    assert 0.90 <= view_o <= 0.94, f"Overridden campaign Viewability out of bounds: {view_o}"
    
    # Fallback checks
    vcr_f = float(row_fallback["Video Completion Rate"])
    assert 0.75 <= vcr_f <= 0.89, f"Fallback campaign VCR out of bounds: {vcr_f}"
    
    view_f = float(row_fallback["Viewability"])
    assert 0.75 <= view_f <= 0.89, f"Fallback campaign Viewability out of bounds: {view_f}"
    
    # Cleanup
    resp_del = client.delete(f"/api/campaigns/by-id/{rule_id}")
    assert resp_del.status_code == 200
    print("POST /api/process (With Campaign Rule Override): OK")


def test_process_with_equal_bounds():
    # 1. Create a campaign override rule where min == max (e.g. VCR = 95%, Viewability = 99%)
    payload = {
        "line_item_id": "EqualCampaign",
        "campaign_name": "Equal Label",
        "min_vcr": 95.0,
        "max_vcr": 95.0,
        "min_viewability": 99.0,
        "max_viewability": 99.0,
        "enabled": True
    }
    resp = client.post("/api/campaigns", json=payload)
    assert resp.status_code == 200
    rule_id = resp.json()["id"]
    
    # 2. Process file
    data = {
        "Campaign": ["EqualCampaign"],
        "Impressions": ["1000"],
        "Start Views": ["800"],
        "Complete Views": ["400"],
        "Viewable Impressions": ["700"],
        "Measurable Impressions": ["900"],
    }
    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")
    
    files = {"file": ("test_input.csv", csv_bytes, "text/csv")}
    response = client.post("/api/process", files=files)
    assert response.status_code == 200
    
    out_df = pd.read_excel(io.BytesIO(response.content))
    row = out_df.iloc[0]
    
    # Assert values are extremely close to 95.0% and 99.0% (expressed as float in Excel as 0.95 and 0.99)
    # Allows a margin of error due to integer rounding of counts
    vcr_val = float(row["Video Completion Rate"])
    view_val = float(row["Viewability"])
    assert abs(vcr_val - 0.95) < 0.015, f"VCR value mismatch, expected 0.95, got {vcr_val}"
    assert abs(view_val - 0.99) < 0.015, f"Viewability value mismatch, expected 0.99, got {view_val}"
    
    # Cleanup
    resp_del = client.delete(f"/api/campaigns/by-id/{rule_id}")
    assert resp_del.status_code == 200
    print("POST /api/process (With Equal min/max Campaign Rules): OK")


def test_process_with_single_bound():
    # 1. Create a campaign override rule where only min_vcr is specified
    payload = {
        "line_item_id": "SingleBoundCampaign",
        "campaign_name": "Single Label",
        "min_vcr": 92.0,
        "max_vcr": None,
        "min_viewability": None,
        "max_viewability": 80.0,
        "enabled": True
    }
    resp = client.post("/api/campaigns", json=payload)
    assert resp.status_code == 200
    rule_id = resp.json()["id"]
    
    # 2. Process file
    data = {
        "Campaign": ["SingleBoundCampaign"],
        "Impressions": ["1000"],
        "Start Views": ["800"],
        "Complete Views": ["400"],
        "Viewable Impressions": ["700"],
        "Measurable Impressions": ["900"],
    }
    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    csv_bytes = csv_buf.getvalue().encode("utf-8")
    
    files = {"file": ("test_input.csv", csv_bytes, "text/csv")}
    response = client.post("/api/process", files=files)
    assert response.status_code == 200
    
    out_df = pd.read_excel(io.BytesIO(response.content))
    row = out_df.iloc[0]
    
    # VCR checks: since min_vcr = 92% and max_vcr = None (defaults to 89%), min > max.
    # The code resolves min > max by clamping max to min (i.e. [92%, 92%]).
    # So it should be close to 92%.
    vcr_val = float(row["Video Completion Rate"])
    assert abs(vcr_val - 0.92) < 0.015, f"VCR value mismatch, expected 0.92, got {vcr_val}"
    
    # Viewability checks: since min_viewability = None (defaults to 75%) and max_viewability = 80%,
    # viewability range is [75%, 80%].
    view_val = float(row["Viewability"])
    assert 0.74 <= view_val <= 0.81, f"Viewability value out of bounds: {view_val}"
    
    # Cleanup
    resp_del = client.delete(f"/api/campaigns/by-id/{rule_id}")
    assert resp_del.status_code == 200
    print("POST /api/process (With Single boundary Campaign Rules): OK")


if __name__ == "__main__":
    try:
        test_read_settings()
        test_list_campaigns()
        test_upsert_campaign()
        test_process_file()
        test_process_with_override()
        test_process_with_equal_bounds()
        test_process_with_single_bound()
        print("\nAll integration tests passed successfully!")
    except Exception as e:
        print("\nIntegration test failed!", e)
        sys.exit(1)
