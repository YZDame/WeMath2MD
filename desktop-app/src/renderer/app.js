// 应用状态
const state = {
  isConverting: false,
  currentTaskId: null,
  pollInterval: null,
  outputDir: '',
  history: []
};

// DOM 元素
const elements = {
  form: document.getElementById('convertForm'),
  urlInput: document.getElementById('url'),
  apiTokenInput: document.getElementById('apiToken'),
  outputDirInput: document.getElementById('outputDir'),
  selectDirBtn: document.getElementById('selectDirBtn'),
  convertBtn: document.getElementById('convertBtn'),
  btnText: document.querySelector('.btn-text'),
  progressContainer: document.getElementById('progressContainer'),
  progressFill: document.getElementById('progressFill'),
  progressStatus: document.getElementById('progressStatus'),
  progressPercent: document.getElementById('progressPercent'),
  resultContainer: document.getElementById('resultContainer'),
  resultTitle: document.getElementById('resultTitle'),
  resultPath: document.getElementById('resultPath'),
  openFolderBtn: document.getElementById('openFolderBtn'),
  historyCard: document.getElementById('historyCard'),
  historyList: document.getElementById('historyList'),
  toast: document.getElementById('toast'),
  appVersion: document.getElementById('appVersion'),
  githubLink: document.getElementById('githubLink')
};

// 初始化
async function init() {
  // 加载保存的设置
  loadSettings();

  // 获取应用版本
  const version = await window.electronAPI.getAppVersion();
  elements.appVersion.textContent = version || '1.0.0';

  // 绑定事件
  bindEvents();
}

// 绑定事件
function bindEvents() {
  elements.form.addEventListener('submit', handleSubmit);
  elements.selectDirBtn.addEventListener('click', handleSelectDir);
  elements.openFolderBtn.addEventListener('click', handleOpenFolder);

  // 输入框变化时保存设置
  elements.apiTokenInput.addEventListener('change', saveSettings);
}

// 加载设置
function loadSettings() {
  const settings = localStorage.getItem('wemath2md_settings');
  if (settings) {
    const parsed = JSON.parse(settings);
    if (parsed.apiToken) {
      elements.apiTokenInput.value = parsed.apiToken;
    }
    if (parsed.outputDir) {
      state.outputDir = parsed.outputDir;
      elements.outputDirInput.value = parsed.outputDir;
    }
  }

  // 加载历史记录
  const history = localStorage.getItem('wemath2md_history');
  if (history) {
    state.history = JSON.parse(history);
    renderHistory();
  }
}

// 保存设置
function saveSettings() {
  const settings = {
    apiToken: elements.apiTokenInput.value,
    outputDir: state.outputDir
  };
  localStorage.setItem('wemath2md_settings', JSON.stringify(settings));
}

// 添加到历史记录
function addToHistory(item) {
  state.history.unshift(item);
  // 只保留最近20条
  if (state.history.length > 20) {
    state.history = state.history.slice(0, 20);
  }
  localStorage.setItem('wemath2md_history', JSON.stringify(state.history));
  renderHistory();
}

// 渲染历史记录
function renderHistory() {
  if (state.history.length === 0) {
    elements.historyCard.style.display = 'none';
    return;
  }

  elements.historyCard.style.display = 'block';
  elements.historyList.innerHTML = state.history.map(item => `
    <div class="history-item" data-url="${item.url}">
      <div class="history-item-title">${escapeHtml(item.title)}</div>
      <div class="history-item-time">${formatTime(item.time)}</div>
    </div>
  `).join('');

  // 点击历史记录填充URL
  document.querySelectorAll('.history-item').forEach(el => {
    el.addEventListener('click', () => {
      elements.urlInput.value = el.dataset.url;
    });
  });
}

// 提交表单
async function handleSubmit(e) {
  e.preventDefault();

  if (state.isConverting) {
    return;
  }

  const url = elements.urlInput.value.trim();
  const apiToken = elements.apiTokenInput.value.trim();

  if (!url) {
    showToast('请输入文章链接', 'error');
    return;
  }

  if (!apiToken) {
    showToast('请输入 MinerU API Token', 'error');
    return;
  }

  if (!url.startsWith('http')) {
    showToast('请输入有效的链接', 'error');
    return;
  }

  // 开始转换
  await startConversion(url, apiToken);
}

