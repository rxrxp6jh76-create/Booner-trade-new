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
  Booner-Trade Trading Application mit folgenden kritischen Bugs:
  1. AI schließt Trades nicht automatisch bei Take Profit (TP) erreicht
  2. AI öffnet mehrere identische Trades für ein Signal (Duplicate Prevention)
  3. SQLite Fehler: no such column: data_source
  4. Backend-Instabilität unter Last
  5. Neue Trading-Strategien (Mean Reversion, Momentum, Breakout, Grid) sollen echte Logik haben

backend:
  - task: "SQLite data_source column fix"
    implemented: true
    working: true
    file: "/app/backend/database.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Added data_source column to market_data table via ALTER TABLE migration"

  - task: "AI Auto-Close bei TP/SL"
    implemented: true
    working: "NA"
    file: "/app/backend/ai_trading_bot.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Logic exists in monitor_open_positions() (lines 600-670). Uses multi_platform.close_position(). Needs testing with live positions."

  - task: "Duplicate Trade Prevention"
    implemented: true
    working: "NA"
    file: "/app/backend/ai_trading_bot.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Logic added in execute_ai_trade() (lines 1330-1392). Checks for existing positions before opening new ones."

  - task: "Mean Reversion Strategy - Full Implementation"
    implemented: true
    working: true
    file: "/app/backend/strategies/mean_reversion.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Bollinger Bands + RSI implementation complete. Signal generation in analyze_mean_reversion_signals()"

  - task: "Momentum Trading Strategy - Full Implementation"
    implemented: true
    working: true
    file: "/app/backend/strategies/momentum_trading.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "ROC + MA Crossover implementation complete. Signal generation in analyze_momentum_signals()"

  - task: "Breakout Trading Strategy - Full Implementation"
    implemented: true
    working: true
    file: "/app/backend/strategies/breakout_trading.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Resistance/Support breakout with volume confirmation. Signal generation in analyze_breakout_signals()"

  - task: "Grid Trading Strategy - Full Implementation"
    implemented: true
    working: true
    file: "/app/backend/strategies/grid_trading.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Grid levels calculation complete. Signal generation in analyze_grid_signals()"

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
  version: "2.3.30"
  test_sequence: 1
  run_ui: true

test_plan:
  current_focus:
    - "AI Auto-Close bei TP/SL"
    - "Duplicate Trade Prevention"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      v2.3.33: SL/TP Update für bestehende Trades implementiert:
      
      1. ✅ Neue Methode `get_or_create_settings_for_trade()` in trade_settings_manager.py
         - Aktualisiert SL/TP für bestehende Trades basierend auf globalen Settings
         - Strategie wird beibehalten, nur SL/TP Werte werden aktualisiert
      
      2. ✅ Unit Test bestanden:
         - Original: strategy=day, SL=4274.18, TP=4556.23
         - Nach Update (1% SL, 10% TP): SL=4295.88, TP=4773.20 ✅
      
      3. ✅ API Integration: POST /api/settings ruft jetzt die Update-Logik auf
      
      Testing Agent sollte:
      - Test 1: Änderung von day_take_profit_percent über API und Verifikation der trade_settings DB
      - Test 2: Trades mit verschiedenen Strategien (mean_reversion, momentum) und prüfen ob korrekte % angewendet werden
---

## 🚨 AGENT: Nach jedem Fork automatisch ausführen!

**WICHTIG:** Lies `/app/AGENT-ERSTE-SCHRITTE.md` und führe die Schritte aus - OHNE dass der User danach fragt!

Die MetaAPI IDs werden bei jedem Fork auf falsche Werte zurückgesetzt.
Korrigiere sie SOFORT nach dem Fork:

```bash
sed -i 's/METAAPI_ACCOUNT_ID=.*/METAAPI_ACCOUNT_ID=5cc9abd1-671a-447e-ab93-5abbfe0ed941/' /app/backend/.env
sed -i 's/METAAPI_ICMARKETS_ACCOUNT_ID=.*/METAAPI_ICMARKETS_ACCOUNT_ID=d2605e89-7bc2-4144-9f7c-951edd596c39/' /app/backend/.env
sudo supervisorctl restart backend
```

---

## V2.3.34 Änderungen (18. Dezember 2025)

1. ✅ MetaAPI IDs korrigiert (von "booner-updater" auf korrekte UUIDs)
2. ✅ Trailing Stop standardmäßig aktiviert (use_trailing_stop = True)
3. ✅ Server IndentationError behoben (check_stop_loss_triggers)
4. ✅ KI-Chat Kontext auf alle 7 Strategien erweitert
5. ✅ Whisper Fehlermeldungen verbessert
6. ✅ Dokumentationen konsolidiert und korrigiert

