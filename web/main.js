
let versionWindow;

function createVersionWindow() {
    if (versionWindow && !versionWindow.isDestroyed()) {
        versionWindow.focus();
        return;
    }
    versionWindow = new BrowserWindow({
        width: 900,
        height: 600,
        webPreferences: { nodeIntegration: true, contextIsolation: false },
        frame: true,
        title: 'ClawsJoy · 版本管理',
        backgroundColor: '#0a0a1a'
    });
    versionWindow.loadFile('renderer/version_manager.html');
    versionWindow.on('closed', () => { versionWindow = null; });
    versionWindow.show();
}

ipcMain.handle('open-version-window', () => { createVersionWindow(); return { success: true }; });
