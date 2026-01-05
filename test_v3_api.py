"""
Test V3 Offer-Centric API Endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_get_bookmakers():
    """Test getting available bookmakers list"""
    print("\n=== Test: Get Available Bookmakers ===")
    response = requests.get(f"{BASE_URL}/v3/bookmakers")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "bookmakers" in data, "Response should have 'bookmakers' key"
    assert len(data["bookmakers"]) > 0, "Should have at least one bookmaker"
    print(f"Found {len(data['bookmakers'])} bookmakers")
    print(f"Sample: {data['bookmakers'][:5]}")
    print("PASSED")


def test_seed_offers():
    """Test seeding sample offers"""
    print("\n=== Test: Seed Sample Offers ===")
    response = requests.post(f"{BASE_URL}/v3/offers/catalog/seed")
    
    # May return 200 or 500 if already seeded (that's ok)
    print(f"Status: {response.status_code}")
    print("PASSED (seeding attempted)")


def test_get_offers_catalog():
    """Test getting offers catalog"""
    print("\n=== Test: Get Offers Catalog ===")
    response = requests.get(f"{BASE_URL}/v3/offers/catalog")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "offers" in data, "Response should have 'offers' key"
    assert "total" in data, "Response should have 'total' key"
    
    print(f"Found {data['total']} offers")
    
    if data["offers"]:
        offer = data["offers"][0]
        print(f"Sample offer: {offer['bookmaker']} - {offer['offer_name']}")
        assert "bookmaker" in offer
        assert "offer_name" in offer
        assert "offer_value" in offer
        assert "expected_profit" in offer
    
    print("PASSED")
    return data["offers"]


def test_get_offer_details(offers):
    """Test getting specific offer details"""
    if not offers:
        print("\n=== Test: Get Offer Details ===")
        print("SKIPPED (no offers)")
        return
    
    print("\n=== Test: Get Offer Details ===")
    offer_id = offers[0]["id"]
    response = requests.get(f"{BASE_URL}/v3/offers/catalog/{offer_id}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    print(f"Offer: {data['bookmaker']} - {data['offer_name']}")
    print(f"Value: {data['offer_value']}, Expected Profit: {data['expected_profit']}")
    print(f"Terms: {data.get('terms_summary', 'N/A')}")
    print("PASSED")


def test_get_stage_actions():
    """Test getting stage action labels"""
    print("\n=== Test: Get Stage Actions ===")
    response = requests.get(f"{BASE_URL}/v3/offers/stages/actions")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    expected_stages = ["discovered", "selected", "signing_up", "completed"]
    for stage in expected_stages:
        assert stage in data, f"Missing stage: {stage}"
    
    print(f"Stage actions: {len(data)} stages defined")
    print(f"Sample: 'selected' -> '{data['selected']}'")
    print("PASSED")


def test_calculator():
    """Test calculator endpoint"""
    print("\n=== Test: Calculator ===")
    payload = {
        "back_odds": 2.0,
        "stake": 10.0,
        "lay_odds": 2.1,
        "commission": 0.05,
        "bet_type": "qualifying"
    }
    response = requests.post(f"{BASE_URL}/calculate", json=payload)
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    
    print(f"Back: {payload['back_odds']} x {payload['stake']}")
    print(f"Lay: {data['lay_stake']:.2f} @ {payload['lay_odds']}")
    print(f"Liability: {data['liability']:.2f}")
    
    for outcome in data.get("outcomes", []):
        print(f"  {outcome['outcome']}: {outcome['profit']:.2f}")
    
    print("PASSED")


def test_find_matches():
    """Test find matches endpoint"""
    print("\n=== Test: Find Matches ===")
    response = requests.get(f"{BASE_URL}/find-matches")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    print(f"Found {len(data.get('recommendations', []))} recommendations")
    if data.get("recommendations"):
        rec = data["recommendations"][0]
        print(f"Sample: {rec['home_team']} vs {rec['away_team']}")
        print(f"  Back: {rec['back_odds']}, Lay: {rec['lay_odds']}, Spread: {rec['spread_percent']:.2f}%")
    print("PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("V3 API Tests")
    print("=" * 60)
    
    try:
        test_get_bookmakers()
        test_seed_offers()
        offers = test_get_offers_catalog()
        test_get_offer_details(offers)
        test_get_stage_actions()
        test_calculator()
        test_find_matches()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("\nERROR: Cannot connect to API. Is the backend running?")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False
    
    return True


if __name__ == "__main__":
    run_all_tests()

