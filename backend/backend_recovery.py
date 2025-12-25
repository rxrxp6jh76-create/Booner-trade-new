#!/usr/bin/env python3
"""
🔄 BACKEND AUTO-RECOVERY SYSTEM für macOS
==========================================
Dieses Script sorgt dafür, dass das Backend stabil läuft und sich
automatisch erholt wenn es abstürzt.

Probleme die es löst:
1. Backend stürzt nach gewisser Laufzeit ab
2. Zombie-Prozesse blockieren Port
3. Memory Leaks durch lange Laufzeit
4. Datenbank-Locks nach Crash

Verwendung:
  python backend_recovery.py

Oder als Modul importieren:
  from backend_recovery import cleanup_and_start, health_check
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import logging
from pathlib import Path
from datetime import datetime
import sqlite3

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backend_recovery.log')
    ]
)
logger = logging.getLogger(__name__)

# Konfiguration
BACKEND_PORT = 8000
BACKEND_SCRIPT = "server.py"
DB_PATH = "trading.db"
HEALTH_CHECK_INTERVAL = 30  # Sekunden
MAX_MEMORY_MB = 500  # Max Memory bevor Neustart
MAX_RESTART_ATTEMPTS = 5
RESTART_COOLDOWN = 10  # Sekunden zwischen Neustarts


def find_processes_on_port(port: int) -> list:
    """Findet alle Prozesse die auf einem Port lauschen"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port == port:
                    processes.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes


def find_python_backend_processes() -> list:
    """Findet alle Python-Prozesse die server.py oder uvicorn ausführen"""
    processes = []
    keywords = ['server.py', 'uvicorn', 'fastapi']
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.cmdline()).lower()
            if any(kw in cmdline for kw in keywords):
                processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes


def kill_process_tree(pid: int, sig=signal.SIGTERM):
    """Beendet einen Prozess und alle seine Kindprozesse"""
    try:
        parent = psutil.Process(pid)
        children = parent.children(recursive=True)
        
        # Erst Kinder beenden
        for child in children:
            try:
                logger.info(f"  Beende Kind-Prozess: {child.pid}")
                child.send_signal(sig)
            except psutil.NoSuchProcess:
                pass
        
        # Dann Parent
        logger.info(f"  Beende Haupt-Prozess: {pid}")
        parent.send_signal(sig)
        
        # Warten
        gone, alive = psutil.wait_procs([parent] + children, timeout=5)
        
        # Falls noch am Leben, SIGKILL
        for p in alive:
            try:
                logger.warning(f"  Force-Kill: {p.pid}")
                p.kill()
            except psutil.NoSuchProcess:
                pass
                
        return True
    except psutil.NoSuchProcess:
        return True
    except Exception as e:
        logger.error(f"Fehler beim Beenden von Prozess {pid}: {e}")
        return False


def cleanup_zombie_processes():
    """Räumt alle Zombie-Prozesse und alte Backend-Instanzen auf"""
    logger.info("🧹 Räume alte Prozesse auf...")
    
    # 1. Finde Prozesse auf dem Port
    port_procs = find_processes_on_port(BACKEND_PORT)
    if port_procs:
        logger.info(f"   Gefunden: {len(port_procs)} Prozesse auf Port {BACKEND_PORT}")
        for proc in port_procs:
            kill_process_tree(proc.pid)
    
    # 2. Finde alle Backend-Prozesse
    backend_procs = find_python_backend_processes()
    if backend_procs:
        logger.info(f"   Gefunden: {len(backend_procs)} Backend-Prozesse")
        for proc in backend_procs:
            if proc.pid != os.getpid():  # Nicht uns selbst killen
                kill_process_tree(proc.pid)
    
    # 3. Warte kurz
    time.sleep(2)
    
    # 4. Prüfe ob Port frei ist
    remaining = find_processes_on_port(BACKEND_PORT)
    if remaining:
        logger.warning(f"⚠️ Port {BACKEND_PORT} noch belegt!")
        for proc in remaining:
            kill_process_tree(proc.pid, signal.SIGKILL)
        time.sleep(1)
    
    logger.info("✅ Cleanup abgeschlossen")


def cleanup_database_locks():
    """Entfernt Datenbank-Locks nach einem Crash"""
    logger.info("🔓 Prüfe Datenbank-Locks...")
    
    db_path = Path(DB_PATH)
    lock_files = [
        db_path.with_suffix('.db-journal'),
        db_path.with_suffix('.db-wal'),
        db_path.with_suffix('.db-shm')
    ]
    
    for lock_file in lock_files:
        if lock_file.exists():
            try:
                lock_file.unlink()
                logger.info(f"   Entfernt: {lock_file}")
            except Exception as e:
                logger.warning(f"   Konnte nicht entfernen: {lock_file} - {e}")
    
    # Prüfe ob DB lesbar ist
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path), timeout=5)
            conn.execute("SELECT 1")
            conn.close()
            logger.info("✅ Datenbank OK")
        except sqlite3.OperationalError as e:
            logger.error(f"❌ Datenbank-Problem: {e}")
            # Backup erstellen
            backup_path = db_path.with_suffix(f'.db.backup.{int(time.time())}')
            try:
                import shutil
                shutil.copy(db_path, backup_path)
                logger.info(f"   Backup erstellt: {backup_path}")
            except:
                pass


