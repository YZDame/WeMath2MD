const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const https = require('https');

let mainWindow;
let pythonProcess = null;

// 判断是否为开发模式
const isDev = process.argv.includes('--dev');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 700,
    minWidth: 600,
    minHeight: 500,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    },
    backgroundColor: '#f5f5f5',
    titleBarStyle: 'default'
  });

  // 开发模式加载本地文件，生产模式加载打包文件
  const indexPath = isDev
    ? path.join(__dirname, '../renderer', 'index.html')
    : path.join(__dirname, '../renderer', 'index.html');

  mainWindow.loadFile(indexPath);

  // 开发模式打开开发者工具
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
    // 停止 Python 进程
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }
  });
}

// 启动 Python 后端服务
function startPythonServer() {
  return new Promise((resolve, reject) => {
    // 确定Python路径
    let pythonPath;
    let scriptPath;

    if (app.isPackaged) {
      // 生产环境：使用系统Python（不捆绑Python解释器）
      // 按优先级尝试：python3、python、python3.11、python3.12
      const pythonCandidates = ['python3', 'python', 'python3.12', 'python3.11'];
      pythonPath = 'python3';  // 默认使用 python3
      scriptPath = path.join(process.resourcesPath, 'python', 'desktop_backend.py');
    } else {
      // 开发环境：使用系统Python和父目录的脚本
      pythonPath = 'python3';
      scriptPath = path.join(__dirname, '../../../desktop_backend.py');
    }

    // 检查Python脚本是否存在
    if (!fs.existsSync(scriptPath)) {
      reject(new Error(`Python脚本不存在: ${scriptPath}`));
      return;
    }

    // 启动Python进程
    pythonProcess = spawn(pythonPath, [scriptPath], {
      cwd: app.isPackaged ? path.dirname(scriptPath) : path.join(__dirname, '../../..')
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`Python: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
      console.log(`Python进程退出，代码: ${code}`);
      pythonProcess = null;
    });

    // 轮询健康检查，等待服务器真正启动
    const maxAttempts = 30; // 最多等待 30 秒
    let attempts = 0;

    const checkHealth = () => {
      attempts++;

      https.get('http://127.0.0.1:54321/health', (res) => {
        if (res.statusCode === 200) {
          clearInterval(healthCheckInterval);
          console.log('Python 后端健康检查通过');
          resolve();
        } else {
          if (attempts >= maxAttempts) {
            cleanupAndReject();
          }
        }
      }).on('error', () => {
        if (attempts >= maxAttempts) {
          cleanupAndReject();
        }
      });
    };

    const cleanupAndReject = () => {
      clearInterval(healthCheckInterval);
      if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
      }
      reject(new Error('Python 后端启动超时，请检查系统是否安装了 Python 3 和必要的依赖包'));
    };

    const healthCheckInterval = setInterval(checkHealth, 1000);
  });
}

// 应用就绪后创建窗口
app.whenReady().then(async () => {
  // 设置外部链接处理
  app.on('web-contents-created', (event, contents) => {
    contents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: 'deny' };
    });
  });
  await createWindow();

  // 通知渲染进程：正在启动 Python 后端
  if (mainWindow) {
    mainWindow.webContents.send('python-status', { status: 'starting' });
  }

  try {
    await startPythonServer();
    console.log('Python后端已启动');
    // 通知渲染进程：Python 后端启动成功
    if (mainWindow) {
      mainWindow.webContents.send('python-status', { status: 'ready' });
    }
  } catch (error) {
    console.error('启动Python后端失败:', error);
    // 通知渲染进程：Python 后端启动失败
    if (mainWindow) {
      mainWindow.webContents.send('python-status', {
        status: 'failed',
        error: error.message
      });
    }
  }
});

// macOS: 点击dock图标重新创建窗口
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// 所有窗口关闭时退出应用
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 退出前清理
app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
});

// IPC: 选择输出目录
ipcMain.handle('select-output-dir', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory']
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

// IPC: 打开输出文件夹
ipcMain.handle('open-output-folder', async (event, folderPath) => {
  shell.openPath(folderPath);
});

// IPC: 获取版本信息
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

// IPC: 获取平台信息
ipcMain.handle('get-platform', () => {
  return process.platform;
});
