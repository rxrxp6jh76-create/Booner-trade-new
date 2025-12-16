const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');

let mainWindow;
let backendProcess;
let workerProcess;
let ollamaProcess;

// Setup logging to file
const logDir = path.join(app.getPath('logs'));
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}
const logFile = path.join(logDir, 'main.log');
const errorLogFile = path.join(logDir, 'error.log');

function log(message, isError = false) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  console.log(message);
  
  try {
    fs.appendFileSync(isError ? errorLogFile : logFile, logMessage);
  } catch (err) {
    console.error('Failed to write to log:', err);
  }
}

function logError(message, error) {
  const errorMessage = error ? `${message}: ${error.stack || error}` : message;
  log(errorMessage, true);
  console.error(errorMessage);
}

// Pfade für portable Installation
const isDev = process.env.NODE_ENV === 'development';
const appPath = isDev ? __dirname : path.join(process.resourcesPath, 'app');
const backendPath = path.join(appPath, 'backend');

// SQLite Datenbank Pfad - im User Data Verzeichnis (persistent)
const dbPath = path.join(app.getPath('userData'), 'database');
const sqliteDbPath = path.join(dbPath, 'trading.db');

log('=== Booner Trade Starting with SQLite ===');
log(`App paths: ${JSON.stringify({ appPath, dbPath, sqliteDbPath, backendPath }, null, 2)}`);

// Erstelle DB-Verzeichnis wenn nicht vorhanden
if (!fs.existsSync(dbPath)) {
  log(`Creating DB directory: ${dbPath}`);
  fs.mkdirSync(dbPath, { recursive: true });
}

// ✅ KEIN MongoDB mehr benötigt! SQLite wird verwendet.
// SQLite Datenbank wird automatisch beim Backend-Start initialisiert

// ═══════════════════════════════════════════════════════════════
// Ollama Service starten (für AI Chat)
// ═══════════════════════════════════════════════════════════════
async function startOllama() {
  return new Promise((resolve) => {
    try {
      // Prüfe ob Ollama bereits läuft
      const { execSync } = require('child_process');
      try {
        execSync('curl -s http://127.0.0.1:11434/ > /dev/null 2>&1');
        log('✅ Ollama is already running');
        return resolve();
      } catch (err) {
        // Ollama läuft nicht, starten
      }
      
      // Prüfe ob Ollama installiert ist
      let ollamaPath;
      try {
        const ollamaWhich = execSync('which ollama', { encoding: 'utf8' }).trim();
        ollamaPath = ollamaWhich;
        log(`📦 Ollama found at: ${ollamaPath}`);
      } catch (err) {
        log('⚠️  Ollama not installed - AI Chat will not work');
        log('   Install: brew install ollama');
        log('   Then: ollama pull llama3:latest');
        return resolve(); // Continue without Ollama
      }
      
      log('🦙 Starting Ollama service...');
      
      // Starte Ollama als Background Service
      // WICHTIG: Wir starten Ollama nur, wenn es nicht bereits als Service läuft
      // (z.B. via brew services start ollama)
      ollamaProcess = spawn('ollama', ['serve'], {
        detached: false,
        stdio: ['ignore', 'pipe', 'pipe'] // Capture stdout/stderr für Debugging
      });
      
      // Log Ollama output (optional, für Debugging)
      ollamaProcess.stdout.on('data', (data) => {
        const output = data.toString().trim();
        if (output) {
          log(`Ollama: ${output}`);
        }
      });
      
      ollamaProcess.stderr.on('data', (data) => {
        const output = data.toString().trim();
        if (output && !output.includes('Listening on')) {
          log(`Ollama: ${output}`);
        }
      });
      
      ollamaProcess.on('error', (error) => {
        logError('❌ Failed to start Ollama', error);
        resolve(); // Continue without Ollama
      });
      
      ollamaProcess.on('exit', (code) => {
        if (code !== 0 && code !== null) {
          log(`⚠️  Ollama exited with code ${code}`);
        }
      });
      
      // Warte kurz und prüfe ob Ollama läuft
      setTimeout(() => {
        try {
          execSync('curl -s http://127.0.0.1:11434/ > /dev/null 2>&1');
          log('✅ Ollama started successfully on http://127.0.0.1:11434');
          log('   Model: llama3:latest ready for AI Chat');
        } catch (err) {
          log('⚠️  Ollama might not be running yet, but continuing...');
        }
        resolve();
      }, 3000); // 3 Sekunden warten für Ollama Start
      
    } catch (error) {
      logError('❌ Error starting Ollama', error);
      resolve(); // Continue without Ollama
    }
  });
}

