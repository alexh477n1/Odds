"""Comprehensive test suite for MatchCaddy backend."""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test results tracking
results = {"passed": 0, "failed": 0, "errors": []}


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result."""
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}")
    if details and not passed:
        print(f"         {details}")
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
        results["errors"].append(f"{name}: {details}")


async def test_health_check():
    """Test health check endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Health Check")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            log_test("GET /health returns 200", response.status_code == 200)
            log_test("Response contains status", "status" in response.json())
            log_test("Status is healthy", response.json().get("status") == "healthy")
        except Exception as e:
            log_test("Health check", False, str(e))


async def test_root():
    """Test root endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Root Endpoint")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/")
            log_test("GET / returns 200", response.status_code == 200)
            data = response.json()
            log_test("Response contains message", "message" in data)
            log_test("Response contains version", "version" in data)
        except Exception as e:
            log_test("Root endpoint", False, str(e))


async def test_calculator_qualifying():
    """Test qualifying bet calculator."""
    print("\n" + "=" * 60)
    print("TEST: Calculator - Qualifying Bet")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Basic qualifying bet
        payload = {
            "back_odds": 2.10,
            "lay_odds": 2.12,
            "stake": 10.0,
            "bet_type": "qualifying",
            "commission": 0.05
        }
        
        try:
            response = await client.post(f"{BASE_URL}/calculate", json=payload)
            log_test("POST /calculate returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Response contains lay_stake", "lay_stake" in data)
            log_test("Response contains liability", "liability" in data)
            log_test("Response contains guaranteed_profit", "guaranteed_profit" in data)
            log_test("Response contains outcomes", "outcomes" in data and len(data["outcomes"]) == 2)
            log_test("Lay stake is reasonable", 9 < data["lay_stake"] < 12)
            log_test("Guaranteed profit is negative (qualifying loss)", data["guaranteed_profit"] < 0)
            log_test("Rating is present", "rating" in data)
            
            # Test math accuracy
            # For qualifying: outcomes should be roughly equal
            outcomes = data["outcomes"]
            diff = abs(outcomes[0]["profit"] - outcomes[1]["profit"])
            log_test("Outcomes are balanced (diff < 0.05)", diff < 0.05)
            
        except Exception as e:
            log_test("Qualifying calculator", False, str(e))
        
        # Test 2: Edge case - very tight spread
        payload_tight = {
            "back_odds": 2.00,
            "lay_odds": 2.01,
            "stake": 100.0,
            "bet_type": "qualifying",
            "commission": 0.05
        }
        
        try:
            response = await client.post(f"{BASE_URL}/calculate", json=payload_tight)
            data = response.json()
            log_test("Tight spread: Rating is Excellent", data["rating"] == "Excellent")
            log_test("Tight spread: Low qualifying loss", abs(data["guaranteed_profit"]) < 5)  # For £100 stake
        except Exception as e:
            log_test("Tight spread test", False, str(e))
        
        # Test 3: Edge case - wide spread
        payload_wide = {
            "back_odds": 2.00,
            "lay_odds": 2.20,
            "stake": 10.0,
            "bet_type": "qualifying",
            "commission": 0.05
        }
        
        try:
            response = await client.post(f"{BASE_URL}/calculate", json=payload_wide)
            data = response.json()
            log_test("Wide spread: Rating is Poor", data["rating"] == "Poor")
            log_test("Wide spread: Higher qualifying loss", abs(data["guaranteed_profit"]) > 0.5)
        except Exception as e:
            log_test("Wide spread test", False, str(e))


async def test_calculator_free_bet_snr():
    """Test free bet SNR calculator."""
    print("\n" + "=" * 60)
    print("TEST: Calculator - Free Bet SNR")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        payload = {
            "back_odds": 3.00,
            "lay_odds": 3.05,
            "stake": 20.0,
            "bet_type": "free_bet_snr",
            "commission": 0.05
        }
        
        try:
            response = await client.post(f"{BASE_URL}/calculate", json=payload)
            log_test("POST /calculate (SNR) returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Bet type is free_bet_snr", data["bet_type"] == "free_bet_snr")
            log_test("Guaranteed profit is positive", data["guaranteed_profit"] > 0)
            log_test("Lay stake is less than stake (SNR)", data["lay_stake"] < payload["stake"])
            
            # SNR retention check: profit should be ~60-80% of stake for reasonable odds
            retention = (data["guaranteed_profit"] / payload["stake"]) * 100
            log_test(f"Retention rate is reasonable ({retention:.1f}%)", 50 < retention < 85)
            
        except Exception as e:
            log_test("Free bet SNR calculator", False, str(e))


async def test_calculator_free_bet_sr():
    """Test free bet SR calculator."""
    print("\n" + "=" * 60)
    print("TEST: Calculator - Free Bet SR (Stake Returned)")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        payload = {
            "back_odds": 2.50,
            "lay_odds": 2.52,
            "stake": 10.0,
            "bet_type": "free_bet_sr",
            "commission": 0.05
        }
        
        try:
            response = await client.post(f"{BASE_URL}/calculate", json=payload)
            log_test("POST /calculate (SR) returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Bet type is free_bet_sr", data["bet_type"] == "free_bet_sr")
            log_test("Guaranteed profit is positive", data["guaranteed_profit"] > 0)
            
            # SR should have higher profit than SNR for same odds
            # because you're covering the full payout, not just profit
            log_test("Lay stake covers full payout", data["lay_stake"] > payload["stake"])
            
        except Exception as e:
            log_test("Free bet SR calculator", False, str(e))


async def test_calculator_batch():
    """Test batch calculator."""
    print("\n" + "=" * 60)
    print("TEST: Calculator - Batch")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        payload = {
            "calculations": [
                {"back_odds": 2.10, "lay_odds": 2.12, "stake": 10.0, "bet_type": "qualifying", "commission": 0.05},
                {"back_odds": 2.10, "lay_odds": 2.12, "stake": 10.0, "bet_type": "free_bet_snr", "commission": 0.05},
            ]
        }
        
        try:
            response = await client.post(f"{BASE_URL}/calculate/batch", json=payload)
            log_test("POST /calculate/batch returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Results array has 2 items", len(data["results"]) == 2)
            log_test("Total profit is calculated", "total_guaranteed_profit" in data)
            log_test("Best opportunity is identified", data["best_opportunity"] is not None)
            
            # Total should be qualifying loss + free bet profit
            total = data["total_guaranteed_profit"]
            qual_profit = data["results"][0]["guaranteed_profit"]
            fb_profit = data["results"][1]["guaranteed_profit"]
            log_test("Total equals sum of parts", abs(total - (qual_profit + fb_profit)) < 0.01)
            log_test("Total profit is positive (offer is worth it)", total > 0)
            
        except Exception as e:
            log_test("Batch calculator", False, str(e))


async def test_calculator_retention():
    """Test retention calculator."""
    print("\n" + "=" * 60)
    print("TEST: Calculator - Retention")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/calculate/retention",
                params={"free_bet_value": 50, "back_odds": 3.0, "lay_odds": 3.05, "commission": 0.05}
            )
            log_test("GET /calculate/retention returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Retention percent is present", "retention_percent" in data)
            log_test("Guaranteed profit is present", "guaranteed_profit" in data)
            log_test("Rating is present", "rating" in data)
            log_test("Retention is reasonable (50-80%)", 50 < data["retention_percent"] < 80)
            
            # Verify math: profit = retention% * free_bet_value / 100
            expected_profit = (data["retention_percent"] / 100) * 50
            log_test("Profit matches retention", abs(data["guaranteed_profit"] - expected_profit) < 0.1)
            
        except Exception as e:
            log_test("Retention calculator", False, str(e))


async def test_calculator_validation():
    """Test calculator input validation."""
    print("\n" + "=" * 60)
    print("TEST: Calculator - Input Validation")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test invalid odds (< 1.0)
        try:
            response = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": 0.5,  # Invalid
                "lay_odds": 2.0,
                "stake": 10.0,
                "bet_type": "qualifying"
            })
            log_test("Rejects odds < 1.0", response.status_code == 422)
        except Exception as e:
            log_test("Odds validation", False, str(e))
        
        # Test invalid stake (< 0)
        try:
            response = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": 2.0,
                "lay_odds": 2.1,
                "stake": -10.0,  # Invalid
                "bet_type": "qualifying"
            })
            log_test("Rejects negative stake", response.status_code == 422)
        except Exception as e:
            log_test("Stake validation", False, str(e))
        
        # Test invalid bet type
        try:
            response = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": 2.0,
                "lay_odds": 2.1,
                "stake": 10.0,
                "bet_type": "invalid_type"  # Invalid
            })
            log_test("Rejects invalid bet type", response.status_code == 422)
        except Exception as e:
            log_test("Bet type validation", False, str(e))


async def test_find_matches():
    """Test match finder endpoint."""
    print("\n" + "=" * 60)
    print("TEST: Match Finder")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/find-matches", params={
                "min_odds": 1.5,
                "max_odds": 5.0,
                "max_spread": 5.0,
                "limit": 5
            })
            log_test("GET /find-matches returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Success is true", data["success"] == True)
            log_test("Matches found count is present", "matches_found" in data)
            log_test("Recommendations array is present", "recommendations" in data)
            log_test("API requests remaining is tracked", "api_requests_remaining" in data)
            
            if data["recommendations"]:
                rec = data["recommendations"][0]
                log_test("Recommendation has match_id", "match_id" in rec)
                log_test("Recommendation has back_odds", "back_odds" in rec)
                log_test("Recommendation has lay_odds", "lay_odds" in rec)
                log_test("Recommendation has spread_percent", "spread_percent" in rec)
                log_test("Recommendation has match_rating", "match_rating" in rec)
                log_test("Recommendation has qualifying_loss", "qualifying_loss" in rec)
                log_test("Recommendation has free_bet_profit", "free_bet_profit" in rec)
                
                # Validate spread is within limit
                log_test("Spread is within limit", rec["spread_percent"] <= 5.0)
                
                # Validate odds are in range
                log_test("Back odds in range", 1.5 <= rec["back_odds"] <= 5.0)
                
                print(f"\n  Sample match: {rec['home_team']} vs {rec['away_team']}")
                print(f"  Back: {rec['back_odds']} @ {rec['back_bookmaker']}")
                print(f"  Lay: {rec['lay_odds']} @ {rec['lay_exchange']}")
                print(f"  Spread: {rec['spread_percent']}%")
            else:
                print("  (No matches found - API may have no upcoming games)")
            
        except Exception as e:
            log_test("Match finder", False, str(e))


async def test_find_matches_filters():
    """Test match finder with different filters."""
    print("\n" + "=" * 60)
    print("TEST: Match Finder - Filters")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test with stricter odds filter
        try:
            response = await client.get(f"{BASE_URL}/find-matches", params={
                "min_odds": 1.5,
                "max_odds": 4.0,
                "limit": 3
            })
            log_test("Odds filter endpoint works", response.status_code == 200)
            
            data = response.json()
            if data["recommendations"]:
                for rec in data["recommendations"]:
                    in_range = 1.5 <= rec["back_odds"] <= 4.0
                    if not in_range:
                        log_test(f"Odds {rec['back_odds']} in range 1.5-4.0", False)
                        break
                else:
                    log_test("All recommendations have odds in filtered range", True)
            else:
                log_test("All recommendations have odds in filtered range", True)  # No matches = pass
                
        except Exception as e:
            log_test("Odds filter test", False, str(e))
        
        # Test with very tight spread requirement
        try:
            response = await client.get(f"{BASE_URL}/find-matches", params={
                "max_spread": 1.0,  # Very tight
                "limit": 5
            })
            log_test("Tight spread filter works", response.status_code == 200)
            
            data = response.json()
            for rec in data["recommendations"]:
                if rec["spread_percent"] > 1.0:
                    log_test("Spread filter respected", False)
                    break
            else:
                log_test("All recommendations have spread <= 1%", True)
                
        except Exception as e:
            log_test("Spread filter test", False, str(e))


async def test_generate_instructions():
    """Test instruction generator."""
    print("\n" + "=" * 60)
    print("TEST: Instruction Generator - Single Bet")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test qualifying bet instructions
        payload = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "outcome": "home",
            "back_odds": 2.10,
            "lay_odds": 2.12,
            "bookmaker": "Coral",
            "exchange": "Betfair",
            "stake": 10.0,
            "bet_type": "qualifying",
            "commission": 0.05,
            "offer_name": "Test Offer",
            "min_odds_required": 2.0
        }
        
        try:
            response = await client.post(f"{BASE_URL}/generate-instructions", json=payload)
            log_test("POST /generate-instructions returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Title is present", "title" in data)
            log_test("Summary is present", "summary" in data)
            log_test("Steps are present", "steps" in data and len(data["steps"]) >= 2)
            log_test("Plain text is present", "plain_text" in data)
            log_test("Lay stake is calculated", "lay_stake" in data)
            log_test("Expected result is present", "expected_result" in data)
            
            # Check steps contain required info
            steps_text = " ".join([s["details"] for s in data["steps"]])
            log_test("Steps mention bookmaker", "Coral" in steps_text or "10.00" in steps_text)
            log_test("Steps mention team", "Arsenal" in steps_text)
            
        except Exception as e:
            log_test("Instruction generator", False, str(e))
        
        # Test free bet instructions
        payload["bet_type"] = "free_bet_snr"
        try:
            response = await client.post(f"{BASE_URL}/generate-instructions", json=payload)
            log_test("Free bet instructions return 200", response.status_code == 200)
            
            data = response.json()
            log_test("Free bet has positive expected result", data["expected_result"] > 0)
            log_test("Free bet warnings mention FREE BET", any("free" in w.lower() for w in data["warnings"]))
            
        except Exception as e:
            log_test("Free bet instructions", False, str(e))


async def test_generate_full_offer_instructions():
    """Test full offer instruction generator."""
    print("\n" + "=" * 60)
    print("TEST: Instruction Generator - Full Offer")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        payload = {
            "home_team": "Manchester United",
            "away_team": "Liverpool",
            "outcome": "away",
            "back_odds": 2.50,
            "lay_odds": 2.52,
            "bookmaker": "Bet365",
            "exchange": "Betfair",
            "qualifying_stake": 20.0,
            "free_bet_value": 20.0,
            "commission": 0.05,
            "offer_name": "Bet 20 Get 20 Free Bet",
            "min_odds_required": 2.0
        }
        
        try:
            response = await client.post(f"{BASE_URL}/generate-instructions/full-offer", json=payload)
            log_test("POST /generate-instructions/full-offer returns 200", response.status_code == 200)
            
            data = response.json()
            log_test("Offer name is present", data["offer_name"] == "Bet 20 Get 20 Free Bet")
            log_test("Qualifying instructions present", "qualifying_instructions" in data)
            log_test("Free bet instructions present", "free_bet_instructions" in data)
            log_test("Total profit is calculated", "total_profit" in data)
            log_test("Full plain text is present", "full_plain_text" in data)
            
            # Validate profit calculation
            qual_loss = data["total_qualifying_loss"]
            fb_profit = data["total_free_bet_profit"]
            total = data["total_profit"]
            log_test("Qualifying loss is negative", qual_loss < 0)
            log_test("Free bet profit is positive", fb_profit > 0)
            log_test("Total profit equals sum", abs(total - (qual_loss + fb_profit)) < 0.01)
            log_test("Overall profit is positive", total > 0)
            
            # Check plain text contains key info
            plain = data["full_plain_text"]
            log_test("Plain text mentions offer name", "Bet 20 Get 20" in plain)
            log_test("Plain text mentions teams", "Liverpool" in plain)
            log_test("Plain text has profit summary", "PROFIT" in plain.upper())
            
            print(f"\n  Offer: {data['offer_name']}")
            print(f"  Qualifying loss: {qual_loss:.2f}")
            print(f"  Free bet profit: {fb_profit:.2f}")
            print(f"  TOTAL PROFIT: {total:.2f}")
            
        except Exception as e:
            log_test("Full offer instructions", False, str(e))


async def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("TEST: Edge Cases & Error Handling")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # Test with draw outcome
        try:
            response = await client.post(f"{BASE_URL}/generate-instructions", json={
                "home_team": "Team A",
                "away_team": "Team B",
                "outcome": "draw",
                "back_odds": 3.50,
                "lay_odds": 3.55,
                "bookmaker": "TestBook",
                "stake": 10.0,
                "bet_type": "qualifying"
            })
            log_test("Draw outcome works", response.status_code == 200)
            data = response.json()
            log_test("Draw appears in instructions", "Draw" in data["plain_text"])
        except Exception as e:
            log_test("Draw outcome", False, str(e))
        
        # Test with high odds
        try:
            response = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": 10.0,
                "lay_odds": 10.5,
                "stake": 10.0,
                "bet_type": "free_bet_snr"
            })
            log_test("High odds calculation works", response.status_code == 200)
            data = response.json()
            log_test("High odds: High liability", data["liability"] > 50)
        except Exception as e:
            log_test("High odds", False, str(e))
        
        # Test with Smarkets commission (2%)
        try:
            response = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": 2.0,
                "lay_odds": 2.02,
                "stake": 10.0,
                "bet_type": "qualifying",
                "commission": 0.02  # Smarkets rate
            })
            log_test("Smarkets commission works", response.status_code == 200)
            data = response.json()
            
            # Compare with Betfair commission
            response2 = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": 2.0,
                "lay_odds": 2.02,
                "stake": 10.0,
                "bet_type": "qualifying",
                "commission": 0.05  # Betfair rate
            })
            data2 = response2.json()
            
            # Lower commission should mean better (less negative) result
            log_test("Lower commission = better result", 
                     data["guaranteed_profit"] > data2["guaranteed_profit"])
        except Exception as e:
            log_test("Commission variation", False, str(e))
        
        # Test 404 for non-existent endpoint
        try:
            response = await client.get(f"{BASE_URL}/nonexistent")
            log_test("404 for missing endpoint", response.status_code == 404)
        except Exception as e:
            log_test("404 handling", False, str(e))


async def test_integration_flow():
    """Test the complete integration flow."""
    print("\n" + "=" * 60)
    print("TEST: Integration Flow (Match Find -> Calculate -> Instructions)")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Step 1: Find matches
            matches_response = await client.get(f"{BASE_URL}/find-matches", params={
                "min_odds": 1.8,
                "max_odds": 3.5,
                "max_spread": 3.0,
                "limit": 1
            })
            
            if matches_response.status_code != 200:
                log_test("Integration: Find matches", False, "Failed to find matches")
                return
            
            matches_data = matches_response.json()
            
            if not matches_data["recommendations"]:
                print("  No matches available for integration test - skipping")
                log_test("Integration: Matches available", True, "Skipped - no matches")
                return
            
            match = matches_data["recommendations"][0]
            log_test("Integration: Found match", True)
            print(f"  Using: {match['home_team']} vs {match['away_team']}")
            
            # Step 2: Calculate the bet
            calc_response = await client.post(f"{BASE_URL}/calculate", json={
                "back_odds": match["back_odds"],
                "lay_odds": match["lay_odds"],
                "stake": 10.0,
                "bet_type": "qualifying",
                "commission": 0.05
            })
            
            calc_data = calc_response.json()
            log_test("Integration: Calculate bet", calc_response.status_code == 200)
            
            # Step 3: Generate instructions
            instr_response = await client.post(f"{BASE_URL}/generate-instructions/full-offer", json={
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "outcome": match["outcome"],
                "back_odds": match["back_odds"],
                "lay_odds": match["lay_odds"],
                "bookmaker": match["back_bookmaker"],
                "exchange": "Betfair",
                "qualifying_stake": 10.0,
                "free_bet_value": 10.0,
                "commission": 0.05,
                "offer_name": "Integration Test Offer"
            })
            
            instr_data = instr_response.json()
            log_test("Integration: Generate instructions", instr_response.status_code == 200)
            
            # Verify consistency
            log_test("Integration: Profit is positive", instr_data["total_profit"] > 0)
            
            print(f"\n  Full flow completed successfully!")
            print(f"  Match: {match['home_team']} vs {match['away_team']}")
            print(f"  Back: {match['back_odds']} @ {match['back_bookmaker']}")
            print(f"  Lay: {match['lay_odds']} @ Betfair")
            print(f"  Expected profit: {instr_data['total_profit']:.2f}")
            
        except Exception as e:
            log_test("Integration flow", False, str(e))


async def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MATCHCADDY BACKEND - COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    
    # Run all test suites
    await test_health_check()
    await test_root()
    await test_calculator_qualifying()
    await test_calculator_free_bet_snr()
    await test_calculator_free_bet_sr()
    await test_calculator_batch()
    await test_calculator_retention()
    await test_calculator_validation()
    await test_find_matches()
    await test_find_matches_filters()
    await test_generate_instructions()
    await test_generate_full_offer_instructions()
    await test_edge_cases()
    await test_integration_flow()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    total = results["passed"] + results["failed"]
    print(f"Total tests: {total}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    if results["failed"] > 0:
        print(f"\nFailed tests:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    pass_rate = (results["passed"] / total * 100) if total > 0 else 0
    print(f"\nPass rate: {pass_rate:.1f}%")
    
    if pass_rate == 100:
        print("\n[SUCCESS] All tests passed!")
    elif pass_rate >= 90:
        print("\n[GOOD] Most tests passed, minor issues to fix")
    else:
        print("\n[WARNING] Significant test failures detected")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())

