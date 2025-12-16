const { contextBridge, ipcRenderer } = require('electron');

// Expose geschützte APIs an React
contextBridge.exposeInMainWorld('electronAPI', {
  getAppPath: () => ipcRenderer.invoke('get-app-path'),
  platform: process.platform,
  isElectron: true
});
