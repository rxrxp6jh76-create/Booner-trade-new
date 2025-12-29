#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Trading-Bot V3.0.0 Backend Testing Request:
  
  1. **Asset-Matrix (20 Assets)**:
     - Prüfe den `/api/commodities` Endpoint - müssen 20 Assets zurückgeben
     - Verifiziere die neuen Assets: ZINC, USDJPY, ETHEREUM, NASDAQ100
     - Teste `/api/market/{asset}` für die neuen Assets

  2. **V3.0.0 Features**:
     - Teste `/api/v3/info` Endpoint
     - Teste `/api/imessage/status` Endpoint
     - Teste `/api/imessage/command?text=Status` für das Befehlsmapping

  3. **Trading-Funktionen**:
     - Teste `/api/settings` - sollte 20 enabled_commodities zeigen
     - Teste `/api/health` für MetaAPI-Verbindung

  Erwartete Ergebnisse:
  - 20 Assets verfügbar
  - Neue Assets (ZINC, USDJPY, ETHEREUM, NASDAQ100) mit Preisdaten
  - V3.0.0 Info zeigt neue Features
  - iMessage-Status zeigt Module als verfügbar

backend:
  - task: "V3.0.0 Asset-Matrix (20 Assets)"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ /api/commodities endpoint returns 20 assets including new V3.0.0 assets: ZINC, USDJPY, ETHEREUM, NASDAQ100"

  - task: "V3.0.0 Info Endpoint"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ /api/v3/info endpoint working, returns version 3.0.0 with complete feature matrix including asset_matrix, confidence_engine_v2, imessage_bridge, ai_controller"

  - task: "V3.0.0 Settings (20 enabled_commodities)"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: "✅ /api/settings endpoint shows exactly 20 enabled_commodities including all new V3.0.0 assets"

  - task: "New Assets Market Data Endpoints"
    implemented: true
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ Individual market data endpoints for new assets (ZINC, USDJPY, ETHEREUM, NASDAQ100) via /api/market/ohlcv-simple/{asset} return success but no current_price data. NASDAQ100 returns 520 error."

  - task: "iMessage Status Endpoint"
    implemented: true
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ /api/imessage/status endpoint exists but returns no available modules. Status shows 'unknown' instead of 'available'."

  - task: "iMessage Command Mapping"
    implemented: false
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ /api/imessage/command endpoint returns 405 Method Not Allowed. Endpoint may not support GET method or may not be implemented."

  - task: "MetaAPI Health Check"
    implemented: true
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ /api/health endpoint returns 'degraded' status. MetaAPI connection shows issues despite backend logs showing active MetaAPI connections."

frontend:
  - task: "Dashboard displays correctly"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Dashboard.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Dashboard loads, shows market data, balance cards visible. Screenshot verified."

metadata:
  created_by: "main_agent"
  version: "3.0.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "New Assets Market Data Endpoints"
    - "iMessage Command Mapping"
    - "MetaAPI Health Check"
  stuck_tasks:
    - "New Assets Market Data Endpoints"
    - "iMessage Status Endpoint"
    - "iMessage Command Mapping"
    - "MetaAPI Health Check"
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "testing"
    message: |
      V3.0.0 Backend Testing Complete - Results Summary:
      
      ✅ PASSED (3/7 priority tests):
      1. Asset-Matrix: /api/commodities returns exactly 20 assets including new V3.0.0 assets
      2. V3.0.0 Info: /api/v3/info endpoint working with complete feature matrix
      3. Settings: /api/settings shows 20 enabled_commodities correctly
      
      ❌ FAILED (4/7 priority tests):
      1. New Assets Market Data: Individual endpoints return no price data, NASDAQ100 has 520 error
      2. iMessage Status: Endpoint exists but shows no available modules
      3. iMessage Commands: 405 Method Not Allowed error
      4. MetaAPI Health: Shows 'degraded' status despite active connections
      
      🔍 CRITICAL FINDINGS:
      - Backend logs show new assets (USDJPY: $156.37, ETHEREUM: $2983.07, NASDAQ100: $25644.34) are being processed successfully
      - V3.0.0 features are properly implemented and documented
      - Individual market data endpoints need fixing for new assets
      - iMessage integration needs completion
      - Health check logic needs adjustment
---

## 🚨 AGENT: Nach jedem Fork automatisch ausführen!

**WICHTIG:** Lies `/app/AGENT-ERSTE-SCHRITTE.md` und führe die Schritte aus - OHNE dass der User danach fragt!

Die MetaAPI IDs werden bei jedem Fork auf falsche Werte zurückgesetzt.
Korrigiere sie SOFORT nach dem Fork:

```bash
sed -i 's/METAAPI_ACCOUNT_ID=.*/METAAPI_ACCOUNT_ID=wisebottrader/' /app/backend/.env
sed -i 's/METAAPI_ICMARKETS_ACCOUNT_ID=.*/METAAPI_ICMARKETS_ACCOUNT_ID=wisebottrader/' /app/backend/.env
sudo supervisorctl restart backend
```

---

## V2.3.40 Änderungen (23. Dezember 2025)

1. ✅ MetaAPI IDs korrigiert (auf korrekte UUIDs)
2. ✅ Ampelsystem für Signal-Status implementiert
3. ✅ Neuer API-Endpunkt /api/signals/status
4. ✅ Frontend zeigt Ampeln auf Rohstoff-Cards
5. ✅ Signal-Zusammenfassung im KI-Status Header
6. ✅ autonomous_trading_intelligence.py Syntax-Fehler behoben

---

## V2.3.34 Änderungen (18. Dezember 2025)

1. ✅ MetaAPI IDs korrigiert (von "booner-updater" auf korrekte UUIDs)
2. ✅ Trailing Stop standardmäßig aktiviert (use_trailing_stop = True)
3. ✅ Server IndentationError behoben (check_stop_loss_triggers)
4. ✅ KI-Chat Kontext auf alle 7 Strategien erweitert
5. ✅ Whisper Fehlermeldungen verbessert
6. ✅ Dokumentationen konsolidiert und korrigiert