// Backend (FastAPI) starten
async function startBackend() {
  // Prüfe ob Backend-Prozess schon läuft
  if (backendProcess && backendProcess.pid) {
    log('✅ Backend process already running (PID: ' + backendProcess.pid + ')');
    return Promise.resolve();
  }
  
  // Stelle sicher dass DB-Pfad existiert
  if (!fs.existsSync(dbPath)) {
    log(`Creating DB directory: ${dbPath}`);
    fs.mkdirSync(dbPath, { recursive: true });
  }
  log(`📂 Database will be stored at: ${sqliteDbPath}`);
  
  return new Promise((resolve, reject) => {
    try {
      // Try both possible Python locations
      let pythonPath = path.join(appPath, 'python', 'venv', 'bin', 'python3');
      if (!fs.existsSync(pythonPath)) {
        pythonPath = path.join(appPath, 'python', 'bin', 'python3');
      }
      const serverPath = path.join(backendPath, 'server.py');
      
      // Check if backend files exist
      if (!fs.existsSync(serverPath)) {
        const error = `Backend server.py not found at: ${serverPath}`;
        logError(error);
        reject(new Error(error));
        return;
      }
      
      log(`Starting Backend from: ${serverPath}`);
      
      // Setze Environment Variables für SQLite
      const pythonPackagesPath = path.join(appPath, 'python-packages');
      const pythonBinPath = path.join(appPath, 'python', 'bin');
      
      // Lade .env Datei für MetaAPI Credentials
      const envPath = path.join(backendPath, '.env');
      const envVars = {};
      if (fs.existsSync(envPath)) {
        log(`✅ Loading .env from: ${envPath}`);
        const envContent = fs.readFileSync(envPath, 'utf8');
        envContent.split('\n').forEach(line => {
          const trimmed = line.trim();
          if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
            const [key, ...valueParts] = trimmed.split('=');
            envVars[key.trim()] = valueParts.join('=').trim();
          }
        });
        log(`✅ Loaded ${Object.keys(envVars).length} environment variables`);
      } else {
        logError(`⚠️  .env file not found at: ${envPath}`);
      }
      
      const env = {
        ...process.env,
        ...envVars,  // Include .env variables!
        SQLITE_DB_PATH: sqliteDbPath,  // SQLite Datenbank Pfad
        PORT: '8000',
        // KRITISCH: Verwende unser portable Python!
        PYTHONPATH: pythonPackagesPath,
        PATH: `${pythonBinPath}:${process.env.PATH}`,
        // Stelle sicher dass System-Python ignoriert wird
        PYTHONNOUSERSITE: '1'
      };
      
      log(`Backend will use SQLite at: ${sqliteDbPath}`);

      // Backend muss mit uvicorn gestartet werden, nicht direkt mit python
      // Prüfe beide möglichen Locations
      const uvicornLocations = [
        path.join(appPath, 'python', 'venv', 'bin', 'uvicorn'),
        path.join(appPath, 'python', 'bin', 'uvicorn')
      ];
      
      let uvicornPath = null;
      for (const location of uvicornLocations) {
        if (fs.existsSync(location)) {
          uvicornPath = location;
          log(`✅ Found uvicorn at: ${location}`);
          break;
        }
      }
      
      if (!uvicornPath) {
        const error = `Uvicorn not found at any location: ${uvicornLocations.join(', ')}`;
        logError(error);
        reject(new Error(error));
        return;
      }
      
      log(`Using Uvicorn at: ${uvicornPath}`);
      log(`Backend directory: ${backendPath}`);
      
      backendProcess = spawn(uvicornPath, [
        'server:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'  // Auto-reload bei Fehlern
      ], {
        cwd: backendPath,
        env: env
      });
      
      // NOTE: Exit handler wird später definiert nach dem Health Check

      // Backend log files in App Support (~/Library/Application Support/Booner Trade)
      const backendLogDir = path.join(app.getPath('userData'), 'logs');
      const backendLogFile = path.join(backendLogDir, 'backend.log');
      const backendErrorLogFile = path.join(backendLogDir, 'backend-error.log');
      
      // Erstelle Log-Verzeichnis falls nicht vorhanden
      if (!fs.existsSync(backendLogDir)) {
        log(`Creating backend log directory: ${backendLogDir}`);
        fs.mkdirSync(backendLogDir, { recursive: true });
      }
      
      log(`Backend logs will be written to: ${backendLogFile}`);
      log(`Backend errors will be written to: ${backendErrorLogFile}`);

      backendProcess.stdout.on('data', (data) => {
        const message = data.toString();
        log(`Backend: ${message.trim()}`);
        
        // Write to backend.log
        try {
          fs.appendFileSync(backendLogFile, `[${new Date().toISOString()}] ${message}`);
        } catch (err) {
          console.error('Failed to write backend log:', err);
          logError(`Backend log write error: ${err.message}`);
        }
        
        if (message.includes('Uvicorn running') || message.includes('Application startup complete')) {
          log('✅ Backend ready');
          resolve();
        }
      });

      backendProcess.stderr.on('data', (data) => {
        const message = data.toString();
        logError(`Backend stderr: ${message.trim()}`);
        
        // Write to backend-error.log
        try {
          fs.appendFileSync(backendErrorLogFile, `[${new Date().toISOString()}] ${message}`);
        } catch (err) {
          console.error('Failed to write backend error log:', err);
          logError(`Backend error log write error: ${err.message}`);
        }
      });

      backendProcess.on('error', (error) => {
        logError('Backend failed to start', error);
        reject(error);
      });

      // Auto-Restart bei Exit (nur ein Handler!)
      backendProcess.on('exit', (code, signal) => {
        log(`Backend process exited with code: ${code}, signal: ${signal}`);
        backendProcess = null;
        
        // Auto-Restart bei Crash (nicht bei normalem Shutdown)
        if (!app.isQuitting && code !== 0 && signal !== 'SIGTERM') {
          log('Backend crashed, restarting in 5 seconds...');
          setTimeout(() => {
            if (!app.isQuitting) {
              startBackend().catch(e => logError('Backend restart failed:', e));
            }
          }, 5000);
        }
      });

      // Warte auf Backend-Bereitschaft mit Healthcheck
      let attempts = 0;
      const maxAttempts = 30; // 30 Sekunden max
      const checkBackend = setInterval(async () => {
        attempts++;
        try {
          const http = require('http');
          const options = {
            hostname: 'localhost',
            port: 8000,  // Backend läuft auf Port 8000
            path: '/api/ping',
            timeout: 1000
          };
          
          http.get(options, (res) => {
            if (res.statusCode === 200) {
              clearInterval(checkBackend);
              log('✅ Backend is ready and responding!');
              resolve();
            }
          }).on('error', () => {
            // Backend noch nicht bereit
            if (attempts >= maxAttempts) {
              clearInterval(checkBackend);
              log('⚠️  Backend timeout reached after 30s, continuing anyway...');
              resolve();
            }
          });
        } catch (err) {
          if (attempts >= maxAttempts) {
            clearInterval(checkBackend);
            log('⚠️  Backend timeout reached after 60s, continuing anyway...');
            resolve();
          }
        }
      }, 1000); // Check jede Sekunde
    } catch (error) {
      logError('Backend startup error', error);
      reject(error);
    }
  });
}

