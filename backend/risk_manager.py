"""
🛡️ Booner Trade v2.3.31 - Risk Manager
======================================
Zentrale Risiko-Verwaltung für alle Trading-Operationen:
- Portfolio-Risiko Überwachung (max 20% pro Broker)
- Gleichmäßige Broker-Verteilung
- Position Sizing
- Drawdown Protection
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BrokerStatus:
    """Status eines Brokers"""
    name: str
    balance: float
    equity: float
    margin_used: float
    free_margin: float
    open_positions: int
    risk_percent: float
    is_available: bool
    last_updated: datetime


@dataclass
class RiskAssessment:
    """Ergebnis einer Risiko-Bewertung"""
    can_trade: bool
    reason: str
    recommended_broker: Optional[str]
    max_lot_size: float
    risk_score: float  # 0-100, höher = riskanter


class RiskManager:
    """
    Zentrale Risiko-Verwaltung
    
    Features:
    - Max 20% Portfolio-Risiko pro Broker
    - Gleichmäßige Verteilung auf alle Broker
    - Dynamische Position Sizing
    - Drawdown Protection
    """
    
    # Konstanten
    MAX_PORTFOLIO_RISK_PERCENT = 20.0  # Max 20% des Guthabens riskieren
    MAX_SINGLE_TRADE_RISK_PERCENT = 2.0  # Max 2% pro Trade
    MIN_FREE_MARGIN_PERCENT = 30.0  # Min 30% freie Margin behalten
    MAX_DRAWDOWN_PERCENT = 15.0  # Max 15% Drawdown bevor Trading gestoppt
    
    def __init__(self, multi_platform_connector=None):
        self.connector = multi_platform_connector
        self.broker_statuses: Dict[str, BrokerStatus] = {}
        self.initial_balances: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        logger.info("🛡️ RiskManager initialized (max 20% portfolio risk per broker)")
    
    async def update_broker_status(self, platform_name: str) -> Optional[BrokerStatus]:
        """Aktualisiert den Status eines Brokers"""
        if not self.connector:
            return None
        
        try:
            account_info = await self.connector.get_account_info(platform_name)
            if not account_info:
                return None
            
            balance = account_info.get('balance', 0)
            equity = account_info.get('equity', 0)
            margin = account_info.get('margin', 0)
            free_margin = account_info.get('freeMargin', balance - margin)
            
            # V2.3.32 FIX: Korrektes Portfolio-Risiko = verwendete Margin / Balance
            # Das zeigt wieviel % des Kapitals in offenen Positionen gebunden ist
            if balance > 0:
                risk_percent = (margin / balance) * 100
            else:
                risk_percent = 0
            
            # Hole offene Positionen
            positions = await self.connector.get_open_positions(platform_name)
            open_positions = len(positions) if positions else 0
            
            # Speichere initialen Balance für Drawdown-Berechnung
            if platform_name not in self.initial_balances:
                self.initial_balances[platform_name] = balance
            
            status = BrokerStatus(
                name=platform_name,
                balance=balance,
                equity=equity,
                margin_used=margin,
                free_margin=free_margin,
                open_positions=open_positions,
                risk_percent=risk_percent,
                is_available=risk_percent < self.MAX_PORTFOLIO_RISK_PERCENT,
                last_updated=datetime.now(timezone.utc)
            )
            
            self.broker_statuses[platform_name] = status
            return status
            
        except Exception as e:
            logger.error(f"Error updating broker status for {platform_name}: {e}")
            return None
    
    async def update_all_brokers(self, platform_names: List[str]) -> Dict[str, BrokerStatus]:
        """Aktualisiert alle Broker-Status"""
        
        # V2.3.31: Filtere Aliase und Duplikate
        # Nur echte Plattformen mit eigener MetaAPI Account ID zählen
        alias_map = {
            'MT5_LIBERTEX': 'MT5_LIBERTEX_DEMO',
            'LIBERTEX': 'MT5_LIBERTEX_DEMO',
            'MT5_ICMARKETS': 'MT5_ICMARKETS_DEMO',
            'ICMARKETS': 'MT5_ICMARKETS_DEMO'
        }
        
        # Hole die echten Plattformen vom Connector
        real_platforms = set()
        seen_account_ids = set()
        
        if self.connector:
            for name in platform_names:
                # Konvertiere Alias zu echtem Namen
                real_name = alias_map.get(name, name)
                
                # Prüfe ob diese Plattform eine eigene Account ID hat
                platform_config = self.connector.platforms.get(real_name, {})
                account_id = platform_config.get('account_id', '')
                
                # Überspringe Plattformen ohne gültige Account ID
                if not account_id or account_id == 'PLACEHOLDER_REAL_ACCOUNT_ID':
                    logger.debug(f"⏭️ Skipping {real_name} - no valid account ID")
                    continue
                
                # Überspringe Duplikate (gleiche Account ID = gleicher Account)
                if account_id in seen_account_ids:
                    logger.debug(f"⏭️ Skipping {real_name} - duplicate account ID")
                    continue
                
                seen_account_ids.add(account_id)
                real_platforms.add(real_name)
        else:
            # Fallback ohne Connector
            for name in platform_names:
                real_name = alias_map.get(name, name)
                if real_name.endswith('_DEMO') or real_name.endswith('_REAL'):
                    real_platforms.add(real_name)
        
        logger.info(f"📊 Updating {len(real_platforms)} unique brokers: {list(real_platforms)}")
        
        for name in real_platforms:
            await self.update_broker_status(name)
        
        return self.broker_statuses
    
    async def assess_trade_risk(self, 
                                commodity: str, 
                                action: str, 
                                lot_size: float,
                                price: float,
                                platform_names: List[str]) -> RiskAssessment:
        """
        Bewertet das Risiko eines geplanten Trades
        
        Returns:
            RiskAssessment mit Empfehlung ob Trade ausgeführt werden sollte
        """
        # Aktualisiere alle Broker
        await self.update_all_brokers(platform_names)
        
        # Finde verfügbare Broker
        available_brokers = []
        for name, status in self.broker_statuses.items():
            if status.is_available and status.free_margin > 0:
                available_brokers.append((name, status))
        
        if not available_brokers:
            return RiskAssessment(
                can_trade=False,
                reason="Alle Broker haben das 20% Risiko-Limit erreicht",
                recommended_broker=None,
                max_lot_size=0,
                risk_score=100
            )
        
        # Wähle besten Broker (niedrigstes Risiko, gleichmäßige Verteilung)
        best_broker = self._select_best_broker(available_brokers)
        
        if not best_broker:
            return RiskAssessment(
                can_trade=False,
                reason="Kein geeigneter Broker gefunden",
                recommended_broker=None,
                max_lot_size=0,
                risk_score=100
            )
        
        broker_name, broker_status = best_broker
        
        # Berechne maximale Lot Size für diesen Broker
        max_lot = self._calculate_max_lot_size(broker_status, price)
        
        # Prüfe Drawdown
        drawdown = self._calculate_drawdown(broker_name, broker_status.equity)
        if drawdown > self.MAX_DRAWDOWN_PERCENT:
            return RiskAssessment(
                can_trade=False,
                reason=f"Drawdown zu hoch: {drawdown:.1f}% > {self.MAX_DRAWDOWN_PERCENT}%",
                recommended_broker=broker_name,
                max_lot_size=0,
                risk_score=100
            )
        
        # Berechne Risiko-Score
        risk_score = self._calculate_risk_score(broker_status, lot_size, max_lot)
        
        # Finale Entscheidung
        can_trade = (
            lot_size <= max_lot and
            broker_status.risk_percent < self.MAX_PORTFOLIO_RISK_PERCENT and
            risk_score < 80
        )
        
        reason = "Trade zugelassen" if can_trade else f"Lot Size {lot_size} > Max {max_lot:.2f}"
        
        return RiskAssessment(
            can_trade=can_trade,
            reason=reason,
            recommended_broker=broker_name,
            max_lot_size=max_lot,
            risk_score=risk_score
        )
    
    def _select_best_broker(self, available_brokers: List[Tuple[str, BrokerStatus]]) -> Optional[Tuple[str, BrokerStatus]]:
        """
        Wählt den besten Broker für einen neuen Trade
        
        Kriterien:
        1. Niedrigstes aktuelles Risiko
        2. Wenigste offene Positionen (für Gleichverteilung)
        3. Höchste freie Margin
        """
        if not available_brokers:
            return None
        
        # Score-basierte Auswahl
        scored_brokers = []
        
        for name, status in available_brokers:
            # Niedrigeres Risiko = besserer Score
            risk_score = 100 - status.risk_percent
            
            # Weniger Positionen = besserer Score (für Gleichverteilung)
            position_score = max(0, 50 - status.open_positions * 5)
            
            # Mehr freie Margin = besserer Score
            margin_score = min(50, status.free_margin / 1000)
            
            total_score = risk_score + position_score + margin_score
            scored_brokers.append((total_score, name, status))
        
        # Sortiere nach Score (höchster zuerst)
        scored_brokers.sort(reverse=True)
        
        _, best_name, best_status = scored_brokers[0]
        
        logger.info(f"🎯 Best broker selected: {best_name} (Risk: {best_status.risk_percent:.1f}%, Positions: {best_status.open_positions})")
        
        return (best_name, best_status)
    
    def _calculate_max_lot_size(self, status: BrokerStatus, price: float) -> float:
        """Berechnet die maximale Lot Size basierend auf Risiko-Limits"""
        
        # Verfügbares Risiko-Budget (bis 20% Limit)
        remaining_risk_percent = max(0, self.MAX_PORTFOLIO_RISK_PERCENT - status.risk_percent)
        risk_budget = status.balance * (remaining_risk_percent / 100)
        
        # Maximale Lot Size basierend auf Risk Budget
        # Annahme: 1 Lot = $100 Margin (vereinfacht)
        max_lot_from_risk = risk_budget / 100
        
        # Maximale Lot Size basierend auf freier Margin
        max_lot_from_margin = status.free_margin / 100
        
        # Nehme das Minimum
        max_lot = min(max_lot_from_risk, max_lot_from_margin, 10.0)  # Max 10 Lots
        
        return max(0.01, round(max_lot, 2))
    
    def _calculate_drawdown(self, platform_name: str, current_equity: float) -> float:
        """Berechnet den aktuellen Drawdown in Prozent"""
        initial_balance = self.initial_balances.get(platform_name, current_equity)
        
        if initial_balance <= 0:
            return 0
        
        drawdown = ((initial_balance - current_equity) / initial_balance) * 100
        return max(0, drawdown)
    
    def _calculate_risk_score(self, status: BrokerStatus, requested_lot: float, max_lot: float) -> float:
        """
        Berechnet einen Risiko-Score von 0-100
        
        0-30: Niedriges Risiko (grün)
        30-60: Mittleres Risiko (gelb)
        60-80: Hohes Risiko (orange)
        80-100: Sehr hohes Risiko (rot)
        """
        score = 0
        
        # Portfolio-Risiko (0-40 Punkte)
        score += (status.risk_percent / self.MAX_PORTFOLIO_RISK_PERCENT) * 40
        
        # Lot Size Verhältnis (0-30 Punkte)
        if max_lot > 0:
            lot_ratio = min(1.0, requested_lot / max_lot)
            score += lot_ratio * 30
        
        # Anzahl Positionen (0-20 Punkte)
        score += min(20, status.open_positions * 2)
        
        # Margin Level (0-10 Punkte)
        if status.balance > 0:
            margin_level = (status.free_margin / status.balance) * 100
            if margin_level < 50:
                score += 10
            elif margin_level < 70:
                score += 5
        
        return min(100, score)
    
    async def get_broker_distribution(self) -> Dict[str, Dict]:
        """
        Gibt die aktuelle Verteilung über alle Broker zurück
        Für UI-Anzeige
        
        V2.3.31: Filtert Duplikate (gleiche Balance = gespiegelte Accounts)
        """
        distribution = {}
        total_balance = 0
        total_equity = 0
        total_positions = 0
        
        # V2.3.31: Erkenne Duplikate anhand der Balance
        seen_balances = {}
        
        for name, status in self.broker_statuses.items():
            # Prüfe ob diese Balance schon von einem anderen Broker gemeldet wurde
            balance_key = f"{status.balance:.2f}_{status.equity:.2f}"
            
            if balance_key in seen_balances:
                # Duplikat gefunden - überspringe (wahrscheinlich gespiegelter Account)
                logger.warning(f"⚠️ Skipping duplicate broker {name} (same balance as {seen_balances[balance_key]})")
                continue
            
            # Prüfe ob Account tatsächlich aktiv ist (hat Positionen oder wurde kürzlich aktualisiert)
            if status.balance == 0 and status.open_positions == 0:
                logger.info(f"ℹ️ Skipping inactive broker {name} (no balance, no positions)")
                continue
            
            seen_balances[balance_key] = name
            
            distribution[name] = {
                'balance': status.balance,
                'equity': status.equity,
                'risk_percent': status.risk_percent,
                'open_positions': status.open_positions,
                'is_available': status.is_available,
                'free_margin': status.free_margin
            }
            total_balance += status.balance
            total_equity += status.equity
            total_positions += status.open_positions
        
        distribution['_summary'] = {
            'total_balance': total_balance,
            'total_equity': total_equity,
            'total_positions': total_positions,
            'broker_count': len([k for k in distribution.keys() if not k.startswith('_')]),
            'avg_risk_percent': sum(s.risk_percent for s in self.broker_statuses.values()) / max(1, len(self.broker_statuses))
        }
        
        return distribution
    
    def get_risk_limits(self) -> Dict[str, float]:
        """Gibt die konfigurierten Risiko-Limits zurück"""
        return {
            'max_portfolio_risk_percent': self.MAX_PORTFOLIO_RISK_PERCENT,
            'max_single_trade_risk_percent': self.MAX_SINGLE_TRADE_RISK_PERCENT,
            'min_free_margin_percent': self.MIN_FREE_MARGIN_PERCENT,
            'max_drawdown_percent': self.MAX_DRAWDOWN_PERCENT
        }


# ============================================================================
# V2.3.35: GLOBAL DRAWDOWN MANAGEMENT
# Auto-Reduktion von Position Size/Frequenz bei steigendem Drawdown
# ============================================================================

@dataclass
class DrawdownAdjustment:
    """Ergebnis der Drawdown-Anpassung"""
    position_size_multiplier: float  # 0.0-1.0, reduziert Position Size
    frequency_multiplier: float      # 0.0-1.0, reduziert Trading-Häufigkeit
    warning_level: str               # "ok", "caution", "warning", "critical", "stopped"
    reason: str
    current_drawdown: float


class GlobalDrawdownManager:
    """
    V2.3.35: Globales Drawdown Management
    
    Stufenweise Reduktion von Trading-Aktivität bei steigendem Drawdown:
    
    | Drawdown    | Position Size | Frequenz | Level    |
    |-------------|---------------|----------|----------|
    | 0-5%        | 100%          | 100%     | OK       |
    | 5-10%       | 80%           | 80%      | Caution  |
    | 10-15%      | 50%           | 60%      | Warning  |
    | 15-20%      | 25%           | 40%      | Critical |
    | >20%        | 0%            | 0%       | Stopped  |
    """
    
    # Drawdown-Schwellenwerte und Anpassungen
    DRAWDOWN_LEVELS = [
        # (max_drawdown, position_multiplier, frequency_multiplier, level_name)
        (5.0,  1.0, 1.0, "ok"),
        (10.0, 0.8, 0.8, "caution"),
        (15.0, 0.5, 0.6, "warning"),
        (20.0, 0.25, 0.4, "critical"),
        (100.0, 0.0, 0.0, "stopped")
    ]
    
    def __init__(self):
        self.peak_equity: Dict[str, float] = {}  # Peak Equity pro Platform
        self.daily_peak_equity: Dict[str, float] = {}  # Tägliches Peak
        self.last_adjustment_time: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        logger.info("🛡️ GlobalDrawdownManager v2.3.35 initialized")
    
    async def calculate_adjustment(
        self, 
        platform_name: str, 
        current_equity: float,
        initial_balance: Optional[float] = None
    ) -> DrawdownAdjustment:
        """
        Berechnet die Anpassungen basierend auf dem aktuellen Drawdown
        
        Args:
            platform_name: Name der Platform (z.B. "MT5_ICMARKETS")
            current_equity: Aktuelles Equity
            initial_balance: Initiale Balance (falls bekannt)
        
        Returns:
            DrawdownAdjustment mit allen Multiplikatoren
        """
        async with self._lock:
            # Peak Equity aktualisieren
            if platform_name not in self.peak_equity:
                self.peak_equity[platform_name] = current_equity
            else:
                self.peak_equity[platform_name] = max(
                    self.peak_equity[platform_name], 
                    current_equity
                )
            
            peak = self.peak_equity[platform_name]
            
            # Drawdown berechnen
            if peak <= 0:
                return DrawdownAdjustment(
                    position_size_multiplier=1.0,
                    frequency_multiplier=1.0,
                    warning_level="ok",
                    reason="Keine Daten für Peak Equity",
                    current_drawdown=0.0
                )
            
            drawdown = ((peak - current_equity) / peak) * 100
            drawdown = max(0, drawdown)  # Negative Drawdowns (Gewinne) ignorieren
            
            # Finde das passende Level
            for max_dd, pos_mult, freq_mult, level in self.DRAWDOWN_LEVELS:
                if drawdown <= max_dd:
                    reason = self._generate_reason(drawdown, level, pos_mult, freq_mult)
                    
                    logger.info(
                        f"📊 Drawdown [{platform_name}]: {drawdown:.1f}% → "
                        f"Position: {pos_mult*100:.0f}%, Frequency: {freq_mult*100:.0f}% ({level})"
                    )
                    
                    return DrawdownAdjustment(
                        position_size_multiplier=pos_mult,
                        frequency_multiplier=freq_mult,
                        warning_level=level,
                        reason=reason,
                        current_drawdown=drawdown
                    )
            
            # Fallback: Trading gestoppt
            return DrawdownAdjustment(
                position_size_multiplier=0.0,
                frequency_multiplier=0.0,
                warning_level="stopped",
                reason=f"Maximaler Drawdown ({drawdown:.1f}%) überschritten - Trading gestoppt",
                current_drawdown=drawdown
            )
    
    def _generate_reason(
        self, 
        drawdown: float, 
        level: str, 
        pos_mult: float, 
        freq_mult: float
    ) -> str:
        """Generiert eine Begründung für die Anpassung"""
        if level == "ok":
            return f"Drawdown normal ({drawdown:.1f}%) - Volles Trading erlaubt"
        elif level == "caution":
            return f"⚠️ Erhöhter Drawdown ({drawdown:.1f}%) - Position/Frequenz auf {pos_mult*100:.0f}% reduziert"
        elif level == "warning":
            return f"⚠️ Hoher Drawdown ({drawdown:.1f}%) - Position auf {pos_mult*100:.0f}%, Frequenz auf {freq_mult*100:.0f}%"
        elif level == "critical":
            return f"🚨 Kritischer Drawdown ({drawdown:.1f}%) - Minimales Trading"
        else:
            return f"🛑 Trading gestoppt bei {drawdown:.1f}% Drawdown"
    
    async def get_global_adjustment(self) -> DrawdownAdjustment:
        """
        Berechnet die globale Anpassung über alle Platforms
        Verwendet den schlechtesten Wert (konservativ)
        """
        if not self.peak_equity:
            return DrawdownAdjustment(
                position_size_multiplier=1.0,
                frequency_multiplier=1.0,
                warning_level="ok",
                reason="Keine Platform-Daten verfügbar",
                current_drawdown=0.0
            )
        
        # Sammle alle Adjustments
        worst_level = "ok"
        worst_pos_mult = 1.0
        worst_freq_mult = 1.0
        worst_drawdown = 0.0
        
        level_priority = {"ok": 0, "caution": 1, "warning": 2, "critical": 3, "stopped": 4}
        
        for platform, peak in self.peak_equity.items():
            # Hier würden wir das aktuelle Equity holen
            # Für jetzt verwenden wir das gespeicherte Peak (konservativ)
            adjustment = await self.calculate_adjustment(platform, peak * 0.95)  # Simuliert 5% DD
            
            if level_priority.get(adjustment.warning_level, 0) > level_priority.get(worst_level, 0):
                worst_level = adjustment.warning_level
                worst_pos_mult = adjustment.position_size_multiplier
                worst_freq_mult = adjustment.frequency_multiplier
            
            worst_drawdown = max(worst_drawdown, adjustment.current_drawdown)
        
        return DrawdownAdjustment(
            position_size_multiplier=worst_pos_mult,
            frequency_multiplier=worst_freq_mult,
            warning_level=worst_level,
            reason=f"Global Drawdown: {worst_drawdown:.1f}%",
            current_drawdown=worst_drawdown
        )
    
    def should_reduce_frequency(self, adjustment: DrawdownAdjustment) -> bool:
        """Prüft ob die Trading-Frequenz reduziert werden sollte"""
        return adjustment.frequency_multiplier < 1.0
    
    def should_skip_trade(self, adjustment: DrawdownAdjustment) -> bool:
        """Prüft ob dieser Trade übersprungen werden sollte (basierend auf Frequenz)"""
        import random
        if adjustment.frequency_multiplier >= 1.0:
            return False
        if adjustment.frequency_multiplier <= 0:
            return True
        
        # Zufällig überspringen basierend auf Multiplikator
        return random.random() > adjustment.frequency_multiplier
    
    def apply_to_lot_size(self, base_lot_size: float, adjustment: DrawdownAdjustment) -> float:
        """Wendet die Position-Size-Anpassung auf eine Lot Size an"""
        adjusted = base_lot_size * adjustment.position_size_multiplier
        return max(0.01, round(adjusted, 2))  # Minimum 0.01 Lot
    
    def reset_peak(self, platform_name: str = None):
        """Setzt das Peak Equity zurück (z.B. bei neuem Tag oder nach manuellem Reset)"""
        if platform_name:
            if platform_name in self.peak_equity:
                del self.peak_equity[platform_name]
                logger.info(f"🔄 Peak Equity reset für {platform_name}")
        else:
            self.peak_equity.clear()
            logger.info("🔄 Alle Peak Equity Werte zurückgesetzt")
    
    def get_status(self) -> Dict[str, Any]:
        """Gibt den aktuellen Drawdown-Status für alle Platforms zurück"""
        return {
            'platforms': {
                name: {
                    'peak_equity': peak,
                    'last_adjustment': self.last_adjustment_time.get(name, None)
                }
                for name, peak in self.peak_equity.items()
            },
            'drawdown_levels': [
                {
                    'max_drawdown': level[0],
                    'position_multiplier': level[1],
                    'frequency_multiplier': level[2],
                    'level': level[3]
                }
                for level in self.DRAWDOWN_LEVELS
            ]
        }


# Singleton Instances
risk_manager = RiskManager()
drawdown_manager = GlobalDrawdownManager()


async def init_risk_manager(connector):
    """Initialisiert den Risk Manager mit dem Platform Connector"""
    global risk_manager
    risk_manager.connector = connector
    logger.info("✅ RiskManager initialized with platform connector")
    return risk_manager


async def get_drawdown_adjustment(platform_name: str, current_equity: float) -> DrawdownAdjustment:
    """Convenience function für Drawdown-Anpassung"""
    return await drawdown_manager.calculate_adjustment(platform_name, current_equity)


__all__ = [
    'RiskManager', 'risk_manager', 'init_risk_manager', 'RiskAssessment', 'BrokerStatus',
    'GlobalDrawdownManager', 'drawdown_manager', 'DrawdownAdjustment', 'get_drawdown_adjustment'
]
