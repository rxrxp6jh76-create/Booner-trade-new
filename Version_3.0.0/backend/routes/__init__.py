"""
🚀 Booner Trade V3.1.0 - Routes Package

Dieses Package enthält alle API-Route-Module, aufgeteilt nach Funktionalität:

- market_routes.py: Marktdaten, OHLCV, Live-Ticks
- trade_routes.py: Trade-Ausführung, Schließung, Historie
- settings_routes.py: Einstellungen, Bot-Steuerung
- platform_routes.py: MT5, MetaAPI, Bitpanda Plattformen
- ai_routes.py: KI-Analyse, Bayesian Learning, Spread-Analyse
- imessage_routes.py: iMessage Bridge, Ollama Controller
- system_routes.py: Health, Memory, Cleanup
"""

from fastapi import APIRouter

# Haupt-Router für alle Sub-Module
main_router = APIRouter(prefix="/api")

# Sub-Router werden in den jeweiligen Modulen definiert
# und hier registriert

__all__ = ['main_router']