// MetaApi Worker starten
function startWorker() {
  return new Promise((resolve, reject) => {
    try {
      log('⚙️  Starting MetaApi Worker...');
      
      // Try both possible Python locations
      let pythonPath = path.join(appPath, 'python', 'venv', 'bin', 'python3');
      if (!fs.existsSync(pythonPath)) {
        pythonPath = path.join(appPath, 'python', 'bin', 'python3');
      }
      const workerPath = path.join(backendPath, 'worker.py');
      
      if (!fs.existsSync(workerPath)) {
        log('⚠️  Worker not found, skipping...');
        resolve();
        return;
      }
      
      if (!fs.existsSync(pythonPath)) {
        log('⚠️  Python not found, skipping worker...');
        resolve();
        return;
      }
      
      const env = {
        ...process.env,
        SQLITE_DB_PATH: sqliteDbPath
      };
      
      log(`Starting Worker from: ${workerPath}`);
      log(`Worker will use SQLite at: ${sqliteDbPath}`);
      
      workerProcess = spawn(pythonPath, [workerPath], {
        cwd: backendPath,
        env: env
      });
      
      workerProcess.stdout.on('data', (data) => {
        log(`Worker: ${data.toString().trim()}`);
      });
      
      workerProcess.stderr.on('data', (data) => {
        logError(`Worker stderr: ${data.toString().trim()}`);
      });
      
      workerProcess.on('error', (error) => {
        logError('Worker failed to start', error);
      });
      
      workerProcess.on('exit', (code) => {
        log(`Worker process exited with code: ${code}`);
      });
      
      // Worker läuft im Hintergrund, warten nicht
      log('✅ Worker started in background');
      resolve();
      
    } catch (error) {
      logError('Worker startup error', error);
      // Worker ist optional, fortfahren
      resolve();
    }
  });
}