// 开始转换
async function startConversion(url, apiToken) {
  state.isConverting = true;
  updateConvertButton(true);
  showProgress();
  updateProgress(10, '正在下载图片...');

  try {
    // 调用转换 API
    const response = await window.electronAPI.apiRequest('/convert', {
      method: 'POST',
      body: JSON.stringify({ url, api_token: apiToken, output_dir: state.outputDir || undefined })
    });

    if (!response.success) {
      throw new Error(response.error || '转换失败');
    }

    state.currentTaskId = response.task_id;

    // 开始轮询任务状态
    startPolling();

  } catch (error) {
    console.error('转换失败:', error);
    showToast(error.message || '转换失败，请检查网络连接', 'error');
    resetState();
  }
}

// 开始轮询
function startPolling() {
  if (state.pollInterval) {
    clearInterval(state.pollInterval);
  }

  state.pollInterval = setInterval(async () => {
    try {
      const response = await window.electronAPI.apiRequest(`/status/${state.currentTaskId}`);

      if (!response.success) {
        throw new Error(response.error || '查询失败');
      }

      const { state: taskState, progress, progress_percent, result, error } = response;

      // 更新进度
      updateProgress(progress_percent || 0, progress || '处理中...');

      // 检查任务状态
      if (taskState === 'done') {
        stopPolling();
        handleSuccess(result);
      } else if (taskState === 'failed') {
        stopPolling();
        throw new Error(error || '转换失败');
      }

    } catch (error) {
      stopPolling();
      showToast(error.message || '转换失败', 'error');
      resetState();
    }
  }, 2000);
}

// 停止轮询
function stopPolling() {
  if (state.pollInterval) {
    clearInterval(state.pollInterval);
    state.pollInterval = null;
  }
}

// 转换成功
function handleSuccess(result) {
  state.isConverting = false;
  updateConvertButton(false);
  hideProgress();

  // 显示结果
  elements.resultTitle.textContent = result.title;
  elements.resultPath.textContent = result.result_dir;
  elements.resultContainer.classList.add('active');

  // 添加到历史
  addToHistory({
    title: result.title,
    url: elements.urlInput.value,
    time: Date.now(),
    resultDir: result.result_dir
  });

  // 保存当前结果目录
  state.currentResultDir = result.result_dir;

  showToast('转换完成！', 'success');
}

// 重置状态
function resetState() {
  state.isConverting = false;
  updateConvertButton(false);
  hideProgress();
  elements.resultContainer.classList.remove('active');
}

// 选择输出目录
async function handleSelectDir() {
  const dir = await window.electronAPI.selectOutputDir();
  if (dir) {
    state.outputDir = dir;
    elements.outputDirInput.value = dir;
    saveSettings();
  }
}

// 打开输出文件夹
async function handleOpenFolder() {
  if (state.currentResultDir) {
    await window.electronAPI.openOutputFolder(state.currentResultDir);
  }
}

// 更新转换按钮
function updateConvertButton(isConverting) {
  elements.convertBtn.disabled = isConverting;
  if (isConverting) {
    elements.btnText.innerHTML = '<div class="spinner"></div>';
  } else {
    elements.btnText.textContent = '开始转换';
  }
}

// 显示进度
function showProgress() {
  elements.progressContainer.classList.add('active');
  elements.resultContainer.classList.remove('active');
}

// 隐藏进度
function hideProgress() {
  elements.progressContainer.classList.remove('active');
}

// 更新进度
function updateProgress(percent, status) {
  elements.progressFill.style.width = `${percent}%`;
  elements.progressPercent.textContent = `${percent}%`;
  elements.progressStatus.textContent = status;
}

// 显示提示
function showToast(message, type = 'info') {
  elements.toast.textContent = message;
  elements.toast.className = `toast ${type} show`;

  setTimeout(() => {
    elements.toast.classList.remove('show');
  }, 3000);
}

// HTML 转义
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 格式化时间
function formatTime(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) {
    return '刚刚';
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)} 分钟前`;
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)} 小时前`;
  } else {
    return date.toLocaleDateString('zh-CN');
  }
}

// 初始化应用
init();
