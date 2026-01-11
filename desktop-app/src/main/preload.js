const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 选择输出目录
  selectOutputDir: () => ipcRenderer.invoke('select-output-dir'),

  // 打开输出文件夹
  openOutputFolder: (folderPath) => ipcRenderer.invoke('open-output-folder', folderPath),

  // 获取应用版本
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),

  // 获取平台信息
  getPlatform: () => ipcRenderer.invoke('get-platform'),

  // API请求（通过本地服务器）
  async apiRequest(endpoint, options = {}) {
    const baseUrl = 'http://127.0.0.1:54321';
    const url = `${baseUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        }
      });

      const data = await response.json();
      return data;
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  // 上传文件请求
  async uploadFiles(formData) {
    const baseUrl = 'http://127.0.0.1:54321';
    const url = `${baseUrl}/upload`;

    try {
      const response = await fetch(url, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      return data;
    } catch (error) {
      return { success: false, error: error.message };
    }
  },

  // 监听 Python 后端状态
  onPythonStatus: (callback) => {
    const listener = (event, data) => callback(data);
    ipcRenderer.on('python-status', listener);
    // 返回清理函数，允许取消订阅
    return () => ipcRenderer.removeListener('python-status', listener);
  }
});