// Main Window erstellen
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 800,
    icon: path.join(__dirname, 'assets', 'logo.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0f172a'
  });

  // Lade React App (läuft auf Port 3000 im Dev oder als statische Files)
  if (isDev) {
    log('🔧 Development Mode - Loading from localhost:3000');
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    const indexPath = path.join(appPath, 'frontend', 'index.html');
    log(`📦 Production Mode - Loading from: ${indexPath}`);
    
    // Prüfe ob index.html existiert
    if (fs.existsSync(indexPath)) {
      log('✅ index.html found');
      mainWindow.loadFile(indexPath);
    } else {
      logError(`❌ index.html NOT FOUND at: ${indexPath}`);
      const frontendPath = path.join(appPath, 'frontend');
      if (fs.existsSync(frontendPath)) {
        log(`Available files: ${fs.readdirSync(frontendPath).join(', ')}`);
      } else {
        logError(`❌ Frontend folder does not exist: ${frontendPath}`);
      }
      
      // Zeige Fehlermeldung im Fenster
      mainWindow.loadURL(`data:text/html,
        <!DOCTYPE html>
        <html>
          <body style="background:#0f172a;color:white;font-family:Arial;padding:40px;text-align:center;">
            <h1>⚠️ Frontend Build Missing</h1>
            <p>The React frontend was not found in the app package.</p>
            <p style="color:#ef4444;">Expected: ${indexPath}</p>
            <br>
            <p>Please rebuild the app:</p>
            <pre style="background:#1e293b;padding:20px;border-radius:8px;text-align:left;">
cd /app/electron-app
./BUILD-MACOS-COMPLETE.sh
            </pre>
          </body>
        </html>
      `);
    }
  }

  // Debug: Log WebContents events
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    logError(`Failed to load page: ${errorCode} - ${errorDescription}`);
  });

  mainWindow.webContents.on('did-finish-load', () => {
    log('✅ Page loaded successfully');
  });

  mainWindow.webContents.on('crashed', () => {
    logError('Renderer process crashed!');
  });

  mainWindow.on('unresponsive', () => {
    logError('Window became unresponsive');
  });

  // 🚨 Electron detected renderer unresponsive
  mainWindow.webContents.on('unresponsive', () => {
    logError('Renderer became unresponsive → force reload');
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.reloadIgnoringCache();
    }
  });

  // 🔁 Auto force reload every 10 minutes (prevents renderer freeze)
  const AUTO_RELOAD_INTERVAL = 10 * 60 * 1000;
  setInterval(() => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      log('🔁 Auto force reload triggered');
      mainWindow.webContents.reloadIgnoringCache();
    }
  }, AUTO_RELOAD_INTERVAL);

  mainWindow.on('closed', () => {
    log('Window closed');
    mainWindow = null;
  });
}

