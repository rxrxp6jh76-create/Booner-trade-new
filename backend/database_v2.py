"""
🚀 Booner Trade v2.3.31 - Multi-Database Architecture
=====================================================
Separate Datenbanken für bessere Performance und keine Lock-Konflikte:
- settings.db: Trading Settings, API Keys (selten geschrieben)
- trades.db: Trades, Trade Settings (mittel häufig)
- market_data.db: Marktdaten, Historische Daten (sehr häufig)
"""

import sqlite3
import aiosqlite
import json
import logging
import asyncio
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE PATH MANAGEMENT
# ============================================================================

def get_db_directory():
    """Ermittelt das Datenbank-Verzeichnis basierend auf Umgebung"""
    
    # 1. Environment Variable (von Electron gesetzt)
    env_path = os.getenv('SQLITE_DB_PATH')
    if env_path:
        db_dir = Path(env_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ DB directory from env: {db_dir}")
        return db_dir
    
    # 2. App-Bundle (macOS)
    current_path = Path(__file__).parent
    if '/Applications/' in str(current_path) or '.app/Contents/Resources' in str(current_path):
        user_data_dir = Path.home() / 'Library' / 'Application Support' / 'booner-trade' / 'database'
        user_data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ App-Bundle DB directory: {user_data_dir}")
        return user_data_dir
    
    # 3. Development
    dev_dir = current_path
    logger.info(f"✅ Development DB directory: {dev_dir}")
    return dev_dir


# Global DB directory
_DB_DIR = None

def get_db_dir():
    global _DB_DIR
    if _DB_DIR is None:
        _DB_DIR = get_db_directory()
    return _DB_DIR


# ============================================================================
# BASE DATABASE CLASS WITH RETRY LOGIC
# ============================================================================

class BaseDatabase:
    """Basis-Klasse für alle Datenbanken mit Retry-Logik"""
    
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.db_path = str(get_db_dir() / db_name)
        self._conn = None
        self._lock = asyncio.Lock()
        logger.info(f"🗄️  {db_name} initialized: {self.db_path}")
    
    async def connect(self):
        """Verbindung mit optimierten Settings herstellen"""
        try:
            self._conn = await aiosqlite.connect(
                self.db_path,
                timeout=60.0,
                isolation_level=None  # Autocommit für bessere Concurrency
            )
            # Optimierte PRAGMA Settings
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA foreign_keys=ON")
            await self._conn.execute("PRAGMA busy_timeout=60000")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
            await self._conn.execute("PRAGMA cache_size=-32000")  # 32MB Cache
            await self._conn.execute("PRAGMA temp_store=MEMORY")
            await self._conn.commit()
            logger.info(f"✅ {self.db_name} connected (WAL mode)")
            return self._conn
        except Exception as e:
            logger.error(f"❌ {self.db_name} connection failed: {e}")
            raise
    
    async def close(self):
        """Verbindung schließen"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info(f"🔒 {self.db_name} closed")
    
    async def execute_with_retry(self, query: str, params: tuple = None, max_retries: int = 5):
        """Execute mit Retry-Logik für Lock-Fehler"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self._lock:
                    if params:
                        result = await self._conn.execute(query, params)
                    else:
                        result = await self._conn.execute(query)
                    await self._conn.commit()
                    return result
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    last_error = e
                    wait_time = 0.2 * (attempt + 1)
                    logger.warning(f"⚠️ {self.db_name} locked (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    raise
        
        logger.error(f"❌ {self.db_name} still locked after {max_retries} attempts")
        raise last_error


# ============================================================================
# SETTINGS DATABASE (settings.db)
# ============================================================================

class SettingsDatabase(BaseDatabase):
    """Datenbank für Trading Settings - selten geschrieben"""
    
    def __init__(self):
        super().__init__("settings.db")
    
    async def initialize_schema(self):
        """Schema für Settings erstellen"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trading_settings (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                key_encrypted TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        await self._conn.commit()
        logger.info("✅ Settings schema initialized")
    
    async def get_settings(self, setting_id: str = "trading_settings") -> Optional[dict]:
        """Trading Settings laden"""
        try:
            async with self._conn.execute(
                "SELECT data FROM trading_settings WHERE id = ?",
                (setting_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return None
    
    async def save_settings(self, data: dict, setting_id: str = "trading_settings"):
        """Trading Settings speichern mit Retry"""
        for attempt in range(5):
            try:
                async with self._lock:
                    data_json = json.dumps(data)
                    now = datetime.now(timezone.utc).isoformat()
                    
                    # Upsert
                    await self._conn.execute("""
                        INSERT INTO trading_settings (id, data, updated_at) 
                        VALUES (?, ?, ?)
                        ON CONFLICT(id) DO UPDATE SET data = ?, updated_at = ?
                    """, (setting_id, data_json, now, data_json, now))
                    
                    await self._conn.commit()
                    logger.info(f"✅ Settings saved")
                    return True
            except Exception as e:
                if "locked" in str(e).lower() and attempt < 4:
                    await asyncio.sleep(0.3 * (attempt + 1))
                else:
                    logger.error(f"Error saving settings: {e}")
                    raise
        return False


# ============================================================================
# TRADES DATABASE (trades.db)
# ============================================================================

class TradesDatabase(BaseDatabase):
    """Datenbank für Trades - mittel häufig geschrieben"""
    
    def __init__(self):
        super().__init__("trades.db")
    
    async def initialize_schema(self):
        """Schema für Trades erstellen"""
        # Trades Tabelle
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                commodity TEXT,
                type TEXT,
                price REAL,
                quantity REAL,
                status TEXT DEFAULT 'OPEN',
                platform TEXT,
                entry_price REAL,
                exit_price REAL,
                profit_loss REAL,
                stop_loss REAL,
                take_profit REAL,
                strategy_signal TEXT,
                closed_at TEXT,
                mt5_ticket TEXT,
                strategy TEXT,
                opened_at TEXT,
                opened_by TEXT,
                closed_by TEXT,
                close_reason TEXT
            )
        """)
        
        # Trade Settings Tabelle
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS trade_settings (
                trade_id TEXT PRIMARY KEY,
                stop_loss REAL,
                take_profit REAL,
                strategy TEXT,
                entry_price REAL,
                created_at TEXT,
                platform TEXT,
                commodity TEXT,
                created_by TEXT,
                status TEXT DEFAULT 'OPEN',
                type TEXT
            )
        """)
        
        # Closed Trades Tabelle
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS closed_trades (
                id TEXT PRIMARY KEY,
                original_trade_id TEXT,
                timestamp TEXT,
                commodity TEXT,
                type TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                profit_loss REAL,
                strategy TEXT,
                platform TEXT,
                closed_at TEXT,
                close_reason TEXT,
                mt5_ticket TEXT
            )
        """)
        
        # Indices für Performance
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_platform ON trades(platform)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_commodity ON trades(commodity)")
        
        # V2.3.31: Ticket-Strategy Mapping Tabelle
        # Speichert permanent die Zuordnung von MT5-Ticket zu Strategie
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS ticket_strategy_map (
                mt5_ticket TEXT PRIMARY KEY,
                strategy TEXT NOT NULL,
                commodity TEXT,
                platform TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_ticket_strategy ON ticket_strategy_map(mt5_ticket)")
        
        await self._conn.commit()
        logger.info("✅ Trades schema initialized (incl. ticket_strategy_map)")
    
    async def insert_trade(self, data: dict):
        """Neuen Trade einfügen mit Retry"""
        import uuid
        
        if 'id' not in data:
            data['id'] = str(uuid.uuid4())
        
        # DateTime zu ISO String
        for key in ['timestamp', 'closed_at', 'opened_at']:
            if key in data and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        
        fields = ['id', 'timestamp', 'commodity', 'type', 'price', 'quantity',
                  'status', 'platform', 'entry_price', 'exit_price', 'profit_loss',
                  'stop_loss', 'take_profit', 'strategy_signal', 'closed_at',
                  'mt5_ticket', 'strategy', 'opened_at', 'opened_by', 'closed_by', 'close_reason']
        
        values = [data.get(f) for f in fields]
        placeholders = ','.join(['?' for _ in fields])
        
        for attempt in range(5):
            try:
                async with self._lock:
                    await self._conn.execute(
                        f"INSERT INTO trades ({','.join(fields)}) VALUES ({placeholders})",
                        values
                    )
                    await self._conn.commit()
                    return data['id']
            except Exception as e:
                if "locked" in str(e).lower() and attempt < 4:
                    await asyncio.sleep(0.2 * (attempt + 1))
                else:
                    logger.error(f"Error inserting trade: {e}")
                    raise
    
    async def update_trade(self, trade_id: str, updates: dict):
        """Trade aktualisieren"""
        set_parts = []
        values = []
        
        for key, value in updates.items():
            set_parts.append(f"{key} = ?")
            if isinstance(value, datetime):
                value = value.isoformat()
            values.append(value)
        
        values.append(trade_id)
        
        for attempt in range(5):
            try:
                async with self._lock:
                    await self._conn.execute(
                        f"UPDATE trades SET {', '.join(set_parts)} WHERE id = ?",
                        values
                    )
                    await self._conn.commit()
                    return True
            except Exception as e:
                if "locked" in str(e).lower() and attempt < 4:
                    await asyncio.sleep(0.2 * (attempt + 1))
                else:
                    logger.error(f"Error updating trade: {e}")
                    raise
    
    async def get_trades(self, status: str = None, platform: str = None, limit: int = 1000) -> List[dict]:
        """Trades laden mit optionalen Filtern"""
        try:
            query = "SELECT * FROM trades"
            params = []
            conditions = []
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            if platform:
                conditions.append("platform = ?")
                params.append(platform)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += f" ORDER BY timestamp DESC LIMIT {limit}"
            
            async with self._conn.execute(query, params) as cursor:
                columns = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
    
    async def get_trade_by_id(self, trade_id: str) -> Optional[dict]:
        """Einzelnen Trade laden"""
        try:
            async with self._conn.execute(
                "SELECT * FROM trades WHERE id = ?", (trade_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error fetching trade: {e}")
            return None
    
    async def get_trade_by_ticket(self, ticket: str) -> Optional[dict]:
        """Trade per MT5 Ticket laden"""
        try:
            async with self._conn.execute(
                "SELECT * FROM trades WHERE mt5_ticket = ?", (ticket,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error fetching trade by ticket: {e}")
            return None
    
    async def count_open_trades(self, platform: str = None, strategy: str = None, commodity: str = None) -> int:
        """Anzahl offener Trades zählen"""
        try:
            query = "SELECT COUNT(*) FROM trades WHERE status = 'OPEN'"
            params = []
            
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            if strategy:
                query += " AND strategy = ?"
                params.append(strategy)
            if commodity:
                query += " AND commodity = ?"
                params.append(commodity)
            
            async with self._conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error counting trades: {e}")
            return 0
    
    # Trade Settings Methods
    async def get_trade_settings(self, trade_id: str) -> Optional[dict]:
        """Trade Settings laden"""
        try:
            async with self._conn.execute(
                "SELECT * FROM trade_settings WHERE trade_id = ?", (trade_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error fetching trade settings: {e}")
            return None
    
    async def save_trade_settings(self, trade_id: str, settings: dict):
        """Trade Settings speichern/aktualisieren"""
        settings['trade_id'] = trade_id
        
        fields = ['trade_id', 'stop_loss', 'take_profit', 'strategy', 'entry_price',
                  'created_at', 'platform', 'commodity', 'created_by', 'status', 'type']
        
        for attempt in range(5):
            try:
                async with self._lock:
                    # Check if exists
                    existing = await self.get_trade_settings(trade_id)
                    
                    if existing:
                        # Update
                        set_parts = []
                        values = []
                        for f in fields:
                            if f in settings and f != 'trade_id':
                                set_parts.append(f"{f} = ?")
                                values.append(settings[f])
                        values.append(trade_id)
                        
                        if set_parts:
                            await self._conn.execute(
                                f"UPDATE trade_settings SET {', '.join(set_parts)} WHERE trade_id = ?",
                                values
                            )
                    else:
                        # Insert
                        values = [settings.get(f) for f in fields]
                        placeholders = ','.join(['?' for _ in fields])
                        await self._conn.execute(
                            f"INSERT INTO trade_settings ({','.join(fields)}) VALUES ({placeholders})",
                            values
                        )
                    
                    await self._conn.commit()
                    return True
            except Exception as e:
                if "locked" in str(e).lower() and attempt < 4:
                    await asyncio.sleep(0.2 * (attempt + 1))
                else:
                    logger.error(f"Error saving trade settings: {e}")
                    raise


# ============================================================================
# MARKET DATA DATABASE (market_data.db)
# ============================================================================

class MarketDataDatabase(BaseDatabase):
    """Datenbank für Marktdaten - sehr häufig geschrieben"""
    
    def __init__(self):
        super().__init__("market_data.db")
    
    async def initialize_schema(self):
        """Schema für Marktdaten erstellen"""
        # Aktuelle Marktdaten
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                commodity TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL,
                sma_20 REAL,
                ema_20 REAL,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                macd_histogram REAL,
                trend TEXT,
                signal TEXT,
                data_source TEXT
            )
        """)
        
        # Historische Daten
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                commodity TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL,
                data_source TEXT,
                UNIQUE(commodity, timestamp)
            )
        """)
        
        # Indices
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_market_commodity ON market_data(commodity)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_history_commodity ON market_data_history(commodity)")
        await self._conn.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON market_data_history(timestamp)")
        
        await self._conn.commit()
        logger.info("✅ Market data schema initialized")
    
    async def update_market_data(self, commodity: str, data: dict):
        """Marktdaten aktualisieren (Upsert)"""
        data['commodity'] = commodity
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        fields = ['commodity', 'timestamp', 'price', 'volume', 'sma_20', 'ema_20',
                  'rsi', 'macd', 'macd_signal', 'macd_histogram', 'trend', 'signal', 'data_source']
        
        for attempt in range(3):  # Weniger Retries für häufige Updates
            try:
                async with self._lock:
                    values = [data.get(f) for f in fields]
                    placeholders = ','.join(['?' for _ in fields])
                    update_parts = ','.join([f"{f}=excluded.{f}" for f in fields if f != 'commodity'])
                    
                    await self._conn.execute(f"""
                        INSERT INTO market_data ({','.join(fields)}) VALUES ({placeholders})
                        ON CONFLICT(commodity) DO UPDATE SET {update_parts}
                    """, values)
                    
                    await self._conn.commit()
                    return True
            except Exception as e:
                if "locked" in str(e).lower() and attempt < 2:
                    await asyncio.sleep(0.1 * (attempt + 1))
                else:
                    logger.error(f"Error updating market data: {e}")
                    return False
    
    async def get_market_data(self, commodity: str = None) -> List[dict]:
        """Marktdaten laden"""
        try:
            if commodity:
                query = "SELECT * FROM market_data WHERE commodity = ?"
                params = (commodity,)
            else:
                query = "SELECT * FROM market_data"
                params = ()
            
            async with self._conn.execute(query, params) as cursor:
                columns = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return []
    
    async def add_history_entry(self, commodity: str, price: float, volume: float = None, source: str = None):
        """Historischen Datenpunkt hinzufügen"""
        try:
            async with self._lock:
                await self._conn.execute("""
                    INSERT OR IGNORE INTO market_data_history 
                    (commodity, timestamp, price, volume, data_source) VALUES (?, ?, ?, ?, ?)
                """, (commodity, datetime.now(timezone.utc).isoformat(), price, volume, source))
                await self._conn.commit()
        except Exception as e:
            logger.debug(f"Error adding history (may be duplicate): {e}")
    
    async def get_price_history(self, commodity: str, limit: int = 100) -> List[dict]:
        """Preishistorie laden"""
        try:
            async with self._conn.execute("""
                SELECT * FROM market_data_history 
                WHERE commodity = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (commodity, limit)) as cursor:
                columns = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []


# ============================================================================
# DATABASE MANAGER - Koordiniert alle 3 Datenbanken
# ============================================================================

class DatabaseManager:
    """
    V2.3.31: Multi-Database Manager
    Koordiniert alle 3 Datenbanken und bietet MongoDB-kompatible API
    """
    
    def __init__(self):
        self.settings_db = SettingsDatabase()
        self.trades_db = TradesDatabase()
        self.market_db = MarketDataDatabase()
        self._initialized = False
        logger.info("🚀 DatabaseManager v2.3.31 initialized (Multi-DB Architecture)")
    
    async def connect_all(self):
        """Alle Datenbanken verbinden"""
        await self.settings_db.connect()
        await self.trades_db.connect()
        await self.market_db.connect()
        logger.info("✅ All databases connected")
    
    async def initialize_all(self):
        """Alle Schemas initialisieren"""
        if self._initialized:
            return
        
        await self.connect_all()
        await self.settings_db.initialize_schema()
        await self.trades_db.initialize_schema()
        await self.market_db.initialize_schema()
        
        # Migration von alter DB falls vorhanden
        await self._migrate_from_old_db()
        
        self._initialized = True
        logger.info("✅ All database schemas initialized")
    
    async def close_all(self):
        """Alle Datenbanken schließen"""
        await self.settings_db.close()
        await self.trades_db.close()
        await self.market_db.close()
        logger.info("🔒 All databases closed")
    
    async def _migrate_from_old_db(self):
        """Migriere Daten von alter trading.db falls vorhanden"""
        old_db_path = get_db_dir() / "trading.db"
        
        if not old_db_path.exists():
            logger.info("ℹ️ No old database to migrate")
            return
        
        logger.info("🔄 Migrating data from old trading.db...")
        
        try:
            async with aiosqlite.connect(str(old_db_path)) as old_conn:
                # Migrate Settings
                try:
                    async with old_conn.execute("SELECT id, data, updated_at FROM trading_settings") as cursor:
                        rows = await cursor.fetchall()
                        for row in rows:
                            await self.settings_db._conn.execute(
                                "INSERT OR IGNORE INTO trading_settings (id, data, updated_at) VALUES (?, ?, ?)",
                                row
                            )
                        await self.settings_db._conn.commit()
                        logger.info(f"  ✅ Migrated {len(rows)} settings")
                except Exception as e:
                    logger.warning(f"  ⚠️ Settings migration: {e}")
                
                # Migrate Trades
                try:
                    async with old_conn.execute("SELECT * FROM trades") as cursor:
                        columns = [desc[0] for desc in cursor.description]
                        rows = await cursor.fetchall()
                        for row in rows:
                            data = dict(zip(columns, row))
                            try:
                                await self.trades_db.insert_trade(data)
                            except:
                                pass  # Already exists
                        logger.info(f"  ✅ Migrated {len(rows)} trades")
                except Exception as e:
                    logger.warning(f"  ⚠️ Trades migration: {e}")
                
                # Migrate Trade Settings
                try:
                    async with old_conn.execute("SELECT * FROM trade_settings") as cursor:
                        columns = [desc[0] for desc in cursor.description]
                        rows = await cursor.fetchall()
                        for row in rows:
                            data = dict(zip(columns, row))
                            try:
                                await self.trades_db.save_trade_settings(data.get('trade_id'), data)
                            except:
                                pass
                        logger.info(f"  ✅ Migrated {len(rows)} trade settings")
                except Exception as e:
                    logger.warning(f"  ⚠️ Trade settings migration: {e}")
                
                # Migrate Market Data
                try:
                    async with old_conn.execute("SELECT * FROM market_data") as cursor:
                        columns = [desc[0] for desc in cursor.description]
                        rows = await cursor.fetchall()
                        for row in rows:
                            data = dict(zip(columns, row))
                            await self.market_db.update_market_data(data.get('commodity'), data)
                        logger.info(f"  ✅ Migrated {len(rows)} market data entries")
                except Exception as e:
                    logger.warning(f"  ⚠️ Market data migration: {e}")
            
            # Rename old DB
            backup_path = old_db_path.with_suffix('.db.backup')
            old_db_path.rename(backup_path)
            logger.info(f"✅ Migration complete! Old DB backed up to: {backup_path}")
            
        except Exception as e:
            logger.error(f"❌ Migration error: {e}")
    
    # ========================================================================
    # MongoDB-KOMPATIBLE API (für Rückwärtskompatibilität)
    # ========================================================================
    
    @property
    def trading_settings(self):
        """MongoDB-kompatible trading_settings Collection"""
        return TradingSettingsWrapper(self.settings_db)
    
    @property
    def trades(self):
        """MongoDB-kompatible trades Collection"""
        return TradesWrapper(self.trades_db)
    
    @property
    def trade_settings(self):
        """MongoDB-kompatible trade_settings Collection"""
        return TradeSettingsWrapper(self.trades_db)
    
    @property
    def market_data(self):
        """MongoDB-kompatible market_data Collection"""
        return MarketDataWrapper(self.market_db)


# ============================================================================
# MONGODB-KOMPATIBLE WRAPPER KLASSEN
# ============================================================================

class TradingSettingsWrapper:
    """MongoDB-kompatible API für Trading Settings"""
    
    def __init__(self, db: SettingsDatabase):
        self.db = db
    
    async def find_one(self, query: dict) -> Optional[dict]:
        setting_id = query.get('id', 'trading_settings')
        return await self.db.get_settings(setting_id)
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        setting_id = query.get('id', 'trading_settings')
        existing = await self.db.get_settings(setting_id)
        
        if existing:
            if '$set' in update:
                existing.update(update['$set'])
            await self.db.save_settings(existing, setting_id)
        elif upsert:
            new_data = update.get('$set', {})
            new_data['id'] = setting_id
            await self.db.save_settings(new_data, setting_id)
    
    async def insert_one(self, data: dict):
        setting_id = data.get('id', 'trading_settings')
        await self.db.save_settings(data, setting_id)


class TradesWrapper:
    """MongoDB-kompatible API für Trades"""
    
    def __init__(self, db: TradesDatabase):
        self.db = db
    
    async def find_one(self, query: dict, projection: dict = None) -> Optional[dict]:
        if 'id' in query:
            return await self.db.get_trade_by_id(query['id'])
        elif 'mt5_ticket' in query:
            return await self.db.get_trade_by_ticket(query['mt5_ticket'])
        return None
    
    async def find(self, query: dict = None, projection: dict = None):
        return TradesCursorWrapper(self.db, query or {})
    
    async def insert_one(self, data: dict):
        return await self.db.insert_trade(data)
    
    async def update_one(self, query: dict, update: dict):
        if 'id' in query:
            if '$set' in update:
                await self.db.update_trade(query['id'], update['$set'])
    
    async def delete_one(self, query: dict):
        if 'id' in query:
            async with self.db._lock:
                await self.db._conn.execute("DELETE FROM trades WHERE id = ?", (query['id'],))
                await self.db._conn.commit()
    
    async def count_documents(self, query: dict = None) -> int:
        if not query:
            return await self.db.count_open_trades()
        return await self.db.count_open_trades(
            platform=query.get('platform'),
            strategy=query.get('strategy'),
            commodity=query.get('commodity')
        )


class TradesCursorWrapper:
    """Cursor für Trades-Abfragen"""
    
    def __init__(self, db: TradesDatabase, query: dict):
        self.db = db
        self.query = query
    
    async def to_list(self, length: int = 1000) -> List[dict]:
        return await self.db.get_trades(
            status=self.query.get('status'),
            platform=self.query.get('platform'),
            limit=length
        )


class TradeSettingsWrapper:
    """MongoDB-kompatible API für Trade Settings"""
    
    def __init__(self, db: TradesDatabase):
        self.db = db
    
    async def find_one(self, query: dict, projection: dict = None) -> Optional[dict]:
        if 'trade_id' in query:
            return await self.db.get_trade_settings(query['trade_id'])
        return None
    
    async def find(self, query: dict = None):
        return TradeSettingsCursorWrapper(self.db, query or {})
    
    async def insert_one(self, data: dict):
        trade_id = data.get('trade_id')
        if trade_id:
            await self.db.save_trade_settings(trade_id, data)
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        trade_id = query.get('trade_id')
        if trade_id and '$set' in update:
            await self.db.save_trade_settings(trade_id, update['$set'])


class TradeSettingsCursorWrapper:
    """Cursor für Trade Settings"""
    
    def __init__(self, db: TradesDatabase, query: dict):
        self.db = db
        self.query = query
    
    async def to_list(self, length: int = 1000) -> List[dict]:
        # Simplified - returns all settings
        try:
            async with self.db._conn.execute("SELECT * FROM trade_settings LIMIT ?", (length,)) as cursor:
                columns = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except:
            return []


class MarketDataWrapper:
    """MongoDB-kompatible API für Market Data"""
    
    def __init__(self, db: MarketDataDatabase):
        self.db = db
    
    async def find_one(self, query: dict, projection: dict = None, sort: list = None) -> Optional[dict]:
        if 'commodity' in query:
            data = await self.db.get_market_data(query['commodity'])
            return data[0] if data else None
        return None
    
    async def find(self, query: dict = None):
        return MarketDataCursorWrapper(self.db, query or {})
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        if 'commodity' in query and '$set' in update:
            await self.db.update_market_data(query['commodity'], update['$set'])


class MarketDataCursorWrapper:
    """Cursor für Market Data"""
    
    def __init__(self, db: MarketDataDatabase, query: dict):
        self.db = db
        self.query = query
    
    async def to_list(self, length: int = 1000) -> List[dict]:
        return await self.db.get_market_data()


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Singleton Database Manager
db_manager = DatabaseManager()

# Alias für Rückwärtskompatibilität
db = db_manager


async def init_database():
    """Initialize all databases"""
    await db_manager.initialize_all()


async def close_database():
    """Close all databases"""
    await db_manager.close_all()


# Export für andere Module
__all__ = [
    'db', 'db_manager', 'init_database', 'close_database',
    'DatabaseManager', 'SettingsDatabase', 'TradesDatabase', 'MarketDataDatabase'
]