def check_backend_health() -> dict:
    """Prüft ob das Backend gesund ist"""
    import urllib.request
    import json
    
    result = {
        'running': False,
        'responsive': False,
        'memory_mb': 0,
        'uptime_seconds': 0,
        'error': None
    }
    
    # Finde Backend-Prozess
    backend_procs = find_processes_on_port(BACKEND_PORT)
    if not backend_procs:
        result['error'] = 'Kein Prozess auf Port gefunden'
        return result
    
    result['running'] = True
    proc = backend_procs[0]
    
    try:
        result['memory_mb'] = proc.memory_info().rss / (1024 * 1024)
        result['uptime_seconds'] = time.time() - proc.create_time()
    except:
        pass
    
    # HTTP Health Check
    try:
        url = f'http://localhost:{BACKEND_PORT}/api/ping'
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result['responsive'] = True
    except Exception as e:
        result['error'] = str(e)
    
    return result


def start_backend() -> subprocess.Popen:
    """Startet das Backend"""
    logger.info("🚀 Starte Backend...")
    
    # Umgebungsvariablen setzen
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # Backend starten
    process = subprocess.Popen(
        [sys.executable, BACKEND_SCRIPT],
        cwd=Path(__file__).parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    logger.info(f"   PID: {process.pid}")
    
    # Warte bis es responsive ist
    for i in range(30):
        time.sleep(1)
        health = check_backend_health()
        if health['responsive']:
            logger.info("✅ Backend gestartet und responsive!")
            return process
        if process.poll() is not None:
            logger.error(f"❌ Backend ist abgestürzt! Exit Code: {process.returncode}")
            return None
    
    logger.error("❌ Backend nicht responsive nach 30 Sekunden")
    return process


def cleanup_and_start():
    """Kompletter Cleanup und Neustart"""
    logger.info("=" * 60)
    logger.info("🔄 BACKEND RECOVERY GESTARTET")
    logger.info(f"   Zeit: {datetime.now()}")
    logger.info("=" * 60)
    
    cleanup_zombie_processes()
    cleanup_database_locks()
    
    process = start_backend()
    return process


def monitor_loop():
    """Haupt-Monitoring-Loop"""
    restart_count = 0
    last_restart = 0
    
    while True:
        try:
            health = check_backend_health()
            
            # Logging
            if health['responsive']:
                logger.debug(f"✅ Backend OK - Memory: {health['memory_mb']:.1f}MB, Uptime: {health['uptime_seconds']:.0f}s")
            else:
                logger.warning(f"⚠️ Backend Problem: {health['error']}")
            
            # Neustart nötig?
            needs_restart = False
            restart_reason = ""
            
            if not health['running']:
                needs_restart = True
                restart_reason = "Backend nicht gestartet"
            elif not health['responsive']:
                needs_restart = True
                restart_reason = "Backend nicht responsive"
            elif health['memory_mb'] > MAX_MEMORY_MB:
                needs_restart = True
                restart_reason = f"Memory zu hoch ({health['memory_mb']:.0f}MB > {MAX_MEMORY_MB}MB)"
            
            if needs_restart:
                # Cooldown prüfen
                if time.time() - last_restart < RESTART_COOLDOWN:
                    logger.warning(f"⏳ Warte auf Cooldown ({RESTART_COOLDOWN}s)")
                elif restart_count >= MAX_RESTART_ATTEMPTS:
                    logger.error(f"❌ Max Neustarts erreicht ({MAX_RESTART_ATTEMPTS}). Manuelle Intervention nötig!")
                    time.sleep(60)
                    restart_count = 0  # Reset nach Pause
                else:
                    logger.warning(f"🔄 Neustart nötig: {restart_reason}")
                    cleanup_and_start()
                    restart_count += 1
                    last_restart = time.time()
            else:
                # Erfolgreicher Check = Reset Counter
                if health['uptime_seconds'] > 300:  # 5 Minuten stabil
                    restart_count = 0
            
            time.sleep(HEALTH_CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Beende Monitoring...")
            break
        except Exception as e:
            logger.error(f"Monitor-Fehler: {e}")
            time.sleep(10)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Backend Recovery System')
    parser.add_argument('--cleanup', action='store_true', help='Nur Cleanup durchführen')
    parser.add_argument('--start', action='store_true', help='Cleanup + Start')
    parser.add_argument('--monitor', action='store_true', help='Kontinuierliches Monitoring')
    parser.add_argument('--health', action='store_true', help='Health Check')
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_zombie_processes()
        cleanup_database_locks()
    elif args.start:
        cleanup_and_start()
    elif args.monitor:
        cleanup_and_start()
        monitor_loop()
    elif args.health:
        health = check_backend_health()
        print(f"Running: {health['running']}")
        print(f"Responsive: {health['responsive']}")
        print(f"Memory: {health['memory_mb']:.1f} MB")
        print(f"Uptime: {health['uptime_seconds']:.0f} s")
        if health['error']:
            print(f"Error: {health['error']}")
    else:
        # Default: Start + Monitor
        print("🔄 Backend Recovery System")
        print("Optionen: --cleanup, --start, --monitor, --health")
        print()
        print("Starte mit --start für einmaligen Start")
        print("Starte mit --monitor für kontinuierliches Monitoring")
        cleanup_and_start()
