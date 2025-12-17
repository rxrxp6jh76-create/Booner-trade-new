const { contextBridge, ipcRenderer } = require('electron');

// Expose geschützte APIs an React
contextBridge.exposeInMainWorld('electronAPI', {
  getAppPath: () => ipcRenderer.invoke('get-app-path'),
  platform: process.platform,
  isElectron: true,
  // V2.3.34 FIX: Backend URL für Electron-App
  // Der Backend-Server läuft IMMER auf localhost:8000 wenn Electron gestartet wird
  getBackendUrl: () => Promise.resolve('http://localhost:8000')
});
