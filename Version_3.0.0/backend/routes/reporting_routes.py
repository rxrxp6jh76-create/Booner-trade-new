"""
📊 Booner Trade V3.1.0 - Reporting Routes

Enthält alle reporting-bezogenen API-Endpunkte:
- iMessage Reports
- Automated Reporting Status
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

reporting_router = APIRouter(prefix="/reporting", tags=["Reporting"])


@reporting_router.get("/status")
async def get_reporting_status():
    """Get automated reporting status"""
    try:
        try:
            from automated_reporting import AutomatedReporting
            reporter = AutomatedReporting()
            
            return {
                "available": True,
                "status": "active" if reporter.is_active else "inactive",
                "schedule": reporter.schedule if hasattr(reporter, 'schedule') else {},
                "last_report": reporter.last_report_time if hasattr(reporter, 'last_report_time') else None
            }
        except ImportError:
            return {
                "available": False,
                "status": "not_installed",
                "message": "Automated Reporting module not available"
            }
        
    except Exception as e:
        logger.error(f"Error getting reporting status: {e}")
        return {
            "available": False,
            "status": "error",
            "error": str(e)
        }


@reporting_router.post("/test/heartbeat")
async def test_heartbeat_report():
    """Send a test heartbeat report"""
    try:
        try:
            from automated_reporting import AutomatedReporting
            reporter = AutomatedReporting()
            
            result = await reporter.send_heartbeat()
            
            return {
                "success": result.get('success', False),
                "sent": result.get('sent', False),
                "message": result.get('message', 'Heartbeat test completed'),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except ImportError:
            return {
                "success": False,
                "sent": False,
                "message": "Automated Reporting not available (requires macOS)"
            }
        
    except Exception as e:
        logger.error(f"Error sending heartbeat: {e}")
        return {
            "success": False,
            "sent": False,
            "error": str(e)
        }


@reporting_router.post("/test/signal")
async def test_signal_report():
    """Send a test signal report"""
    try:
        try:
            from automated_reporting import AutomatedReporting
            reporter = AutomatedReporting()
            
            # Create test signal
            test_signal = {
                "commodity": "GOLD",
                "action": "BUY",
                "confidence": 75,
                "price": 2000.00,
                "test": True
            }
            
            result = await reporter.send_signal_alert(test_signal)
            
            return {
                "success": result.get('success', False),
                "sent": result.get('sent', False),
                "message": result.get('message', 'Signal test completed'),
                "signal": test_signal,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except ImportError:
            return {
                "success": False,
                "sent": False,
                "message": "Automated Reporting not available (requires macOS)"
            }
        
    except Exception as e:
        logger.error(f"Error sending signal report: {e}")
        return {
            "success": False,
            "sent": False,
            "error": str(e)
        }


@reporting_router.post("/send")
async def send_custom_report(message: str, report_type: str = "info"):
    """Send a custom report via iMessage"""
    try:
        try:
            from automated_reporting import AutomatedReporting
            reporter = AutomatedReporting()
            
            result = await reporter.send_message(message, report_type)
            
            return {
                "success": result.get('success', False),
                "sent": result.get('sent', False),
                "message_sent": message,
                "report_type": report_type
            }
        except ImportError:
            return {
                "success": False,
                "sent": False,
                "message": "Automated Reporting not available"
            }
        
    except Exception as e:
        logger.error(f"Error sending custom report: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@reporting_router.get("/schedule")
async def get_report_schedule():
    """Get the current reporting schedule"""
    try:
        try:
            from automated_reporting import AutomatedReporting
            reporter = AutomatedReporting()
            
            return {
                "schedule": reporter.schedule if hasattr(reporter, 'schedule') else {
                    "morning_report": "08:00",
                    "evening_report": "20:00",
                    "signal_alerts": "immediate",
                    "heartbeat": "every_6_hours"
                },
                "timezone": "Europe/Berlin"
            }
        except ImportError:
            return {
                "schedule": {},
                "message": "Reporting not available"
            }
        
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@reporting_router.post("/schedule/update")
async def update_report_schedule(schedule: Dict[str, str]):
    """Update the reporting schedule"""
    try:
        try:
            from automated_reporting import AutomatedReporting
            reporter = AutomatedReporting()
            
            reporter.schedule = schedule
            
            return {
                "success": True,
                "schedule": schedule,
                "message": "Schedule updated"
            }
        except ImportError:
            return {
                "success": False,
                "message": "Reporting not available"
            }
        
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export
__all__ = ['reporting_router']
