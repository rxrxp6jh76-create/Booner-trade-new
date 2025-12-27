"""
🧠 ENHANCED SELF-LEARNING SYSTEM - V2.3.39
==========================================

Lernt aus jedem Trade und verbessert die Strategie automatisch:
1. Trade-Journal mit Kontext
2. Pattern-Erkennung für Verlust-Trades
3. Automatische Blockade von Verlust-Mustern
4. Performance-Tracking pro Strategie/Asset/Session

Das System analysiert:
- Welche Strategien funktionieren wann?
- Welche Assets sind profitabel?
- Welche Tageszeiten sind am besten?
- Welche Muster führen zu Verlusten?
"""

import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


@dataclass
class TradeContext:
    """Vollständiger Kontext eines Trades für Analyse"""
    trade_id: str
    timestamp: str
    commodity: str
    strategy: str
    signal: str  # BUY/SELL
    entry_price: float
    exit_price: float = 0
    stop_loss: float = 0
    take_profit: float = 0
    lot_size: float = 0
    profit_loss: float = 0
    is_winner: bool = False
    hold_time_minutes: int = 0
    close_reason: str = ""  # SL, TP, TIME_EXIT, MANUAL
    
    # Markt-Kontext
    market_state: str = ""  # range, uptrend, etc.
    volatility: float = 0
    spread_percent: float = 0
    
    # Session-Kontext
    session: str = ""  # london, new_york, etc.
    day_of_week: int = 0
    hour_of_day: int = 0
    
    # Signal-Kontext
    confidence_score: float = 0
    mtf_confirmation: int = 0  # 0-3
    pattern_detected: str = ""
    
    # Ergebnis-Analyse
    max_profit_during_trade: float = 0
    max_loss_during_trade: float = 0
    risk_reward_actual: float = 0


