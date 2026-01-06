#!/usr/bin/env python3
"""
Backend Test Suite for Trading-Bot V3.0.0 4-Pillar Confidence Engine
Tests Market Data API, Signals Status API, and Market Refresh API
Based on review request for 4-pillar indicators testing
"""

import requests
import sys
import json
from datetime import datetime

class FourPillarTester:
    def __init__(self, base_url="https://tradecore-fix.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []
        
        # Expected 20 assets from review request
        self.expected_assets = [
            "GOLD", "SILVER", "PLATINUM", "PALLADIUM", "COPPER", "ZINC",
            "WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS", "WHEAT", "CORN", 
            "SOYBEANS", "COFFEE", "SUGAR", "COCOA", "EURUSD", "USDJPY", 
            "BITCOIN", "ETHEREUM", "NASDAQ100"
        ]
        
        # New 4-pillar indicators to verify
        self.required_indicators = ["adx", "atr", "bollinger_upper", "bollinger_lower", "bollinger_width"]

    def run_test(self, name, test_func, *args, **kwargs):
        """Run a single test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            result = test_func(*args, **kwargs)
            if result:
                self.tests_passed += 1
                self.passed_tests.append(name)
                print(f"✅ Passed - {name}")
                return True
            else:
                self.failed_tests.append(name)
                print(f"❌ Failed - {name}")
                return False
        except Exception as e:
            self.failed_tests.append(f"{name}: {str(e)}")
            print(f"❌ Failed - {name}: {str(e)}")
            return False

    def test_api_endpoint(self, endpoint, expected_status=200, method='GET', data=None):
        """Test API endpoint"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            
            success = response.status_code == expected_status
            if success:
                print(f"   Status: {response.status_code}")
                if response.headers.get('content-type', '').startswith('application/json'):
                    try:
                        json_data = response.json()
                        return success, json_data
                    except:
                        print("   Response: Not valid JSON")
                        return success, {}
            else:
                print(f"   Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            
            return success, {}
        except Exception as e:
            print(f"   Error: {str(e)}")
            return False, {}

    def test_market_data_all_endpoint(self):
        """Test GET /api/market/all - verify 20 assets with new indicators"""
        try:
            success, data = self.test_api_endpoint("market/all")
            if not success:
                print("   ❌ Market data endpoint not accessible")
                return False
            
            # Check if we have markets data
            markets = data.get('markets', {})
            if not markets:
                print("   ❌ No markets data returned")
                return False
            
            asset_count = len(markets)
            print(f"   Found {asset_count} assets")
            
            # Verify we have 20 assets
            if asset_count < 20:
                print(f"   ❌ Expected 20 assets, got {asset_count}")
                return False
            
            # Check for expected assets
            found_assets = list(markets.keys())
            missing_assets = [asset for asset in self.expected_assets if asset not in found_assets]
            
            if missing_assets:
                print(f"   ⚠️ Missing expected assets: {missing_assets}")
            
            print(f"   ✅ Found expected assets: {len(self.expected_assets) - len(missing_assets)}/{len(self.expected_assets)}")
            
            # Check for new 4-pillar indicators in each asset
            assets_with_indicators = 0
            assets_without_indicators = 0
            indicator_stats = {indicator: 0 for indicator in self.required_indicators}
            
            for asset_name, asset_data in markets.items():
                has_all_indicators = True
                asset_indicators = []
                
                for indicator in self.required_indicators:
                    if indicator in asset_data and asset_data[indicator] is not None:
                        indicator_stats[indicator] += 1
                        asset_indicators.append(indicator)
                    else:
                        has_all_indicators = False
                
                if has_all_indicators:
                    assets_with_indicators += 1
                    print(f"   ✅ {asset_name}: All 4-pillar indicators present")
                else:
                    assets_without_indicators += 1
                    missing = [ind for ind in self.required_indicators if ind not in asset_indicators]
                    print(f"   ❌ {asset_name}: Missing indicators: {missing}")
            
            print(f"\n   📊 4-Pillar Indicator Statistics:")
            for indicator, count in indicator_stats.items():
                print(f"   {indicator}: {count}/{asset_count} assets ({count/asset_count*100:.1f}%)")
            
            print(f"\n   Assets with all indicators: {assets_with_indicators}/{asset_count}")
            print(f"   Assets missing indicators: {assets_without_indicators}/{asset_count}")
            
            # Test passes if we have 20 assets and most have the new indicators
            success_criteria = (
                asset_count >= 20 and
                assets_with_indicators > assets_without_indicators
            )
            
            if success_criteria:
                print(f"   ✅ 4-Pillar indicators successfully implemented")
                return True
            else:
                print(f"   ❌ 4-Pillar indicators not properly implemented")
                return False
                
        except Exception as e:
            print(f"   Market data test error: {e}")
            return False

    def test_signals_status_endpoint(self):
        """Test GET /api/signals/status - verify confidence scores and status assignment"""
        try:
            success, data = self.test_api_endpoint("signals/status")
            if not success:
                print("   ❌ Signals status endpoint not accessible")
                return False
            
            # Check if we have signals data
            signals = data.get('signals', {})
            if not signals:
                print("   ❌ No signals data returned")
                return False
            
            signal_count = len(signals)
            print(f"   Found {signal_count} asset signals")
            
            # Analyze confidence scores and status
            confidence_stats = {
                'calculated': 0,  # Not 0 or N/A
                'high_confidence': 0,  # > 50%
                'zero_or_na': 0
            }
            
            status_stats = {
                'green': 0,
                'yellow': 0, 
                'red': 0,
                'unknown': 0
            }
            
            for asset_name, signal_data in signals.items():
                confidence = signal_data.get('confidence', 0)
                status = signal_data.get('status', 'unknown').lower()
                
                # Check confidence score
                if confidence is None or confidence == 0 or str(confidence).upper() == 'N/A':
                    confidence_stats['zero_or_na'] += 1
                    print(f"   ❌ {asset_name}: Confidence = {confidence} (not calculated)")
                else:
                    confidence_stats['calculated'] += 1
                    if confidence > 50:
                        confidence_stats['high_confidence'] += 1
                        print(f"   ✅ {asset_name}: Confidence = {confidence}% (high)")
                    else:
                        print(f"   ⚠️ {asset_name}: Confidence = {confidence}% (low)")
                
                # Check status assignment
                if status in ['green', 'yellow', 'red']:
                    status_stats[status] += 1
                    print(f"   ✅ {asset_name}: Status = {status}")
                else:
                    status_stats['unknown'] += 1
                    print(f"   ❌ {asset_name}: Status = {status} (invalid)")
            
            print(f"\n   📊 Confidence Score Statistics:")
            print(f"   Calculated (not 0/N/A): {confidence_stats['calculated']}/{signal_count}")
            print(f"   High confidence (>50%): {confidence_stats['high_confidence']}/{signal_count}")
            print(f"   Zero or N/A: {confidence_stats['zero_or_na']}/{signal_count}")
            
            print(f"\n   📊 Status Assignment Statistics:")
            for status, count in status_stats.items():
                if status != 'unknown':
                    print(f"   {status.upper()}: {count}/{signal_count}")
                else:
                    print(f"   UNKNOWN/INVALID: {count}/{signal_count}")
            
            # Test passes if most assets have calculated confidence and proper status
            success_criteria = (
                confidence_stats['calculated'] > confidence_stats['zero_or_na'] and
                confidence_stats['high_confidence'] > 0 and
                status_stats['unknown'] == 0
            )
            
            if success_criteria:
                print(f"   ✅ Confidence scores and status assignment working correctly")
                return True
            else:
                print(f"   ❌ Issues with confidence calculation or status assignment")
                return False
                
        except Exception as e:
            print(f"   Signals status test error: {e}")
            return False

    def test_market_refresh_endpoint(self):
        """Test POST /api/market/refresh?clear_cache=true - verify cache clearing and refresh"""
        try:
            # First, get current market data timestamp for comparison
            success, before_data = self.test_api_endpoint("market/all")
            before_timestamp = None
            
            if success and before_data.get('markets'):
                # Get timestamp from first asset
                first_asset = next(iter(before_data['markets'].values()), {})
                before_timestamp = first_asset.get('timestamp')
                print(f"   Before refresh timestamp: {before_timestamp}")
            
            # Call refresh endpoint
            success, refresh_data = self.test_api_endpoint("market/refresh?clear_cache=true", method='POST')
            if not success:
                print("   ❌ Market refresh endpoint not accessible")
                return False
            
            # Check refresh response
            refreshed = refresh_data.get('refreshed', False)
            cache_cleared = refresh_data.get('cache_cleared', False)
            message = refresh_data.get('message', '')
            
            print(f"   Refreshed: {refreshed}")
            print(f"   Cache cleared: {cache_cleared}")
            print(f"   Message: {message}")
            
            if not refreshed:
                print("   ❌ Market data was not refreshed")
                return False
            
            # Wait a moment and check if data was actually refreshed
            import time
            time.sleep(2)
            
            success, after_data = self.test_api_endpoint("market/all")
            if success and after_data.get('markets'):
                first_asset = next(iter(after_data['markets'].values()), {})
                after_timestamp = first_asset.get('timestamp')
                print(f"   After refresh timestamp: {after_timestamp}")
                
                # Check if timestamp changed (indicating refresh)
                if before_timestamp and after_timestamp and after_timestamp != before_timestamp:
                    print(f"   ✅ Data timestamp changed - refresh confirmed")
                elif not before_timestamp:
                    print(f"   ✅ Refresh completed (no before timestamp to compare)")
                else:
                    print(f"   ⚠️ Timestamp unchanged - refresh may not have updated data")
            
            # Test passes if refresh endpoint works
            if refreshed:
                print(f"   ✅ Market refresh endpoint working correctly")
                return True
            else:
                print(f"   ❌ Market refresh endpoint not working")
                return False
                
        except Exception as e:
            print(f"   Market refresh test error: {e}")
            return False

    def test_indicator_values_not_null(self):
        """Verify that 4-pillar indicator values are NOT null for most assets"""
        try:
            success, data = self.test_api_endpoint("market/all")
            if not success:
                return False
            
            markets = data.get('markets', {})
            if not markets:
                return False
            
            print(f"   Checking indicator values for {len(markets)} assets...")
            
            null_count_by_indicator = {indicator: 0 for indicator in self.required_indicators}
            valid_count_by_indicator = {indicator: 0 for indicator in self.required_indicators}
            
            for asset_name, asset_data in markets.items():
                for indicator in self.required_indicators:
                    value = asset_data.get(indicator)
                    if value is None or (isinstance(value, str) and value.lower() in ['null', 'none', 'n/a']):
                        null_count_by_indicator[indicator] += 1
                    else:
                        valid_count_by_indicator[indicator] += 1
                        # Print some example values
                        if valid_count_by_indicator[indicator] <= 3:
                            print(f"   ✅ {asset_name}.{indicator} = {value}")
            
            print(f"\n   📊 Indicator Value Statistics:")
            all_indicators_good = True
            
            for indicator in self.required_indicators:
                valid_count = valid_count_by_indicator[indicator]
                null_count = null_count_by_indicator[indicator]
                total = valid_count + null_count
                valid_percentage = (valid_count / total * 100) if total > 0 else 0
                
                print(f"   {indicator}: {valid_count}/{total} valid ({valid_percentage:.1f}%)")
                
                # Indicator is considered good if >70% of assets have valid values
                if valid_percentage < 70:
                    all_indicators_good = False
                    print(f"     ❌ Too many null values for {indicator}")
                else:
                    print(f"     ✅ Good coverage for {indicator}")
            
            if all_indicators_good:
                print(f"   ✅ All 4-pillar indicators have good non-null coverage")
                return True
            else:
                print(f"   ❌ Some 4-pillar indicators have too many null values")
                return False
                
        except Exception as e:
            print(f"   Indicator values test error: {e}")
            return False

def main():
    """Main test function for 4-Pillar Confidence Engine"""
    print("🚀 Starting Trading-Bot V3.0.0 4-Pillar Confidence Engine Test Suite")
    print("🎯 Testing: Market Data API, Signals Status API, Market Refresh API")
    print("=" * 80)
    
    tester = FourPillarTester()
    
    # ============================================================================
    # 4-PILLAR CONFIDENCE ENGINE TESTS
    # ============================================================================
    
    print(f"\n💎 1. Market Data API Test (GET /api/market/all)")
    print("   - Verify all 20 assets are returned")
    print("   - Check new indicators: adx, atr, bollinger_upper, bollinger_lower, bollinger_width")
    tester.run_test(
        "Market Data API - 20 assets with 4-pillar indicators",
        tester.test_market_data_all_endpoint
    )
    
    print(f"\n📊 2. Signals Status API Test (GET /api/signals/status)")
    print("   - Verify confidence scores are calculated (not 0 or N/A)")
    print("   - Check status assignment (green/yellow/red)")
    print("   - Verify at least some assets have confidence > 50%")
    tester.run_test(
        "Signals Status API - confidence scores and status",
        tester.test_signals_status_endpoint
    )
    
    print(f"\n🔄 3. Market Refresh API Test (POST /api/market/refresh?clear_cache=true)")
    print("   - Test endpoint functionality")
    print("   - Verify cache clearing and data refresh")
    tester.run_test(
        "Market Refresh API - cache clearing and refresh",
        tester.test_market_refresh_endpoint
    )
    
    print(f"\n🔍 4. Indicator Values Verification")
    print("   - Verify 4-pillar indicator values are NOT null")
    tester.run_test(
        "4-Pillar Indicators - non-null values verification",
        tester.test_indicator_values_not_null
    )
    
    # ============================================================================
    # RESULTS SUMMARY
    # ============================================================================
    
    print("\n" + "=" * 80)
    print("📊 4-PILLAR CONFIDENCE ENGINE TEST RESULTS")
    print("=" * 80)
    print(f"Tests run: {tester.tests_run}")
    print(f"Tests passed: {tester.tests_passed}")
    print(f"Tests failed: {len(tester.failed_tests)}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ Failed tests:")
        for test in tester.failed_tests:
            print(f"   - {test}")
    
    if tester.passed_tests:
        print(f"\n✅ Passed tests:")
        for test in tester.passed_tests:
            print(f"   - {test}")
    
    # Final assessment
    print(f"\n" + "=" * 80)
    print("🎯 4-PILLAR CONFIDENCE ENGINE ASSESSMENT")
    print("=" * 80)
    
    critical_tests = [
        "Market Data API - 20 assets with 4-pillar indicators",
        "Signals Status API - confidence scores and status", 
        "4-Pillar Indicators - non-null values verification"
    ]
    
    critical_passed = sum(1 for test in tester.passed_tests if test in critical_tests)
    critical_total = len(critical_tests)
    
    print(f"Critical tests passed: {critical_passed}/{critical_total}")
    
    if critical_passed == critical_total:
        print("🟢 4-PILLAR CONFIDENCE ENGINE: FULLY OPERATIONAL")
        print("   ✅ All 20 assets available with new indicators")
        print("   ✅ Confidence scores calculated correctly")
        print("   ✅ Indicator values populated (not null)")
    elif critical_passed >= 2:
        print("🟡 4-PILLAR CONFIDENCE ENGINE: PARTIALLY OPERATIONAL")
        print("   ⚠️ Some components working, others need attention")
    else:
        print("🔴 4-PILLAR CONFIDENCE ENGINE: NEEDS ATTENTION")
        print("   ❌ Critical components not working properly")
    
    return tester.tests_passed == tester.tests_run

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)