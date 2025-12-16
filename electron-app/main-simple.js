const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let backendProcess;

// Logging Setup
const logDir = path.join(app.getPath('userData'), 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}
const logFile = path.join(logDir, 'main.log');

function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  console.log(message);
  try {
    fs.appendFileSync(logFile, logMessage);
  } catch (err) {
    console.error('Log write failed:', err);
  }
}

log('=== Booner Trade Desktop App Starting (SIMPLE MODE - REST API ONLY) ===');

// Paths
const isDev = process.env.NODE_ENV === 'development';
const appPath = isDev ? __dirname : path.join(process.resourcesPath, 'app');
const backendPath = path.join(appPath, 'backend');
const pythonVenvPath = path.join(appPath, 'python', 'venv', 'bin', 'python3');

log(`App Path: ${appPath}`);
log(`Backend Path: ${backendPath}`);
log(`Python Path: ${pythonVenvPath}`);

// Load .env file
function loadEnvFile() {
  const envPath = path.join(backendPath, '.env');
  const envVars = {};
  
  log(`Loading .env from: ${envPath}`);
  
  if (!fs.existsSync(envPath)) {
    log('ERROR: .env file not found!');
    return envVars;
  }
  
  try {
    const envContent = fs.readFileSync(envPath, 'utf8');
    let count = 0;
    
    envContent.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
        const [key, ...valueParts] = trimmed.split('=');
        const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '');
        envVars[key.trim()] = value;
        count++;
        
        // Log important vars (mask sensitive data)
        if (key.includes('ACCOUNT_ID')) {
          log(`  ${key}: ${value.substring(0, 8)}...`);
        } else if (!key.includes('TOKEN') && !key.includes('KEY') && !key.includes('PASSWORD')) {
          log(`  ${key}: ${value}`);
        }
      }
    });
    
    log(`✅ Loaded ${count} environment variables`);
  } catch (err) {
    log(`ERROR loading .env: ${err.message}`);
  }
  
  return envVars;
}

// Start Backend
async function startBackend() {
  return new Promise((resolve, reject) => {
    log('Starting Backend...');
    
    // Check Python
    if (!fs.existsSync(pythonVenvPath)) {
      const error = `Python not found: ${pythonVenvPath}`;
      log(`ERROR: ${error}`);
      reject(new Error(error));
      return;
    }
    
    // Check uvicorn
    const uvicornPath = path.join(appPath, 'python', 'venv', 'bin', 'uvicorn');
    if (!fs.existsSync(uvicornPath)) {
      const error = `Uvicorn not found: ${uvicornPath}`;
      log(`ERROR: ${error}`);
      reject(new Error(error));
      return;
    }
    
    // Load environment
    const envVars = loadEnvFile();
    
    // Database path
    const dbDir = path.join(app.getPath('userData'), 'database');
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }
    
    // Build environment
    const env = {
      ...process.env,
      ...envVars,
      SQLITE_DB_PATH: path.join(dbDir, 'trading.db'),
      PORT: '8000',
      PYTHONPATH: path.join(appPath, 'python-packages'),
      PATH: `${path.join(appPath, 'python', 'venv', 'bin')}:${process.env.PATH}`,
      PYTHONNOUSERSITE: '1',
      // FORCE REST API MODE
      USE_REST_API_ONLY: 'true',
      DISABLE_SDK: 'true'
    };
    
    log('Environment configured:');
    log(`  DB: ${env.SQLITE_DB_PATH}`);
    log(`  PORT: ${env.PORT}`);
    log(`  REST API Mode: ${env.USE_REST_API_ONLY}`);
    
    // Start uvicorn
    backendProcess = spawn(uvicornPath, [
      'server:app',
      '--host', '0.0.0.0',
      '--port', '8000',
      '--log-level', 'info'
    ], {
      cwd: backendPath,
      env: env
    });
    
    // Backend log file
    const backendLogFile = path.join(app.getPath('userData'), 'backend.log');
    const backendErrorLogFile = path.join(app.getPath('userData'), 'backend-error.log');
    
    backendProcess.stdout.on('data', (data) => {
      const message = data.toString();
      log(`Backend: ${message.trim()}`);
      fs.appendFileSync(backendLogFile, `[${new Date().toISOString()}] ${message}`);
    });
    
    backendProcess.stderr.on('data', (data) => {
      const message = data.toString();
      log(`Backend ERROR: ${message.trim()}`);
      fs.appendFileSync(backendErrorLogFile, `[${new Date().toISOString()}] ${message}`);
    });
    
    backendProcess.on('error', (error) => {
      log(`Backend process error: ${error.message}`);
      reject(error);
    });
    
    backendProcess.on('exit', (code) => {
      log(`Backend exited with code: ${code}`);
    });
    
    // Health check
    let attempts = 0;
    const maxAttempts = 30;
    const checkInterval = setInterval(async () => {
      attempts++;
      try {
        const http = require('http');
        const options = {
          hostname: 'localhost',
          port: 8000,
          path: '/api/ping',
          timeout: 2000
        };
        
        http.get(options, (res) => {
          if (res.statusCode === 200) {
            clearInterval(checkInterval);
            log('✅ Backend is ready!');
            resolve();
          }
        }).on('error', () => {
          if (attempts >= maxAttempts) {
            clearInterval(checkInterval);
            log('⚠️  Backend timeout, continuing anyway...');
            resolve();
          }
        });
      } catch (err) {
        if (attempts >= maxAttempts) {
          clearInterval(checkInterval);
          log('⚠️  Backend timeout, continuing anyway...');
          resolve();
        }
      }
    }, 1000);
  });
}

// Create Window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    title: 'Booner Trade'
  });
  
  const frontendPath = path.join(appPath, 'frontend', 'index.html');
  log(`Loading frontend: ${frontendPath}`);
  mainWindow.loadFile(frontendPath);
  
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App lifecycle
app.on('ready', async () => {
  try {
    await startBackend();
    createWindow();
  } catch (error) {
    log(`Failed to start: ${error.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('quit', () => {
  if (backendProcess) {
    log('Killing backend process...');
    backendProcess.kill();
  }
});
