# MetaAPI SDK - macOS ARM64 Lösung

## 🎯 Problem

MetaAPI SDK funktioniert auf Linux perfekt, aber auf macOS Desktop gab es Probleme:
- WebSocket Verbindungen brechen ab
- Event Loop Konflikte
- Permission Errors beim .metaapi Cache

## ✅ Lösung

### 1. Event Loop Policy (KRITISCH!)

**Problem:** Python asyncio hat unterschiedliche Event Loop Policies auf verschiedenen Plattformen.
**Lösung:** Explizites Setzen der Policy für macOS:

```python
import sys
import asyncio

if sys.platform == 'darwin':  # macOS
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
```

**Implementiert in:**
- `/app/backend/metaapi_sdk_connector.py` (Zeile 16-24)

### 2. .metaapi Cache Verzeichnis

**Problem:** SDK versucht `.metaapi` im read-only App Bundle zu schreiben.
**Lösung:** Monkey-Patch umleitet Cache zu beschreibbarem Verzeichnis:

```python
from pathlib import Path
from metaapi_cloud_sdk.metaapi.filesystem_history_database import FilesystemHistoryDatabase

user_metaapi_dir = Path.home() / 'Library' / 'Application Support' / 'Booner Trade' / '.metaapi-sdk-cache'
user_metaapi_dir.mkdir(parents=True, exist_ok=True)

original_get_db_location = FilesystemHistoryDatabase._get_db_location

async def patched_get_db_location(self, account_id, application):
    return str(user_metaapi_dir / f"{account_id}-{application}.db")

FilesystemHistoryDatabase._get_db_location = patched_get_db_location
```

**Implementiert in:**
- `/app/backend/metaapi_sdk_connector.py` (Zeile 30-65)

### 3. Optimierte SDK Timeouts

**Problem:** Standard-Timeouts zu kurz für macOS WebSocket Verbindungen.
**Lösung:** Längere Timeouts:

```python
opts = {
    'application': 'BooneTrader',
    'requestTimeout': 120000,  # 2 Minuten (statt 60 Sek)
    'connectTimeout': 120000,  # 2 Minuten
    'retryOpts': {
        'retries': 5,  # Mehr retries (statt 3)
        'minDelayInSeconds': 2,
        'maxDelayInSeconds': 60
    }
}
```

**Implementiert in:**
- `/app/backend/metaapi_sdk_connector.py` (Zeile 80-90)

### 4. Schnellerer Reconnect

**Problem:** Health Check nur alle 5 Minuten → Lange Reconnect-Zeit.
**Lösung:** Health Check alle 60 Sekunden:

```python
async def connection_health_check():
    while True:
        await asyncio.sleep(60)  # 1 Minute (statt 5 Min)
        # Check & reconnect
```

**Implementiert in:**
- `/app/backend/server.py` (Zeile 3242-3275)

## 🔬 Alternative: SDK Worker (Optional)

Für maximale Stabilität: Separater Prozess für SDK.

**Vorteile:**
- Eigener Event Loop (keine Konflikte)
- Kann neu gestartet werden ohne Main App
- Bessere Isolation

**Datei:** `/app/backend/metaapi_sdk_worker.py`

**Verwendung:**
```python
# In main.js oder server.py
worker = spawn('python', ['metaapi_sdk_worker.py'], { env: {...} })
```

## 📋 Checkliste für SDK auf macOS

- [x] Event Loop Policy setzen
- [x] Monkey-Patch für .metaapi Cache
- [x] Timeouts erhöht
- [x] Health Check beschleunigt
- [x] Python 3.11 verwendet (kompatibel mit SDK)
- [x] .env wird korrekt geladen
- [ ] SDK Worker implementiert (optional)

## 🧪 Testing

### Test 1: SDK initialisiert sich
```bash
python3 -c "
import asyncio
from metaapi_cloud_sdk import MetaApi
asyncio.run(asyncio.sleep(0.1))
print('✅ SDK imports work')
"
```

### Test 2: Event Loop Policy
```bash
python3 -c "
import sys
import asyncio
if sys.platform == 'darwin':
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    print('✅ Event loop policy set')
"
```

### Test 3: Connection Test
```python
import asyncio
from metaapi_cloud_sdk import MetaApi

async def test():
    api = MetaApi('YOUR_TOKEN', {
        'requestTimeout': 120000,
        'connectTimeout': 120000
    })
    account = await api.metatrader_account_api.get_account('YOUR_ACCOUNT_ID')
    print(f'✅ Account: {account.name}')

asyncio.run(test())
```

## 🐛 Debugging

### Logs prüfen:
```bash
# Desktop App Logs
tail -f ~/Library/Application\ Support/Booner\ Trade/backend.log | grep SDK

# Sollte zeigen:
# ✅ macOS asyncio policy set
# ✅ Monkey-patch applied
# ✅ SDK Connected: MT5_LIBERTEX_DEMO
```

### Häufige Fehler:

#### 1. "RuntimeError: Event loop is closed"
**Lösung:** Event Loop Policy nicht gesetzt
```python
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
```

#### 2. "PermissionError: [Errno 13] Permission denied: '.metaapi'"
**Lösung:** Monkey-Patch nicht angewendet
```python
# Prüfen ob Desktop-Umgebung erkannt wird
if '/Applications/' in str(Path(__file__).parent):
    # Monkey-patch anwenden
```

#### 3. "Connection timeout"
**Lösung:** Timeouts zu kurz
```python
opts = { 'requestTimeout': 120000, 'connectTimeout': 120000 }
```

## 📚 Referenzen

- [MetaAPI Python SDK Docs](https://metaapi.cloud/docs/client/)
- [Python asyncio on macOS](https://docs.python.org/3/library/asyncio-policy.html)
- [Electron Python subprocess](https://til.simonwillison.net/electron/python-inside-electron)

## ✅ Status

| Feature | Status |
|---------|--------|
| Event Loop Policy | ✅ Implementiert |
| .metaapi Monkey-Patch | ✅ Implementiert |
| Optimierte Timeouts | ✅ Implementiert |
| Health Check | ✅ Beschleunigt (60s) |
| SDK Worker | ⚠️ Optional verfügbar |

## 🎯 Ergebnis

Mit diesen Fixes sollte das SDK auf macOS ARM64 **genauso stabil** laufen wie auf Linux!
