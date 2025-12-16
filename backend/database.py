"""
SQLite Database Manager für Desktop Trading App
Ersetzt MongoDB mit einer lokalen SQLite Datenbank
"""

import sqlite3
import aiosqlite
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import os

logger = logging.getLogger(__name__)

# Datenbankpfad - NIEMALS im App-Bundle (read-only unter macOS!)
# Prüfe ob wir in einer Electron App laufen
def get_db_path():
    # 1. Prüfe Environment Variable (gesetzt von main.js)
    env_path = os.getenv('SQLITE_DB_PATH')
    if env_path:
        # Stelle sicher dass Verzeichnis existiert
        db_dir = Path(env_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Using DB path from SQLITE_DB_PATH: {env_path}")
        return env_path
    
    # 2. Fallback: Prüfe ob wir im App-Bundle sind (read-only!)
    current_path = Path(__file__).parent
    if '/Applications/' in str(current_path) or '.app/Contents/Resources' in str(current_path):
        # WIR SIND IM APP-BUNDLE! Nutze User-Verzeichnis
        # WICHTIG: Nutze den gleichen Namen wie electron-app (kleingeschrieben!)
        user_data_dir = Path.home() / 'Library' / 'Application Support' / 'booner-trade' / 'database'
        user_data_dir.mkdir(parents=True, exist_ok=True)
        db_path = user_data_dir / 'trading.db'
        logger.warning(f"⚠️  App-Bundle detected! Using user directory: {db_path}")
        return str(db_path)
    
    # 3. Development: Nutze Backend-Verzeichnis
    dev_path = str(current_path / 'trading.db')
    logger.info(f"📁 Using development DB path: {dev_path}")
    return dev_path

# WICHTIG: Nicht beim Import aufrufen, sondern lazy evaluation!
DB_PATH = None

def get_current_db_path():
    """Gibt den aktuellen DB-Pfad zurück (wird zur Laufzeit ermittelt)"""
    global DB_PATH
    if DB_PATH is None:
        DB_PATH = get_db_path()
    return DB_PATH

class Database:
    """SQLite Database Manager mit async Support"""
    
    def __init__(self, db_path: str = None):
        # Hole DB-Pfad zur Laufzeit, nicht beim Import!
        self.db_path = db_path if db_path else get_current_db_path()
        self._conn = None
        logger.info(f"🗄️  Database initialized with path: {self.db_path}")
        
    async def connect(self):
        """Verbindung zur Datenbank herstellen mit optimierten Settings"""
        try:
            self._conn = await aiosqlite.connect(
                self.db_path,
                timeout=60.0  # CRITICAL FIX V2.3.13: 60 Sekunden Timeout (statt 30)
            )
            # Enable WAL mode for better concurrency
            await self._conn.execute("PRAGMA journal_mode=WAL")
            # Enable foreign keys
            await self._conn.execute("PRAGMA foreign_keys = ON")
            # Optimize for concurrent access - CRITICAL FIX V2.3.13: 60 Sekunden!
            await self._conn.execute("PRAGMA busy_timeout = 60000")  # 60 seconds
            # Synchronous mode = NORMAL for better performance with WAL
            await self._conn.execute("PRAGMA synchronous = NORMAL")
            await self._conn.commit()
            logger.info(f"✅ SQLite verbunden (WAL mode, 60s timeout): {self.db_path}")
            return self._conn
        except Exception as e:
            logger.error(f"❌ SQLite Verbindung fehlgeschlagen: {e}")
            raise
    
    async def close(self):
        """Verbindung schließen"""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("SQLite Verbindung geschlossen")
    
    async def initialize_schema(self):
        """Erstelle alle benötigten Tabellen"""
        try:
            logger.info("Erstelle SQLite Schema...")
            
            # Trading Settings
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trading_settings (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Trades
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    commodity TEXT NOT NULL,
                    type TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL DEFAULT 1.0,
                    status TEXT DEFAULT 'OPEN',
                    platform TEXT DEFAULT 'MT5_LIBERTEX',
                    entry_price REAL NOT NULL,
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
            
            # Trade Settings
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_settings (
                    trade_id TEXT PRIMARY KEY,
                    stop_loss REAL,
                    take_profit REAL,
                    strategy TEXT,
                    created_at TEXT,
                    entry_price REAL,
                    platform TEXT,
                    commodity TEXT,
                    created_by TEXT,
                    status TEXT DEFAULT 'OPEN',
                    type TEXT
                )
            """)
            
            # Add missing columns to existing tables
            try:
                await self._conn.execute("ALTER TABLE trade_settings ADD COLUMN status TEXT DEFAULT 'OPEN'")
            except:
                pass  # Column already exists
            
            try:
                await self._conn.execute("ALTER TABLE trade_settings ADD COLUMN type TEXT")
            except:
                pass  # Column already exists
            
            # Market Data (Latest)
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
                    signal TEXT
                )
            """)
            
            # Market Data History
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    commodity_id TEXT NOT NULL,
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
                    signal TEXT
                )
            """)
            
            # API Keys
            await self._conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    metaapi_token TEXT,
                    metaapi_account_id TEXT,
                    metaapi_icmarkets_account_id TEXT,
                    bitpanda_api_key TEXT,
                    bitpanda_email TEXT,
                    finnhub_api_key TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Indexes für Performance
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_mt5_ticket ON trades(mt5_ticket)
            """)
            
            await self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_market_history_commodity ON market_data_history(commodity_id, timestamp)
            """)
            
            await self._conn.commit()
            logger.info("✅ SQLite Schema erstellt")
            
        except Exception as e:
            logger.error(f"❌ Schema-Erstellung fehlgeschlagen: {e}")
            raise


class TradingSettings:
    """Trading Settings Collection (MongoDB-kompatible API)"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def find_one(self, query: dict) -> Optional[dict]:
        """Hole Trading Settings"""
        try:
            setting_id = query.get('id', 'trading_settings')
            async with self.db._conn.execute(
                "SELECT data FROM trading_settings WHERE id = ?",
                (setting_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return None
        except Exception as e:
            logger.error(f"Error fetching settings: {e}")
            return None
    
    async def insert_one(self, data: dict):
        """Erstelle neue Settings"""
        try:
            setting_id = data.get('id', 'trading_settings')
            data_json = json.dumps(data)
            await self.db._conn.execute(
                "INSERT INTO trading_settings (id, data, updated_at) VALUES (?, ?, ?)",
                (setting_id, data_json, datetime.now(timezone.utc).isoformat())
            )
            await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error inserting settings: {e}")
            raise
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        """Update Settings with retry logic for SQLite locking"""
        import asyncio
        
        max_retries = 5
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                setting_id = query.get('id', 'trading_settings')
                
                # Get current data
                existing = await self.find_one(query)
                
                if existing:
                    # Update existing
                    if '$set' in update:
                        existing.update(update['$set'])
                    data_json = json.dumps(existing)
                    await self.db._conn.execute(
                        "UPDATE trading_settings SET data = ?, updated_at = ? WHERE id = ?",
                        (data_json, datetime.now(timezone.utc).isoformat(), setting_id)
                    )
                elif upsert:
                    # Insert new
                    new_data = update.get('$set', {})
                    new_data['id'] = setting_id
                    await self.insert_one(new_data)
                
                await self.db._conn.commit()
                break  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e).lower()
                if ("locked" in error_msg or "busy" in error_msg) and attempt < max_retries - 1:
                    logger.warning(f"Database locked, retry {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error(f"Error updating settings after {attempt + 1} attempts: {e}")
                    raise


class Trades:
    """Trades Collection (MongoDB-kompatible API)"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def find(self, query: dict = None, projection: dict = None) -> 'TradesCursor':
        """Find trades"""
        return TradesCursor(self.db, query or {}, projection)
    
    async def find_one(self, query: dict, projection: dict = None) -> Optional[dict]:
        """Find single trade"""
        cursor = await self.find(query, projection)
        results = await cursor.to_list(1)
        return results[0] if results else None
    
    async def insert_one(self, data: dict):
        """Insert new trade"""
        try:
            # Generate ID if not present
            if 'id' not in data:
                import uuid
                data['id'] = str(uuid.uuid4())
            
            # Convert datetime objects to ISO strings
            for key in ['timestamp', 'closed_at', 'opened_at']:
                if key in data and isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
            
            # Extract fields
            fields = ['id', 'timestamp', 'commodity', 'type', 'price', 'quantity', 
                     'status', 'platform', 'entry_price', 'exit_price', 'profit_loss',
                     'stop_loss', 'take_profit', 'strategy_signal', 'closed_at', 
                     'mt5_ticket', 'strategy', 'opened_at', 'opened_by', 'closed_by', 
                     'close_reason']
            
            values = [data.get(f) for f in fields]
            placeholders = ','.join(['?' for _ in fields])
            
            await self.db._conn.execute(
                f"INSERT INTO trades ({','.join(fields)}) VALUES ({placeholders})",
                values
            )
            await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error inserting trade: {e}")
            raise
    
    async def update_one(self, query: dict, update: dict):
        """Update trade"""
        try:
            # Build WHERE clause
            where_parts = []
            where_values = []
            for key, value in query.items():
                where_parts.append(f"{key} = ?")
                where_values.append(value)
            
            where_clause = " AND ".join(where_parts)
            
            # Build SET clause
            if '$set' in update:
                set_data = update['$set']
                set_parts = []
                set_values = []
                for key, value in set_data.items():
                    set_parts.append(f"{key} = ?")
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    set_values.append(value)
                
                set_clause = ", ".join(set_parts)
                
                await self.db._conn.execute(
                    f"UPDATE trades SET {set_clause} WHERE {where_clause}",
                    set_values + where_values
                )
                await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            raise
    
    async def delete_one(self, query: dict):
        """Delete trade with retry logic for SQLite locking"""
        import asyncio
        
        max_retries = 5
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                # Build WHERE clause
                where_parts = []
                where_values = []
                for key, value in query.items():
                    where_parts.append(f"{key} = ?")
                    where_values.append(value)
                
                where_clause = " AND ".join(where_parts)
                
                # Execute delete
                cursor = await self.db._conn.execute(
                    f"DELETE FROM trades WHERE {where_clause}",
                    where_values
                )
                await self.db._conn.commit()
                
                # Return result object
                class DeleteResult:
                    def __init__(self, count):
                        self.deleted_count = count
                
                return DeleteResult(cursor.rowcount)
                
            except Exception as e:
                error_msg = str(e).lower()
                if ("locked" in error_msg or "busy" in error_msg) and attempt < max_retries - 1:
                    logger.warning(f"Database locked while deleting trade, retry {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error(f"Error deleting trade after {attempt + 1} attempts: {e}")
                    raise
    
    async def count_documents(self, query: dict = None):
        """Count trades matching query"""
        try:
            if not query:
                cursor = await self.db._conn.execute("SELECT COUNT(*) FROM trades")
            else:
                where_parts = []
                where_values = []
                for key, value in query.items():
                    where_parts.append(f"{key} = ?")
                    where_values.append(value)
                
                where_clause = " AND ".join(where_parts)
                cursor = await self.db._conn.execute(
                    f"SELECT COUNT(*) FROM trades WHERE {where_clause}",
                    where_values
                )
            
            result = await cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error counting trades: {e}")
            return 0


class TradesCursor:
    """MongoDB-like cursor for trades"""
    
    def __init__(self, db: Database, query: dict, projection: dict = None):
        self.db = db
        self.query = query
        self.projection = projection
        self._sort_field = None
        self._sort_direction = None
        self._limit_value = None
    
    def sort(self, field: str, direction: int = 1):
        """Sort results"""
        self._sort_field = field
        self._sort_direction = "ASC" if direction == 1 else "DESC"
        return self
    
    def limit(self, n: int):
        """Limit results"""
        self._limit_value = n
        return self
    
    async def to_list(self, length: int = None) -> List[dict]:
        """Execute query and return list"""
        try:
            # Build WHERE clause - supports $in operator
            where_parts = []
            where_values = []
            for key, value in self.query.items():
                if isinstance(value, dict):
                    # Handle operators
                    for op, op_value in value.items():
                        if op == '$gte':
                            where_parts.append(f"{key} >= ?")
                            where_values.append(op_value.isoformat() if isinstance(op_value, datetime) else op_value)
                        elif op == '$in':
                            # Support $in operator: key IN (?, ?, ?)
                            placeholders = ','.join(['?' for _ in op_value])
                            where_parts.append(f"{key} IN ({placeholders})")
                            where_values.extend(op_value)
                else:
                    where_parts.append(f"{key} = ?")
                    where_values.append(value)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            # Build query
            sql = f"SELECT * FROM trades WHERE {where_clause}"
            
            if self._sort_field:
                sql += f" ORDER BY {self._sort_field} {self._sort_direction}"
            
            if self._limit_value:
                sql += f" LIMIT {self._limit_value}"
            elif length:
                sql += f" LIMIT {length}"
            
            async with self.db._conn.execute(sql, where_values) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return []


class TradeSettings:
    """Trade Settings Collection"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def find(self, query: dict = None) -> 'TradeSettingsCursor':
        """Find trade settings (MongoDB-like API)"""
        return TradeSettingsCursor(self.db, query or {})
    
    async def find_one(self, query: dict, projection: dict = None) -> Optional[dict]:
        """Find single trade setting"""
        try:
            trade_id = query.get('trade_id')
            if not trade_id:
                return None
            
            async with self.db._conn.execute(
                "SELECT * FROM trade_settings WHERE trade_id = ?",
                (trade_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error fetching trade settings: {e}")
            return None
    
    async def insert_one(self, data: dict):
        """Insert trade settings"""
        try:
            fields = ['trade_id', 'stop_loss', 'take_profit', 'strategy', 
                     'created_at', 'entry_price', 'platform', 'commodity', 'created_by',
                     'status', 'type']
            values = [data.get(f) for f in fields]
            placeholders = ','.join(['?' for _ in fields])
            
            await self.db._conn.execute(
                f"INSERT INTO trade_settings ({','.join(fields)}) VALUES ({placeholders})",
                values
            )
            await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error inserting trade settings: {e}")
            raise
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        """Update trade settings with EXPLICIT field order to prevent swapping"""
        try:
            trade_id = query.get('trade_id')
            existing = await self.find_one(query)
            
            if existing:
                # Update with EXPLICIT field order
                set_data = update.get('$set', {})
                
                # CRITICAL FIX: Define fields in EXPLICIT order to prevent confusion
                # Always process in this order: stop_loss FIRST, then take_profit
                field_order = ['stop_loss', 'take_profit', 'strategy', 'entry_price', 
                              'created_at', 'platform', 'commodity', 'created_by', 'status', 'type']
                
                set_parts = []
                set_values = []
                
                for field in field_order:
                    if field in set_data:
                        set_parts.append(f"{field} = ?")
                        set_values.append(set_data[field])
                        logger.debug(f"  UPDATE {field} = {set_data[field]}")
                
                if set_parts:
                    set_clause = ", ".join(set_parts)
                    set_values.append(trade_id)
                    
                    logger.debug(f"UPDATE SQL: UPDATE trade_settings SET {set_clause} WHERE trade_id = {trade_id}")
                    
                    await self.db._conn.execute(
                        f"UPDATE trade_settings SET {set_clause} WHERE trade_id = ?",
                        set_values
                    )
            elif upsert:
                # Insert with explicit field order
                new_data = update.get('$set', {})
                new_data['trade_id'] = trade_id
                await self.insert_one(new_data)
            
            await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error updating trade settings: {e}")
            raise


class TradeSettingsCursor:
    """MongoDB-like cursor for trade settings"""
    
    def __init__(self, db: Database, query: dict):
        self.db = db
        self.query = query
        self._sort_field = None
        self._sort_direction = "ASC"
        self._limit_value = None
    
    def sort(self, field: str, direction: int = 1):
        """Sort results"""
        self._sort_field = field
        self._sort_direction = "ASC" if direction == 1 else "DESC"
        return self
    
    def limit(self, n: int):
        """Limit results"""
        self._limit_value = n
        return self
    
    async def to_list(self, length: int = None) -> List[dict]:
        """Execute query and return list - supports $in operator"""
        try:
            # Build WHERE clause
            where_parts = []
            where_values = []
            for key, value in self.query.items():
                if isinstance(value, dict):
                    # Handle operators
                    for op, op_value in value.items():
                        if op == '$gte':
                            where_parts.append(f"{key} >= ?")
                            where_values.append(op_value.isoformat() if isinstance(op_value, datetime) else op_value)
                        elif op == '$in':
                            # Support $in operator: key IN (?, ?, ?)
                            placeholders = ','.join(['?' for _ in op_value])
                            where_parts.append(f"{key} IN ({placeholders})")
                            where_values.extend(op_value)
                else:
                    where_parts.append(f"{key} = ?")
                    where_values.append(value)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            # Build query
            sql = f"SELECT * FROM trade_settings WHERE {where_clause}"
            
            if self._sort_field:
                sql += f" ORDER BY {self._sort_field} {self._sort_direction}"
            
            if self._limit_value:
                sql += f" LIMIT {self._limit_value}"
            elif length:
                sql += f" LIMIT {length}"
            
            async with self.db._conn.execute(sql, where_values) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error executing trade settings query: {e}")
            return []


class MarketData:
    """Market Data Collection"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def find_one(self, query: dict, projection: dict = None, sort: list = None) -> Optional[dict]:
        """Find market data"""
        try:
            commodity = query.get('commodity')
            if not commodity:
                return None
            
            sql = "SELECT * FROM market_data WHERE commodity = ?"
            
            async with self.db._conn.execute(sql, (commodity,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    async def find(self, query: dict = None) -> 'MarketDataCursor':
        """Find multiple market data"""
        return MarketDataCursor(self.db, query or {})
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        """Update market data"""
        try:
            commodity = query.get('commodity')
            set_data = update.get('$set', {})
            
            existing = await self.find_one(query)
            
            if existing:
                # Update
                set_parts = []
                set_values = []
                for key, value in set_data.items():
                    set_parts.append(f"{key} = ?")
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    set_values.append(value)
                
                set_clause = ", ".join(set_parts)
                set_values.append(commodity)
                
                await self.db._conn.execute(
                    f"UPDATE market_data SET {set_clause} WHERE commodity = ?",
                    set_values
                )
            elif upsert:
                # Insert
                fields = ['commodity', 'timestamp', 'price', 'volume', 'sma_20', 'ema_20',
                         'rsi', 'macd', 'macd_signal', 'macd_histogram', 'trend', 'signal']
                values = [set_data.get(f) for f in fields]
                
                # Convert datetime
                if isinstance(values[1], datetime):
                    values[1] = values[1].isoformat()
                
                placeholders = ','.join(['?' for _ in fields])
                
                await self.db._conn.execute(
                    f"INSERT INTO market_data ({','.join(fields)}) VALUES ({placeholders})",
                    values
                )
            
            await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error updating market data: {e}")
            raise


class MarketDataCursor:
    """Cursor for market data"""
    
    def __init__(self, db: Database, query: dict):
        self.db = db
        self.query = query
    
    async def to_list(self, length: int = None) -> List[dict]:
        """Execute and return list"""
        try:
            sql = "SELECT * FROM market_data"
            if length:
                sql += f" LIMIT {length}"
            
            async with self.db._conn.execute(sql) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error executing market data query: {e}")
            return []


class Stats:
    """Stats Collection for trading statistics"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def update_one(self, query: dict, update: dict, upsert: bool = False):
        """Update or insert stats"""
        import asyncio
        
        max_retries = 5
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                set_data = update.get('$set', {})
                
                # Check if stats exist
                async with self.db._conn.execute("SELECT COUNT(*) FROM stats") as cursor:
                    result = await cursor.fetchone()
                    exists = result[0] > 0 if result else False
                
                if exists:
                    # Update existing
                    set_parts = []
                    set_values = []
                    for key, value in set_data.items():
                        set_parts.append(f"{key} = ?")
                        set_values.append(value)
                    
                    if set_parts:
                        set_clause = ", ".join(set_parts)
                        await self.db._conn.execute(f"UPDATE stats SET {set_clause}", set_values)
                elif upsert:
                    # Insert new
                    fields = ['open_positions', 'closed_positions', 'total_profit_loss', 'total_trades']
                    values = [set_data.get(f, 0) for f in fields]
                    placeholders = ','.join(['?' for _ in fields])
                    await self.db._conn.execute(
                        f"INSERT INTO stats ({','.join(fields)}) VALUES ({placeholders})",
                        values
                    )
                
                await self.db._conn.commit()
                break
                
            except Exception as e:
                error_msg = str(e).lower()
                if ("locked" in error_msg or "busy" in error_msg) and attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    logger.error(f"Error updating stats: {e}")
                    raise


class MarketDataHistory:
    """Market Data History Collection"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def insert_one(self, data: dict):
        """Insert history entry"""
        try:
            fields = ['commodity_id', 'timestamp', 'price', 'volume', 'sma_20', 'ema_20',
                     'rsi', 'macd', 'macd_signal', 'macd_histogram', 'trend', 'signal']
            values = [data.get(f) for f in fields]
            
            # Convert datetime
            if isinstance(values[1], datetime):
                values[1] = values[1].isoformat()
            
            placeholders = ','.join(['?' for _ in fields])
            
            await self.db._conn.execute(
                f"INSERT INTO market_data_history ({','.join(fields)}) VALUES ({placeholders})",
                values
            )
            await self.db._conn.commit()
        except Exception as e:
            logger.error(f"Error inserting market data history: {e}")
            raise
    
    async def find(self, query: dict) -> 'MarketDataHistoryCursor':
        """Find history entries"""
        return MarketDataHistoryCursor(self.db, query)


class MarketDataHistoryCursor:
    """Cursor for market data history"""
    
    def __init__(self, db: Database, query: dict):
        self.db = db
        self.query = query
        self._sort_field = None
        self._sort_direction = "ASC"
    
    def sort(self, field: str, direction: int = 1):
        """Sort results"""
        self._sort_field = field
        self._sort_direction = "ASC" if direction == 1 else "DESC"
        return self
    
    async def to_list(self, length: int = None) -> List[dict]:
        """Execute and return list"""
        try:
            # Build WHERE
            where_parts = []
            where_values = []
            
            for key, value in self.query.items():
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        if op == '$gte':
                            where_parts.append(f"{key} >= ?")
                            if isinstance(op_value, datetime):
                                op_value = op_value.isoformat()
                            where_values.append(op_value)
                else:
                    where_parts.append(f"{key} = ?")
                    where_values.append(value)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            sql = f"SELECT * FROM market_data_history WHERE {where_clause}"
            
            if self._sort_field:
                sql += f" ORDER BY {self._sort_field} {self._sort_direction}"
            
            if length:
                sql += f" LIMIT {length}"
            
            async with self.db._conn.execute(sql, where_values) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error executing history query: {e}")
            return []


# Global database instance
_db = Database()

# MongoDB-kompatible Collections
trading_settings = TradingSettings(_db)
trades = Trades(_db)
trade_settings = TradeSettings(_db)
stats = Stats(_db)
market_data = MarketData(_db)
market_data_history = MarketDataHistory(_db)


async def init_database():
    """Initialize database connection and schema"""
    await _db.connect()
    await _db.initialize_schema()
    logger.info("✅ Database initialized")


async def close_database():
    """Close database connection"""
    await _db.close()
