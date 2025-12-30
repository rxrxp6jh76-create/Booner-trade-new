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
  Trading-Bot V3.1.0 Upgrade mit:
  
  1. **Spread-Anpassung für SL/TP** (statt Trade-Ablehnung):
     - SL/TP werden automatisch an den Spread angepasst
     - Spread-Buffer verhindert sofortige Verluste
     - Spread-Informationen werden in trade_settings gespeichert
     
  2. **Bayesian Self-Learning Erweiterungen**:
     - Neue Funktionen in booner_intelligence_engine.py
     - learn_from_trade_result() für einzelne Trade-Updates
     - get_learning_statistics() für Übersicht
     - analyze_pillar_efficiency() pro Asset
     - get_weight_history() für Historie
     
  3. **AIIntelligenceWidget.jsx Erweiterungen**:
     - Neuer "Spread" Tab mit SpreadAnalysis Komponente
     - Neuer "Lernen" Tab mit LearningStats Komponente
     - 5 Tabs statt 3: Drift, Effizienz, Spread, Lernen, Auditor
     
  4. **Neue API-Endpunkte**:
     - GET /api/ai/spread-analysis
     - GET /api/ai/learning-stats
     - POST /api/ai/learn-from-trade
     - GET /api/ai/pillar-efficiency-detailed

backend:
  - task: "Spread-intelligente SL/TP Berechnung"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/backend/autonomous_trading_intelligence.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "V3.1.0: get_dynamic_sl_tp() erweitert mit spread, bid, ask Parametern. Spread-Buffer wird auf SL angewendet, TP proportional angepasst."
      - working: true
        agent: "testing"
        comment: "✅ TESTED: Spread-aware SL/TP calculation working. Entry: $2000.00, SL: $1968.50, TP: $2063.00. Spread adjustment verified: SL distance increased from $1970.00 to $1968.50 with $1.00 spread."

  - task: "Spread-Analyse API Endpunkt"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/ai/spread-analysis Endpunkt implementiert, gibt Spread-Daten aus trade_settings zurück."

  - task: "Learning Stats API Endpunkt"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "GET /api/ai/learning-stats Endpunkt implementiert, nutzt BoonerIntelligenceEngine für Statistiken."

  - task: "Bayesian Self-Learning Erweiterungen"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/backend/booner_intelligence_engine.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Neue Funktionen: learn_from_trade_result(), get_learning_statistics(), analyze_pillar_efficiency(), get_weight_history()"

  - task: "get_symbol_price Funktion"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/backend/multi_platform_connector.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Neue async def get_symbol_price() Funktion zum Abrufen von Bid/Ask Preisen vom Broker."

  - task: "Trade-Execution mit Spread-Daten"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/backend/multi_bot_system.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Trade-Ausführung aktualisiert: Holt Spread vom Broker, übergibt an SL/TP Berechnung, speichert Spread-Daten in trade_settings."

frontend:
  - task: "AIIntelligenceWidget V3.1 Update"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/frontend/src/components/AIIntelligenceWidget.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "5 Tabs implementiert: Weight Drift, Effizienz, Spread, Lernen, Auditor. Neue Komponenten: SpreadAnalysis, LearningStats."

  - task: "Dashboard displays correctly"
    implemented: true
    working: true
    file: "/app/Version_3.0.0/frontend/src/pages/Dashboard.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Dashboard zeigt alle 20 Assets mit korrekten Confidence-Scores. Screenshot verifiziert."

metadata:
  created_by: "main_agent"
  version: "3.1.0"
  test_sequence: 2
  run_ui: false

test_plan:
  current_focus:
    - "Spread-intelligente SL/TP Berechnung"
    - "Spread-Analyse API Endpunkt"
    - "Learning Stats API Endpunkt"
    - "AIIntelligenceWidget V3.1 Update"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      V3.1.0 Implementierung abgeschlossen:
      
      1. SPREAD-ANPASSUNG (statt Trade-Ablehnung):
         - SL/TP werden um 1.2-2.0x Spread erweitert (je nach Trading-Modus)
         - Spread-Buffer verhindert sofortige Verluste durch hohe Einstiegskosten
         - Spread-Daten werden in trade_settings gespeichert für Analyse
         
      2. BAYESIAN SELF-LEARNING:
         - learn_from_trade_result(): Lernt aus einzelnen Trade-Ergebnissen
         - get_learning_statistics(): Übersicht über Lernverhalten
         - analyze_pillar_efficiency(): Effizienz pro Säule pro Asset
         - get_weight_history(): Historie der Gewichts-Änderungen
         
      3. FRONTEND (AIIntelligenceWidget):
         - 5 Tabs: Drift, Effizienz, Spread, Lernen, Auditor
         - SpreadAnalysis: Zeigt Spread-Status und -Auswirkungen
         - LearningStats: Zeigt Bayesian Learning Statistiken
         
      4. NEUE API-ENDPUNKTE:
         - GET /api/ai/spread-analysis ✅ getestet
         - GET /api/ai/learning-stats ✅ getestet
         - POST /api/ai/learn-from-trade
         - GET /api/ai/pillar-efficiency-detailed
         
      HINWEIS: MetaAPI-Verbindung fehlgeschlagen (IDs müssen auf User's Mac konfiguriert werden).
      Die Code-Änderungen sind vollständig implementiert.
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