class EnhancedSelfLearning:
    """
    Erweitertes Self-Learning System mit Pattern-Erkennung.
    """
    
    def __init__(self, db_path: str = "/app/backend/learning.db"):
        self.db_path = db_path
        self._init_database()
        
        # Cache für schnellen Zugriff
        self.blocked_patterns: List[Dict] = []
        self.strategy_performance: Dict[str, Dict] = {}
        self.asset_performance: Dict[str, Dict] = {}
        self.session_performance: Dict[str, Dict] = {}
        
        # Lade Cache
        self._load_cache()
    
    def _init_database(self):
        """Initialisiert die SQLite Datenbank für Lernprotokoll."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Trade Journal Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    timestamp TEXT,
                    commodity TEXT,
                    strategy TEXT,
                    signal TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    lot_size REAL,
                    profit_loss REAL,
                    is_winner INTEGER,
                    hold_time_minutes INTEGER,
                    close_reason TEXT,
                    market_state TEXT,
                    volatility REAL,
                    spread_percent REAL,
                    session TEXT,
                    day_of_week INTEGER,
                    hour_of_day INTEGER,
                    confidence_score REAL,
                    mtf_confirmation INTEGER,
                    pattern_detected TEXT,
                    max_profit REAL,
                    max_loss REAL,
                    context_json TEXT
                )
            """)
            
            # Blockierte Muster Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocked_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_key TEXT UNIQUE,
                    description TEXT,
                    loss_count INTEGER DEFAULT 0,
                    total_loss REAL DEFAULT 0,
                    blocked_since TEXT,
                    last_occurrence TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Performance Statistiken Tabelle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,  -- 'strategy', 'asset', 'session', 'hour'
                    key TEXT,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    avg_winner REAL DEFAULT 0,
                    avg_loser REAL DEFAULT 0,
                    best_trade REAL DEFAULT 0,
                    worst_trade REAL DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    max_win_streak INTEGER DEFAULT 0,
                    max_loss_streak INTEGER DEFAULT 0,
                    last_updated TEXT,
                    UNIQUE(category, key)
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("✅ Learning Database initialisiert")
            
        except Exception as e:
            logger.error(f"❌ Fehler bei DB-Initialisierung: {e}")
    
    def _load_cache(self):
        """Lädt Daten in den Cache für schnellen Zugriff."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Lade blockierte Muster
            cursor.execute("SELECT * FROM blocked_patterns WHERE is_active = 1")
            rows = cursor.fetchall()
            self.blocked_patterns = []
            for row in rows:
                self.blocked_patterns.append({
                    'pattern_type': row[1],
                    'pattern_key': row[2],
                    'description': row[3],
                    'loss_count': row[4],
                    'total_loss': row[5]
                })
            
            # Lade Performance-Statistiken
            cursor.execute("SELECT * FROM performance_stats")
            rows = cursor.fetchall()
            for row in rows:
                category, key = row[1], row[2]
                stats = {
                    'total_trades': row[3],
                    'winning_trades': row[4],
                    'total_profit': row[5],
                    'win_rate': row[4] / row[3] if row[3] > 0 else 0,
                    'avg_winner': row[6],
                    'avg_loser': row[7]
                }
                
                if category == 'strategy':
                    self.strategy_performance[key] = stats
                elif category == 'asset':
                    self.asset_performance[key] = stats
                elif category == 'session':
                    self.session_performance[key] = stats
            
            conn.close()
            logger.info(f"📚 Cache geladen: {len(self.blocked_patterns)} blockierte Muster")
            
        except Exception as e:
            logger.error(f"❌ Cache-Load Fehler: {e}")
    
    def record_trade(self, context: TradeContext):
        """
        Zeichnet einen Trade auf und analysiert ihn.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Speichere in Journal
            cursor.execute("""
                INSERT OR REPLACE INTO trade_journal
                (trade_id, timestamp, commodity, strategy, signal, entry_price, exit_price,
                 stop_loss, take_profit, lot_size, profit_loss, is_winner, hold_time_minutes,
                 close_reason, market_state, volatility, spread_percent, session, day_of_week,
                 hour_of_day, confidence_score, mtf_confirmation, pattern_detected,
                 max_profit, max_loss, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                context.trade_id, context.timestamp, context.commodity, context.strategy,
                context.signal, context.entry_price, context.exit_price, context.stop_loss,
                context.take_profit, context.lot_size, context.profit_loss, 
                1 if context.is_winner else 0, context.hold_time_minutes, context.close_reason,
                context.market_state, context.volatility, context.spread_percent,
                context.session, context.day_of_week, context.hour_of_day,
                context.confidence_score, context.mtf_confirmation, context.pattern_detected,
                context.max_profit_during_trade, context.max_loss_during_trade,
                json.dumps(asdict(context))
            ))
            
            conn.commit()
            conn.close()
            
            # Analysiere den Trade
            self._analyze_trade(context)
            
            # Update Performance-Statistiken
            self._update_performance_stats(context)
            
            logger.info(f"📝 Trade recorded: {context.trade_id} - {'✅ WIN' if context.is_winner else '❌ LOSS'}: {context.profit_loss:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Fehler beim Trade-Recording: {e}")
    
    def _analyze_trade(self, context: TradeContext):
        """
        Analysiert einen Trade und erkennt Verlust-Muster.
        """
        if context.is_winner:
            return  # Nur Verluste analysieren
        
        # Erstelle Pattern-Keys für verschiedene Kombinationen
        patterns_to_check = [
            # Strategie + Asset
            f"strategy_asset:{context.strategy}_{context.commodity}",
            # Strategie + Markt-Zustand
            f"strategy_market:{context.strategy}_{context.market_state}",
            # Strategie + Session
            f"strategy_session:{context.strategy}_{context.session}",
            # Asset + Session
            f"asset_session:{context.commodity}_{context.session}",
            # Asset + Stunde
            f"asset_hour:{context.commodity}_{context.hour_of_day}",
            # Strategie + Wochentag
            f"strategy_day:{context.strategy}_{context.day_of_week}",
        ]
        
        # Wenn Spread hoch war
        if context.spread_percent > 0.1:
            patterns_to_check.append(f"high_spread:{context.commodity}")
        
        # Wenn niedrige Konfidenz
        if context.confidence_score < 0.65:
            patterns_to_check.append(f"low_confidence:{context.strategy}")
        
        # Wenn kein MTF-Confirmation
        if context.mtf_confirmation < 2:
            patterns_to_check.append(f"no_mtf:{context.strategy}_{context.commodity}")
        
        # Registriere alle erkannten Patterns
        for pattern_key in patterns_to_check:
            self._register_loss_pattern(pattern_key, context)
    
    def _register_loss_pattern(self, pattern_key: str, context: TradeContext):
        """
        Registriert ein Verlust-Muster.
        Nach 3 Verlusten wird das Muster blockiert.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Prüfe ob Pattern schon existiert
            cursor.execute(
                "SELECT loss_count, total_loss FROM blocked_patterns WHERE pattern_key = ?",
                (pattern_key,)
            )
            row = cursor.fetchone()
            
            pattern_type = pattern_key.split(":")[0]
            
            if row:
                # Update existierendes Pattern
                new_count = row[0] + 1
                new_loss = row[1] + abs(context.profit_loss)
                
                cursor.execute("""
                    UPDATE blocked_patterns
                    SET loss_count = ?, total_loss = ?, last_occurrence = ?,
                        is_active = CASE WHEN ? >= 3 THEN 1 ELSE is_active END
                    WHERE pattern_key = ?
                """, (new_count, new_loss, context.timestamp, new_count, pattern_key))
                
                if new_count >= 3:
                    logger.warning(f"🚫 PATTERN BLOCKIERT: {pattern_key} ({new_count} Verluste, {new_loss:.2f} Verlust)")
                    
                    # Update Cache
                    self.blocked_patterns.append({
                        'pattern_type': pattern_type,
                        'pattern_key': pattern_key,
                        'loss_count': new_count,
                        'total_loss': new_loss
                    })
            else:
                # Neues Pattern
                cursor.execute("""
                    INSERT INTO blocked_patterns
                    (pattern_type, pattern_key, description, loss_count, total_loss, 
                     blocked_since, last_occurrence, is_active)
                    VALUES (?, ?, ?, 1, ?, ?, ?, 0)
                """, (
                    pattern_type, pattern_key, 
                    f"Verlust bei {pattern_key}",
                    abs(context.profit_loss),
                    context.timestamp, context.timestamp
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Pattern-Registration Fehler: {e}")
    
    def _update_performance_stats(self, context: TradeContext):
        """
        Aktualisiert die Performance-Statistiken.
        """
        categories = [
            ('strategy', context.strategy),
            ('asset', context.commodity),
            ('session', context.session),
            ('hour', str(context.hour_of_day)),
            ('day', str(context.day_of_week))
        ]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for category, key in categories:
                if not key:
                    continue
                
                cursor.execute("""
                    INSERT INTO performance_stats
                    (category, key, total_trades, winning_trades, total_profit, last_updated)
                    VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(category, key) DO UPDATE SET
                        total_trades = total_trades + 1,
                        winning_trades = winning_trades + ?,
                        total_profit = total_profit + ?,
                        best_trade = CASE WHEN ? > best_trade THEN ? ELSE best_trade END,
                        worst_trade = CASE WHEN ? < worst_trade THEN ? ELSE worst_trade END,
                        last_updated = ?
                """, (
                    category, key,
                    1 if context.is_winner else 0,
                    context.profit_loss,
                    context.timestamp,
                    1 if context.is_winner else 0,
                    context.profit_loss,
                    context.profit_loss, context.profit_loss,
                    context.profit_loss, context.profit_loss,
                    context.timestamp
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Stats-Update Fehler: {e}")
    
    def is_pattern_blocked(
        self,
        strategy: str,
        commodity: str,
        market_state: str = "",
        session: str = "",
        hour: int = -1,
        day: int = -1,
        confidence: float = 1.0,
        spread_percent: float = 0
    ) -> Tuple[bool, str]:
        """
        Prüft ob ein Trade-Muster blockiert ist.
        
        Returns:
            (is_blocked, reason)
        """
        # Generiere alle möglichen Pattern-Keys
        patterns_to_check = [
            f"strategy_asset:{strategy}_{commodity}",
            f"strategy_market:{strategy}_{market_state}",
            f"strategy_session:{strategy}_{session}",
            f"asset_session:{commodity}_{session}",
        ]
        
        if hour >= 0:
            patterns_to_check.append(f"asset_hour:{commodity}_{hour}")
        if day >= 0:
            patterns_to_check.append(f"strategy_day:{strategy}_{day}")
        if spread_percent > 0.1:
            patterns_to_check.append(f"high_spread:{commodity}")
        if confidence < 0.65:
            patterns_to_check.append(f"low_confidence:{strategy}")
        
        # Prüfe gegen blockierte Muster
        for pattern in self.blocked_patterns:
            if pattern['pattern_key'] in patterns_to_check:
                return True, f"Pattern blockiert: {pattern['pattern_key']} ({pattern['loss_count']} Verluste)"
        
        return False, "Kein blockiertes Muster"
    
    def get_best_strategy_for_context(
        self,
        commodity: str,
        market_state: str,
        session: str,
        available_strategies: List[str]
    ) -> Tuple[str, float]:
        """
        Gibt die beste Strategie für den aktuellen Kontext zurück.
        
        Returns:
            (best_strategy, expected_win_rate)
        """
        best_strategy = None
        best_score = -1
        
        for strategy in available_strategies:
            # Prüfe ob blockiert
            is_blocked, _ = self.is_pattern_blocked(strategy, commodity, market_state, session)
            if is_blocked:
                continue
            
            # Hole Performance-Daten
            stats = self.strategy_performance.get(strategy, {})
            win_rate = stats.get('win_rate', 0.5)
            total_trades = stats.get('total_trades', 0)
            
            # Score: Win-Rate gewichtet mit Anzahl Trades (mehr Daten = verlässlicher)
            confidence_weight = min(1.0, total_trades / 20)  # Max Gewicht bei 20+ Trades
            score = win_rate * (0.5 + 0.5 * confidence_weight)
            
            if score > best_score:
                best_score = score
                best_strategy = strategy
        
        if best_strategy:
            return best_strategy, best_score
        
        # Fallback: Erste nicht-blockierte Strategie
        for strategy in available_strategies:
            is_blocked, _ = self.is_pattern_blocked(strategy, commodity, market_state, session)
            if not is_blocked:
                return strategy, 0.5
        
        return None, 0
    
    def get_learning_summary(self) -> Dict:
        """
        Gibt eine Zusammenfassung des Gelernten zurück.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Gesamtstatistik
            cursor.execute("SELECT COUNT(*), SUM(is_winner), SUM(profit_loss) FROM trade_journal")
            row = cursor.fetchone()
            total_trades = row[0] or 0
            total_wins = row[1] or 0
            total_pnl = row[2] or 0
            
            # Beste und schlechteste Strategie
            cursor.execute("""
                SELECT strategy, COUNT(*) as trades, 
                       SUM(is_winner) * 100.0 / COUNT(*) as win_rate,
                       SUM(profit_loss) as pnl
                FROM trade_journal
                GROUP BY strategy
                ORDER BY win_rate DESC
            """)
            strategy_stats = cursor.fetchall()
            
            # Blockierte Muster
            cursor.execute("SELECT COUNT(*) FROM blocked_patterns WHERE is_active = 1")
            blocked_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_trades': total_trades,
                'win_rate': (total_wins / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'strategy_stats': [
                    {'strategy': s[0], 'trades': s[1], 'win_rate': s[2], 'pnl': s[3]}
                    for s in strategy_stats
                ],
                'blocked_patterns': blocked_count,
                'patterns': self.blocked_patterns[:10]  # Top 10
            }
            
        except Exception as e:
            logger.error(f"❌ Summary Fehler: {e}")
            return {}
    
    def reset_pattern(self, pattern_key: str):
        """
        Setzt ein blockiertes Muster zurück (für manuelle Intervention).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE blocked_patterns SET is_active = 0 WHERE pattern_key = ?",
                (pattern_key,)
            )
            
            conn.commit()
            conn.close()
            
            # Update Cache
            self.blocked_patterns = [p for p in self.blocked_patterns if p['pattern_key'] != pattern_key]
            
            logger.info(f"✅ Pattern zurückgesetzt: {pattern_key}")
            
        except Exception as e:
            logger.error(f"❌ Reset Fehler: {e}")


# Globale Instanz
enhanced_learning = EnhancedSelfLearning()


# Export
__all__ = ['EnhancedSelfLearning', 'TradeContext', 'enhanced_learning']