// Global error handlers
process.on('uncaughtException', (error) => {
  logError('Uncaught Exception', error);
});

process.on('unhandledRejection', (reason, promise) => {
  logError(`Unhandled Rejection at: ${promise}, reason: ${reason}`);
});

// App Lifecycle
app.on('ready', async () => {
  try {
    log('🚀 Starting Booner Trade with SQLite...');
    log(`Electron version: ${process.versions.electron}`);
    log(`Node version: ${process.versions.node}`);
    log(`Platform: ${process.platform} ${process.arch}`);
    log(`✅ Using SQLite - No MongoDB installation required!`);
    
    // 0. Starte Ollama (für AI Chat) - v2.3.27
    log('🦙 Starting Ollama...');
    await startOllama();
    
    // 1. Starte Backend (SQLite wird automatisch initialisiert)
    log('⚙️  Starting Backend...');
    await startBackend();
    
    // 2. Starte MetaApi Worker (im Hintergrund)
    log('🔧 Starting MetaApi Worker...');
    await startWorker();
    
    // 3. Warte kurz, dann öffne Window
    setTimeout(() => {
      log('🖥️  Opening Window...');
      createWindow();
    }, 2000);
    
  } catch (error) {
    logError('❌ Startup failed', error);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  log('🪟 All windows closed');
  
  // Auf macOS: App läuft weiter, Backend bleibt aktiv
  // Auf anderen Plattformen: Beende App komplett
  if (process.platform !== 'darwin') {
    log('Non-macOS: Quitting app...');
    app.quit();
  } else {
    log('macOS: App stays in dock, backend keeps running');
  }
});

app.on('activate', async () => {
  log('🔄 App activated');
  
  // Starte Backend wenn nicht läuft
  if (!backendProcess || !backendProcess.pid) {
    log('⚠️ Backend not running on activate, starting...');
    try {
      await startBackend();
    } catch (e) {
      logError('Failed to start backend on activate:', e);
    }
  }
  
  if (mainWindow === null) {
    createWindow();
  }
});

// Cleanup beim Beenden
app.on('before-quit', (event) => {
  log('🛑 Shutting down...');
  app.isQuitting = true;
  
  if (workerProcess && workerProcess.pid) {
    log('Stopping Worker...');
    try {
      workerProcess.kill('SIGTERM');
    } catch (e) {
      logError('Error killing worker:', e);
    }
  }
  
  if (backendProcess && backendProcess.pid) {
    log('Stopping Backend...');
    try {
      backendProcess.kill('SIGTERM');
    } catch (e) {
      logError('Error killing backend:', e);
    }
  }
  
  // Stoppe Ollama (falls wir es gestartet haben) - v2.3.27
  if (ollamaProcess && ollamaProcess.pid) {
    log('🦙 Stopping Ollama...');
    try {
      ollamaProcess.kill('SIGTERM');
    } catch (e) {
      logError('Error killing Ollama:', e);
    }
  }
  
  // ✅ Kein MongoDB mehr zu stoppen!
  log('✅ SQLite Datenbank wird automatisch geschlossen');
});

// IPC Communication (für Settings, etc.)
ipcMain.handle('get-app-path', () => {
  return app.getPath('userData');
});

// Provide Backend URL to Frontend
ipcMain.handle('get-backend-url', () => {
  // In Electron Desktop App, backend always runs on localhost:8000
  return 'http://localhost:8000';
});
