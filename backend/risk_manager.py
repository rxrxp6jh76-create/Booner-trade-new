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
            
            # Berechne Risiko-Prozent
            if balance > 0:
                risk_percent = ((balance - equity) / balance) * 100
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
        for name in platform_names:
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
        """
        distribution = {}
        total_balance = 0
        total_equity = 0
        total_positions = 0
        
        for name, status in self.broker_statuses.items():
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
            'broker_count': len(self.broker_statuses),
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


# Singleton Instance
risk_manager = RiskManager()


async def init_risk_manager(connector):
    """Initialisiert den Risk Manager mit dem Platform Connector"""
    global risk_manager
    risk_manager.connector = connector
    logger.info("✅ RiskManager initialized with platform connector")
    return risk_manager


__all__ = ['RiskManager', 'risk_manager', 'init_risk_manager', 'RiskAssessment', 'BrokerStatus']
