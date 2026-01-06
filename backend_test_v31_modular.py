#!/usr/bin/env python3
"""
Backend Test Suite for V3.1.0 Modular Routes Testing
Tests all new modular route modules after complete refactoring
Based on review request for V3.1.0 modular routes testing
"""

import requests
import sys
import asyncio
import os
import json
from datetime import datetime
from pathlib import Path

class V31ModularTester:
    def __init__(self, base_url="https://tradecore-fix.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []

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
                        print(f"   Response keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
                    except:
                        print("   Response: Not valid JSON")
            else:
                print(f"   Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
            
            return success, response.json() if success and response.headers.get('content-type', '').startswith('application/json') else {}
        except Exception as e:
            print(f"   Error: {str(e)}")
            return False, {}

    # ============================================================================
    # V3.1.0 MODULAR ROUTES TESTING - COMPLETE REGRESSION TEST
    # ============================================================================

    def test_v31_market_routes_all(self):
        """Test V3.1.0: All Market Routes (/api/market/...)"""
        try:
            endpoints_to_test = [
                ("market/all", "Market All - should return 20 assets"),
                ("market/hours", "Market Hours - trading hours"),
                ("market/live-ticks", "Live Ticks - real-time prices")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for market/all
                        if endpoint == "market/all":
                            commodities = data.get('commodities', [])
                            if len(commodities) >= 20:
                                print(f"   ✅ Found {len(commodities)} assets (≥20 required)")
                            else:
                                print(f"   ⚠️ Only {len(commodities)} assets found (<20)")
                        
                        # Specific validation for live-ticks
                        elif endpoint == "market/live-ticks":
                            live_prices = data.get('live_prices', {})
                            print(f"   ✅ Live ticks: {len(live_prices)} prices available")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 0.8:  # At least 80% should work
                print(f"   ✅ Market routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ Market routes: {working_endpoints}/{total_endpoints} working (insufficient)")
                return False
                
        except Exception as e:
            print(f"   Market routes test error: {e}")
            return False

    def test_v31_trade_routes_all(self):
        """Test V3.1.0: All Trade Routes (/api/trades/...)"""
        try:
            endpoints_to_test = [
                ("trades/list", "Trade List - all trades"),
                ("trades/stats", "Trade Stats - statistics")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for trades/list
                        if endpoint == "trades/list":
                            trades = data.get('trades', [])
                            live_count = data.get('live_count', 0)
                            closed_count = data.get('closed_count', 0)
                            print(f"   ✅ Found {len(trades)} trades (Live: {live_count}, Closed: {closed_count})")
                        
                        # Specific validation for trades/stats
                        elif endpoint == "trades/stats":
                            total_trades = data.get('total_trades', 0)
                            win_rate = data.get('win_rate', 0)
                            print(f"   ✅ Stats: {total_trades} trades, {win_rate:.1f}% win rate")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 1.0:  # All should work
                print(f"   ✅ Trade routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ Trade routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   Trade routes test error: {e}")
            return False

    def test_v31_platform_routes_all(self):
        """Test V3.1.0: All Platform Routes (/api/platforms/..., /api/mt5/...)"""
        try:
            endpoints_to_test = [
                ("platforms/status", "Platform Status - all platforms"),
                ("mt5/status", "MT5 Status - MetaAPI connection"),
                ("mt5/symbols", "MT5 Symbols - available symbols")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for platforms/status
                        if endpoint == "platforms/status":
                            platforms = data.get('platforms', {})
                            active_count = data.get('active_count', 0)
                            print(f"   ✅ Platforms: {len(platforms)} configured, {active_count} active")
                        
                        # Specific validation for mt5/status
                        elif endpoint == "mt5/status":
                            mt5_status = data.get('mt5_status', {})
                            any_connected = data.get('any_connected', False)
                            print(f"   ✅ MT5: {len(mt5_status)} accounts, connected: {any_connected}")
                        
                        # Specific validation for mt5/symbols
                        elif endpoint == "mt5/symbols":
                            symbols = data.get('symbols', [])
                            print(f"   ✅ MT5 Symbols: {len(symbols)} available")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 0.8:  # At least 80% should work
                print(f"   ✅ Platform routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ Platform routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   Platform routes test error: {e}")
            return False

    def test_v31_settings_routes_all(self):
        """Test V3.1.0: All Settings Routes (/api/settings, /api/bot/..., /api/risk/...)"""
        try:
            endpoints_to_test = [
                ("settings", "Settings - trading configuration"),
                ("bot/status", "Bot Status - trading bot state"),
                ("risk/status", "Risk Status - risk management")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for settings
                        if endpoint == "settings":
                            enabled_commodities = data.get('enabled_commodities', [])
                            auto_trading = data.get('auto_trading', False)
                            trading_mode = data.get('trading_mode', 'unknown')
                            print(f"   ✅ Settings: {len(enabled_commodities)} assets, auto_trading: {auto_trading}, mode: {trading_mode}")
                        
                        # Specific validation for bot/status
                        elif endpoint == "bot/status":
                            bot_running = data.get('bot_running', False)
                            auto_trading = data.get('auto_trading', False)
                            print(f"   ✅ Bot: running={bot_running}, auto_trading={auto_trading}")
                        
                        # Specific validation for risk/status
                        elif endpoint == "risk/status":
                            max_risk = data.get('max_risk_percent', 0)
                            current_exposure = data.get('current_exposure_percent', 0)
                            print(f"   ✅ Risk: {current_exposure:.1f}%/{max_risk:.1f}% exposure")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 1.0:  # All should work
                print(f"   ✅ Settings routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ Settings routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   Settings routes test error: {e}")
            return False

    def test_v31_signals_routes_all(self):
        """Test V3.1.0: All Signals Routes (/api/signals/...)"""
        try:
            endpoints_to_test = [
                ("signals/status", "Signals Status - 4-Pillar confidence scores")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for signals/status
                        if endpoint == "signals/status":
                            signals = data.get('signals', {})
                            summary = data.get('summary', {})
                            green_signals = summary.get('green_signals', 0)
                            total_signals = summary.get('total', 0)
                            print(f"   ✅ Signals: {len(signals)} assets analyzed, {green_signals}/{total_signals} green signals")
                            
                            # Check for 4-Pillar scores in at least one signal
                            pillar_found = False
                            for signal_data in signals.values():
                                pillar_scores = signal_data.get('pillar_scores', {})
                                if pillar_scores and len(pillar_scores) >= 4:
                                    pillar_found = True
                                    print(f"   ✅ 4-Pillar scores found: {list(pillar_scores.keys())}")
                                    break
                            
                            if not pillar_found:
                                print(f"   ⚠️ No 4-Pillar scores found in signals")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 1.0:  # All should work
                print(f"   ✅ Signals routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ Signals routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   Signals routes test error: {e}")
            return False

    def test_v31_ai_routes_all(self):
        """Test V3.1.0: All AI Routes (/api/ai/...)"""
        try:
            endpoints_to_test = [
                ("ai/learning-stats", "Learning Stats - Bayesian learning"),
                ("ai/spread-analysis", "Spread Analysis - V3.1.0 feature"),
                ("ai/pillar-efficiency?asset=GOLD", "Pillar Efficiency - 4-Pillar scores")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for learning-stats
                        if endpoint == "ai/learning-stats":
                            total_optimizations = data.get('total_optimizations', 0)
                            avg_win_rate = data.get('avg_win_rate', 0)
                            assets_optimized = data.get('assets_optimized', [])
                            print(f"   ✅ Learning: {total_optimizations} optimizations, {avg_win_rate:.1f}% avg win rate, {len(assets_optimized)} assets")
                        
                        # Specific validation for spread-analysis
                        elif endpoint == "ai/spread-analysis":
                            if isinstance(data, list):
                                print(f"   ✅ Spread analysis: {len(data)} entries")
                            else:
                                print(f"   ✅ Spread analysis: data structure returned")
                        
                        # Specific validation for pillar-efficiency
                        elif endpoint.startswith("ai/pillar-efficiency"):
                            if isinstance(data, dict) and len(data) >= 4:
                                pillars = list(data.keys())
                                print(f"   ✅ Pillar efficiency: {len(pillars)} pillars - {pillars}")
                            else:
                                print(f"   ✅ Pillar efficiency: response received")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 0.8:  # At least 80% should work
                print(f"   ✅ AI routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ AI routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   AI routes test error: {e}")
            return False

    def test_v31_system_routes_all(self):
        """Test V3.1.0: All System Routes (/api/system/...)"""
        try:
            endpoints_to_test = [
                ("system/info", "System Info - should show version 3.1.0"),
                ("system/health", "System Health - health check"),
                ("system/memory", "System Memory - memory stats")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for system/info
                        if endpoint == "system/info":
                            version = data.get('version', 'unknown')
                            features = data.get('features', {})
                            platform = data.get('platform', 'unknown')
                            print(f"   ✅ System: version={version}, platform={platform}, {len(features)} features")
                            
                            # Check for V3.1.0 features
                            expected_features = ['spread_adjustment', 'bayesian_learning', '4_pillar_engine']
                            found_features = [f for f in expected_features if features.get(f)]
                            print(f"   ✅ V3.1.0 features: {found_features}")
                        
                        # Specific validation for system/health
                        elif endpoint == "system/health":
                            status = data.get('status', 'unknown')
                            components = data.get('components', {})
                            print(f"   ✅ Health: {status}, {len(components)} components checked")
                        
                        # Specific validation for system/memory
                        elif endpoint == "system/memory":
                            rss_mb = data.get('rss_mb', 0)
                            percent = data.get('percent', 0)
                            print(f"   ✅ Memory: {rss_mb:.1f}MB ({percent:.1f}%)")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 1.0:  # All should work
                print(f"   ✅ System routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ System routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   System routes test error: {e}")
            return False

    def test_v31_reporting_routes_all(self):
        """Test V3.1.0: All Reporting Routes (/api/reporting/...)"""
        try:
            endpoints_to_test = [
                ("reporting/status", "Reporting Status - automated reporting"),
                ("reporting/schedule", "Reporting Schedule - report timing")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test)
            
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for reporting/status
                        if endpoint == "reporting/status":
                            available = data.get('available', False)
                            status = data.get('status', 'unknown')
                            print(f"   ✅ Reporting: available={available}, status={status}")
                        
                        # Specific validation for reporting/schedule
                        elif endpoint == "reporting/schedule":
                            schedule = data.get('schedule', {})
                            timezone = data.get('timezone', 'unknown')
                            print(f"   ✅ Schedule: {len(schedule)} entries, timezone={timezone}")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 1.0:  # All should work
                print(f"   ✅ Reporting routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ Reporting routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   Reporting routes test error: {e}")
            return False

    def test_v31_imessage_routes_all(self):
        """Test V3.1.0: All iMessage Routes (/api/imessage/...)"""
        try:
            endpoints_to_test = [
                ("imessage/status", "iMessage Status - bridge status"),
                ("imessage/restart/status", "iMessage Restart Status - restart capability")
            ]
            
            # POST endpoints to test
            post_endpoints = [
                ("imessage/command?text=Status", "iMessage Command Status")
            ]
            
            working_endpoints = 0
            total_endpoints = len(endpoints_to_test) + len(post_endpoints)
            
            # Test GET endpoints
            for endpoint, description in endpoints_to_test:
                try:
                    success, data = self.test_api_endpoint(endpoint)
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for imessage/status
                        if endpoint == "imessage/status":
                            available = data.get('available', False)
                            print(f"   ✅ iMessage: available={available}")
                        
                        # Specific validation for imessage/restart/status
                        elif endpoint == "imessage/restart/status":
                            platform = data.get('platform', 'unknown')
                            can_restart = data.get('can_restart', False)
                            print(f"   ✅ Restart: platform={platform}, can_restart={can_restart}")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            # Test POST endpoints
            for endpoint, description in post_endpoints:
                try:
                    success, data = self.test_api_endpoint(endpoint, method='POST')
                    if success:
                        working_endpoints += 1
                        print(f"   ✅ {description}")
                        
                        # Specific validation for command
                        if "command" in endpoint:
                            action = data.get('action', 'unknown')
                            response = data.get('response', '')
                            print(f"   ✅ Command: action={action}, response_length={len(response)}")
                            
                    else:
                        print(f"   ❌ {description} - Failed")
                except Exception as e:
                    print(f"   ❌ {description} - Error: {e}")
            
            success_rate = working_endpoints / total_endpoints
            if success_rate >= 0.8:  # At least 80% should work
                print(f"   ✅ iMessage routes: {working_endpoints}/{total_endpoints} working")
                return True
            else:
                print(f"   ❌ iMessage routes: {working_endpoints}/{total_endpoints} working")
                return False
                
        except Exception as e:
            print(f"   iMessage routes test error: {e}")
            return False


async def main():
    """Main test runner for V3.1.0 Modular Routes Testing"""
    print("🧪 Booner Trade V3.1.0 - Vollständige Modularisierung Testing")
    print("=" * 80)
    
    # Get backend URL from frontend .env
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    backend_url = line.split('=', 1)[1].strip()
                    break
            else:
                backend_url = "https://tradecore-fix.preview.emergentagent.com"
    except:
        backend_url = "https://tradecore-fix.preview.emergentagent.com"
    
    print(f"🔗 Backend URL: {backend_url}")
    print()
    
    tester = V31ModularTester(backend_url)
    
    # V3.1.0 Modular Routes Testing - Complete Regression Test
    print("🔍 V3.1.0 MODULAR ROUTES TESTING")
    print("-" * 50)
    
    # 1. Market Routes (/api/market/...)
    tester.run_test(
        "Market Routes - All endpoints",
        tester.test_v31_market_routes_all
    )
    
    # 2. Trade Routes (/api/trades/...)
    tester.run_test(
        "Trade Routes - All endpoints", 
        tester.test_v31_trade_routes_all
    )
    
    # 3. Platform Routes (/api/platforms/..., /api/mt5/...)
    tester.run_test(
        "Platform Routes - All endpoints",
        tester.test_v31_platform_routes_all
    )
    
    # 4. Settings Routes (/api/settings, /api/bot/..., /api/risk/...)
    tester.run_test(
        "Settings Routes - All endpoints",
        tester.test_v31_settings_routes_all
    )
    
    # 5. Signals Routes (/api/signals/...)
    tester.run_test(
        "Signals Routes - 4-Pillar Engine",
        tester.test_v31_signals_routes_all
    )
    
    # 6. AI Routes (/api/ai/...)
    tester.run_test(
        "AI Routes - Bayesian Learning & Spread Analysis",
        tester.test_v31_ai_routes_all
    )
    
    # 7. System Routes (/api/system/...)
    tester.run_test(
        "System Routes - Health & Info",
        tester.test_v31_system_routes_all
    )
    
    # 8. Reporting Routes (/api/reporting/...)
    tester.run_test(
        "Reporting Routes - Automated Reporting",
        tester.test_v31_reporting_routes_all
    )
    
    # 9. iMessage Routes (/api/imessage/...)
    tester.run_test(
        "iMessage Routes - Command Bridge",
        tester.test_v31_imessage_routes_all
    )
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 V3.1.0 MODULAR ROUTES TEST SUMMARY")
    print("=" * 80)
    
    success_rate = (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0
    
    print(f"✅ Tests Passed: {tester.tests_passed}")
    print(f"❌ Tests Failed: {len(tester.failed_tests)}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if tester.passed_tests:
        print(f"\n✅ WORKING MODULES:")
        for test in tester.passed_tests:
            print(f"   • {test}")
    
    if tester.failed_tests:
        print(f"\n❌ FAILED MODULES:")
        for test in tester.failed_tests:
            print(f"   • {test}")
    
    print("\n" + "=" * 80)
    
    # Overall assessment
    if success_rate >= 90:
        print("🎉 EXCELLENT: V3.1.0 Modularisierung vollständig funktionsfähig!")
    elif success_rate >= 80:
        print("✅ GOOD: V3.1.0 Modularisierung größtenteils funktionsfähig")
    elif success_rate >= 60:
        print("⚠️ PARTIAL: V3.1.0 Modularisierung teilweise funktionsfähig")
    else:
        print("❌ CRITICAL: V3.1.0 Modularisierung hat schwerwiegende Probleme")
    
    print("=" * 80)
    
    return success_rate >= 80


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)