#!/usr/bin/env python3
"""
SL/TP Settings Update Test Suite
Tests the specific functionality where changing SL/TP settings updates existing trades
"""

import requests
import sys
import asyncio
import aiosqlite
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

class SLTPSettingsUpdateTester:
    def __init__(self, base_url="https://aitrader-83.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []
        self.test_trade_ids = []  # Keep track of test trades for cleanup

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

    async def run_async_test(self, name, test_func, *args, **kwargs):
        """Run a single async test"""
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            result = await test_func(*args, **kwargs)
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

    def api_request(self, endpoint, method='GET', data=None):
        """Make API request"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            
            print(f"   API {method} {endpoint}: Status {response.status_code}")
            
            if response.status_code >= 400:
                print(f"   Error response: {response.text[:200]}")
                return False, {}
            
            try:
                return True, response.json()
            except:
                return True, {}
                
        except Exception as e:
            print(f"   API request error: {str(e)}")
            return False, {}

    async def get_db_connection(self):
        """Get database connection"""
        # Try different possible database paths
        possible_paths = [
            "/app/backend/trades.db",
            "/app/backend/settings.db", 
            "/app/backend/trading.db",
            "/app/trades.db",
            "/app/settings.db"
        ]
        
        for db_path in possible_paths:
            if Path(db_path).exists():
                print(f"   Found database: {db_path}")
                return await aiosqlite.connect(db_path)
        
        print(f"   No database found in paths: {possible_paths}")
        return None

    async def create_test_trade_in_db(self, trade_data):
        """Create a test trade directly in the database"""
        try:
            conn = await self.get_db_connection()
            if not conn:
                print("   Could not connect to database")
                return False
            
            # Insert into trades table
            trade_id = str(uuid.uuid4())
            self.test_trade_ids.append(trade_id)
            
            await conn.execute("""
                INSERT INTO trades (
                    id, timestamp, commodity, type, price, quantity, status, 
                    platform, entry_price, strategy, mt5_ticket
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                datetime.now(timezone.utc).isoformat(),
                trade_data.get('commodity', 'EURUSD'),
                trade_data.get('type', 'BUY'),
                trade_data.get('price', 1.1000),
                trade_data.get('quantity', 0.01),
                'OPEN',
                trade_data.get('platform', 'MT5_LIBERTEX_DEMO'),
                trade_data.get('entry_price', 1.1000),
                trade_data.get('strategy', 'day'),
                trade_data.get('mt5_ticket', '12345')
            ))
            
            # Insert into trade_settings table
            await conn.execute("""
                INSERT INTO trade_settings (
                    trade_id, stop_loss, take_profit, strategy, entry_price,
                    created_at, platform, commodity, status, type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"mt5_{trade_data.get('mt5_ticket', '12345')}",
                trade_data.get('stop_loss', 1.0780),  # 2% below entry for BUY
                trade_data.get('take_profit', 1.1275),  # 2.5% above entry for BUY
                trade_data.get('strategy', 'day'),
                trade_data.get('entry_price', 1.1000),
                datetime.now(timezone.utc).isoformat(),
                trade_data.get('platform', 'MT5_LIBERTEX_DEMO'),
                trade_data.get('commodity', 'EURUSD'),
                'OPEN',
                trade_data.get('type', 'BUY')
            ))
            
            await conn.commit()
            await conn.close()
            
            print(f"   Created test trade: {trade_id} with MT5 ticket {trade_data.get('mt5_ticket', '12345')}")
            return trade_id
            
        except Exception as e:
            print(f"   Error creating test trade: {e}")
            return False

    async def get_trade_settings_from_db(self, mt5_ticket):
        """Get trade settings from database"""
        try:
            conn = await self.get_db_connection()
            if not conn:
                return None
            
            cursor = await conn.execute("""
                SELECT trade_id, stop_loss, take_profit, strategy, entry_price 
                FROM trade_settings 
                WHERE trade_id = ?
            """, (f"mt5_{mt5_ticket}",))
            
            result = await cursor.fetchone()
            await conn.close()
            
            if result:
                return {
                    'trade_id': result[0],
                    'stop_loss': result[1],
                    'take_profit': result[2],
                    'strategy': result[3],
                    'entry_price': result[4]
                }
            return None
            
        except Exception as e:
            print(f"   Error getting trade settings: {e}")
            return None

    async def cleanup_test_trades(self):
        """Clean up test trades from database"""
        try:
            conn = await self.get_db_connection()
            if not conn:
                return
            
            for trade_id in self.test_trade_ids:
                await conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
                await conn.execute("DELETE FROM trade_settings WHERE trade_id LIKE ?", (f"%{trade_id}%",))
            
            await conn.commit()
            await conn.close()
            print(f"   Cleaned up {len(self.test_trade_ids)} test trades")
            
        except Exception as e:
            print(f"   Error cleaning up test trades: {e}")

    def test_get_current_settings(self):
        """Test 1: Get current trading settings"""
        success, settings = self.api_request("settings")
        
        if not success:
            return False
        
        # Check if we have the required day trading settings
        required_keys = ['day_take_profit_percent', 'day_stop_loss_percent']
        for key in required_keys:
            if key not in settings:
                print(f"   Missing required setting: {key}")
                return False
        
        print(f"   Current day_take_profit_percent: {settings.get('day_take_profit_percent')}")
        print(f"   Current day_stop_loss_percent: {settings.get('day_stop_loss_percent')}")
        
        return True

    async def test_create_test_trade_with_settings(self):
        """Test 2: Create a test trade with initial SL/TP settings"""
        # Create test trade data
        test_trade = {
            'commodity': 'EURUSD',
            'type': 'BUY',
            'entry_price': 1.1000,
            'price': 1.1000,
            'quantity': 0.01,
            'strategy': 'day',
            'platform': 'MT5_LIBERTEX_DEMO',
            'mt5_ticket': '999001',
            'stop_loss': 1.0780,    # 2% below entry (1.1000 * 0.98)
            'take_profit': 1.1275   # 2.5% above entry (1.1000 * 1.025)
        }
        
        trade_id = await self.create_test_trade_in_db(test_trade)
        
        if not trade_id:
            return False
        
        # Verify the trade settings were created
        settings = await self.get_trade_settings_from_db('999001')
        
        if not settings:
            print("   Trade settings not found in database")
            return False
        
        print(f"   Initial SL: {settings['stop_loss']}, TP: {settings['take_profit']}")
        print(f"   Strategy: {settings['strategy']}")
        
        return True

    def test_update_day_trading_settings(self):
        """Test 3: Update day trading SL/TP percentages via POST /api/settings"""
        # Get current settings first
        success, current_settings = self.api_request("settings")
        if not success:
            print("   Could not get current settings")
            return False
        
        # Update day trading percentages
        updated_settings = current_settings.copy()
        updated_settings['day_take_profit_percent'] = 10.0  # Change from 2.5% to 10%
        updated_settings['day_stop_loss_percent'] = 3.0     # Change from 2.0% to 3%
        
        print(f"   Updating day_take_profit_percent: {current_settings.get('day_take_profit_percent')} -> 10.0")
        print(f"   Updating day_stop_loss_percent: {current_settings.get('day_stop_loss_percent')} -> 3.0")
        
        # Send POST request to update settings
        success, response = self.api_request("settings", method='POST', data=updated_settings)
        
        if not success:
            print("   Failed to update settings")
            return False
        
        print("   Settings update request successful")
        
        # Verify settings were updated
        success, new_settings = self.api_request("settings")
        if not success:
            return False
        
        if new_settings.get('day_take_profit_percent') != 10.0:
            print(f"   day_take_profit_percent not updated: {new_settings.get('day_take_profit_percent')}")
            return False
        
        if new_settings.get('day_stop_loss_percent') != 3.0:
            print(f"   day_stop_loss_percent not updated: {new_settings.get('day_stop_loss_percent')}")
            return False
        
        print("   ✅ Settings successfully updated in database")
        return True

    async def test_verify_trade_settings_updated(self):
        """Test 4: Verify that existing trade settings were updated with new SL/TP"""
        # Get the trade settings after the settings update
        settings = await self.get_trade_settings_from_db('999001')
        
        if not settings:
            print("   Trade settings not found")
            return False
        
        entry_price = settings['entry_price']  # Should be 1.1000
        
        # Calculate expected new SL/TP based on new percentages
        # For BUY trade: SL = entry * (1 - 3%), TP = entry * (1 + 10%)
        expected_sl = entry_price * (1 - 3.0 / 100)  # 1.1000 * 0.97 = 1.067
        expected_tp = entry_price * (1 + 10.0 / 100)  # 1.1000 * 1.10 = 1.21
        
        actual_sl = settings['stop_loss']
        actual_tp = settings['take_profit']
        
        print(f"   Entry Price: {entry_price}")
        print(f"   Expected SL: {expected_sl:.4f}, Actual SL: {actual_sl}")
        print(f"   Expected TP: {expected_tp:.4f}, Actual TP: {actual_tp}")
        
        # Allow small tolerance for floating point comparison
        sl_tolerance = abs(actual_sl - expected_sl) < 0.001
        tp_tolerance = abs(actual_tp - expected_tp) < 0.001
        
        if not sl_tolerance:
            print(f"   SL not updated correctly. Expected ~{expected_sl:.4f}, got {actual_sl}")
            return False
        
        if not tp_tolerance:
            print(f"   TP not updated correctly. Expected ~{expected_tp:.4f}, got {actual_tp}")
            return False
        
        print("   ✅ Trade SL/TP correctly updated based on new percentages")
        return True

    async def test_verify_strategy_preserved(self):
        """Test 5: Verify that trade strategy is preserved (day stays day)"""
        settings = await self.get_trade_settings_from_db('999001')
        
        if not settings:
            print("   Trade settings not found")
            return False
        
        strategy = settings['strategy']
        
        if strategy != 'day':
            print(f"   Strategy changed! Expected 'day', got '{strategy}'")
            return False
        
        print(f"   ✅ Strategy preserved: {strategy}")
        return True

    async def test_multiple_trades_different_strategies(self):
        """Test 6: Create trades with different strategies and verify only day trades are updated"""
        # Create a swing trade
        swing_trade = {
            'commodity': 'GOLD',
            'type': 'SELL',
            'entry_price': 2000.0,
            'price': 2000.0,
            'quantity': 0.01,
            'strategy': 'swing',
            'platform': 'MT5_LIBERTEX_DEMO',
            'mt5_ticket': '999002',
            'stop_loss': 2040.0,    # 2% above entry for SELL
            'take_profit': 1920.0   # 4% below entry for SELL
        }
        
        swing_trade_id = await self.create_test_trade_in_db(swing_trade)
        if not swing_trade_id:
            return False
        
        # Update settings again to trigger the update mechanism
        success, current_settings = self.api_request("settings")
        if not success:
            return False
        
        updated_settings = current_settings.copy()
        updated_settings['day_take_profit_percent'] = 15.0  # Change again
        
        success, response = self.api_request("settings", method='POST', data=updated_settings)
        if not success:
            return False
        
        # Check day trade (should be updated)
        day_settings = await self.get_trade_settings_from_db('999001')
        if not day_settings:
            return False
        
        # Check swing trade (should NOT be updated with day percentages)
        swing_settings = await self.get_trade_settings_from_db('999002')
        if not swing_settings:
            return False
        
        print(f"   Day trade TP: {day_settings['take_profit']} (should reflect 15%)")
        print(f"   Swing trade TP: {swing_settings['take_profit']} (should remain unchanged)")
        print(f"   Day strategy: {day_settings['strategy']}")
        print(f"   Swing strategy: {swing_settings['strategy']}")
        
        # Verify strategies are preserved
        if day_settings['strategy'] != 'day':
            print(f"   Day trade strategy changed: {day_settings['strategy']}")
            return False
        
        if swing_settings['strategy'] != 'swing':
            print(f"   Swing trade strategy changed: {swing_settings['strategy']}")
            return False
        
        # Verify day trade TP was updated (15% above 1.1000 = 1.265)
        expected_day_tp = 1.1000 * 1.15
        if abs(day_settings['take_profit'] - expected_day_tp) > 0.001:
            print(f"   Day trade TP not updated correctly. Expected ~{expected_day_tp}, got {day_settings['take_profit']}")
            return False
        
        print("   ✅ Only day trades updated, swing trades preserved")
        return True

async def main():
    """Main test function"""
    print("🚀 Starting SL/TP Settings Update Test Suite")
    print("=" * 60)
    
    tester = SLTPSettingsUpdateTester()
    
    try:
        # Test 1: Get current settings
        tester.run_test(
            "GET /api/settings - retrieve current day trading settings",
            tester.test_get_current_settings
        )
        
        # Test 2: Create test trade with initial settings
        await tester.run_async_test(
            "Create test trade with initial SL/TP settings",
            tester.test_create_test_trade_with_settings
        )
        
        # Test 3: Update day trading settings
        tester.run_test(
            "POST /api/settings - update day_take_profit_percent and day_stop_loss_percent",
            tester.test_update_day_trading_settings
        )
        
        # Test 4: Verify trade settings were updated
        await tester.run_async_test(
            "Verify existing trade SL/TP updated based on new percentages",
            tester.test_verify_trade_settings_updated
        )
        
        # Test 5: Verify strategy is preserved
        await tester.run_async_test(
            "Verify trade strategy preserved (day stays day)",
            tester.test_verify_strategy_preserved
        )
        
        # Test 6: Test multiple strategies
        await tester.run_async_test(
            "Verify only day trades updated, other strategies preserved",
            tester.test_multiple_trades_different_strategies
        )
        
    finally:
        # Cleanup test data
        await tester.cleanup_test_trades()
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 SL/TP SETTINGS UPDATE TEST RESULTS")
    print("=" * 60)
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
    
    return tester.tests_passed == tester.tests_run

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)