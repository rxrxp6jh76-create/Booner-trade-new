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
- signals_routes.py: Signal Status, 4-Pillar Engine
- reporting_routes.py: Automated Reporting, iMessage Reports
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

# Haupt-Router für alle Sub-Module
main_router = APIRouter(prefix="/api")


def register_all_routes(api_router: APIRouter):
    """
    Registriert alle modularen Routen beim Haupt-API-Router.
    
    Args:
        api_router: Der FastAPI APIRouter, bei dem die Routen registriert werden
    """
    registered = []
    failed = []
    
    # AI Routes
    try:
        from .ai_routes import ai_router
        api_router.include_router(ai_router)
        registered.append("ai_routes")
    except ImportError as e:
        failed.append(f"ai_routes: {e}")
    
    # iMessage Routes
    try:
        from .imessage_routes import imessage_router
        api_router.include_router(imessage_router)
        registered.append("imessage_routes")
    except ImportError as e:
        failed.append(f"imessage_routes: {e}")
    
    # System Routes
    try:
        from .system_routes import system_router
        api_router.include_router(system_router)
        registered.append("system_routes")
    except ImportError as e:
        failed.append(f"system_routes: {e}")
    
    # Market Routes
    try:
        from .market_routes import market_router
        api_router.include_router(market_router)
        registered.append("market_routes")
    except ImportError as e:
        failed.append(f"market_routes: {e}")
    
    # Trade Routes
    try:
        from .trade_routes import trade_router
        api_router.include_router(trade_router)
        registered.append("trade_routes")
    except ImportError as e:
        failed.append(f"trade_routes: {e}")
    
    # Platform Routes
    try:
        from .platform_routes import platform_router
        api_router.include_router(platform_router)
        registered.append("platform_routes")
    except ImportError as e:
        failed.append(f"platform_routes: {e}")
    
    # Settings Routes
    try:
        from .settings_routes import settings_router
        api_router.include_router(settings_router)
        registered.append("settings_routes")
    except ImportError as e:
        failed.append(f"settings_routes: {e}")
    
    # Signals Routes
    try:
        from .signals_routes import signals_router
        api_router.include_router(signals_router)
        registered.append("signals_routes")
    except ImportError as e:
        failed.append(f"signals_routes: {e}")
    
    # Reporting Routes
    try:
        from .reporting_routes import reporting_router
        api_router.include_router(reporting_router)
        registered.append("reporting_routes")
    except ImportError as e:
        failed.append(f"reporting_routes: {e}")
    
    logger.info(f"✅ Modulare Routen registriert: {len(registered)}/{len(registered) + len(failed)}")
    if registered:
        logger.info(f"   Erfolgreich: {', '.join(registered)}")
    if failed:
        logger.warning(f"   Fehlgeschlagen: {', '.join(failed)}")
    
    return registered, failed


__all__ = ['main_router', 'register_all_routes']

