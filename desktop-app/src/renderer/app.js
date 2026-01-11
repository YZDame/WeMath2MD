// 应用状态
const state = {
  isConverting: false,
  currentTaskId: null,
  pollInterval: null,
  outputDir: '',
  currentResult: null,
  currentMarkdown: '',
  viewMode: 'rendered',
  history: []
};

// DOM 元素
const elements = {
  form: document.getElementById('convertForm'),
  urlInput: document.getElementById('urlInput'),
  apiTokenInput: document.getElementById('apiToken'),
  outputDirInput: document.getElementById('outputDir'),
  selectDirBtn: document.getElementById('selectDirBtn'),
  convertBtn: document.getElementById('submitBtn'),
  status: document.getElementById('status'),
  statusIcon: document.getElementById('statusIcon'),
  statusText: document.getElementById('statusText'),
  progressContainer: document.getElementById('progressContainer'),
  progressFill: document.getElementById('progressFill'),
  progressStatus: document.getElementById('progressStatus'),
  progressPercent: document.getElementById('progressPercent'),
  resultCard: document.getElementById('resultCard'),
  resultTitle: document.getElementById('resultTitle'),
  resultInfo: document.getElementById('resultInfo'),
  previewBtn: document.getElementById('previewBtn'),
  openFolderBtn: document.getElementById('openFolderBtn'),
  historySection: document.getElementById('historySection'),
  historyList: document.getElementById('historyList'),
  modalOverlay: document.getElementById('modalOverlay'),
  markdownContent: document.getElementById('markdownContent'),
  sourceIcon: document.getElementById('sourceIcon'),
  renderedIcon: document.getElementById('renderedIcon'),
  toast: document.getElementById('toast'),
  appVersion: document.getElementById('appVersion')
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
  elements.previewBtn.addEventListener('click', handlePreview);

  // 输入框变化时保存设置
  elements.apiTokenInput.addEventListener('change', saveSettings);

  // ESC 关闭弹窗
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
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
    elements.historySection.style.display = 'none';
    return;
  }

  elements.historySection.style.display = 'block';
  elements.historyList.innerHTML = state.history.map((item, index) => `
    <div class="history-item">
      <div class="history-info">
        <div class="history-title">${escapeHtml(item.title)}</div>
        <div class="history-meta">${formatTime(item.time)}</div>
      </div>
      <div class="history-actions">
        <button class="btn btn-small btn-outline" onclick="previewHistory(${index})">预览</button>
        <button class="btn btn-small btn-outline" onclick="openHistoryFolder(${index})">打开</button>
      </div>
    </div>
  `).join('');
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
  elements.convertBtn.disabled = true;
  showStatus('loading', '任务已提交，正在处理...');
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
    showStatus('error', error.message || '网络错误');
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
      showStatus('error', error.message || '转换失败');
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
  state.currentResult = result;
  state.isConverting = false;
  elements.convertBtn.disabled = false;
  hideProgress();

  // 显示结果
  elements.resultTitle.textContent = result.title;
  elements.resultInfo.textContent = `识别了 ${result.image_count} 张图片`;
  elements.resultCard.classList.add('show');

  showStatus('success', '转换完成');

  // 添加到历史
  addToHistory({
    title: result.title,
    url: elements.urlInput.value,
    time: Date.now(),
    resultDir: result.result_dir,
    mdFile: result.md_file,
    imageCount: result.image_count
  });

  showToast('转换完成！', 'success');
}

// 重置状态
function resetState() {
  state.isConverting = false;
  elements.convertBtn.disabled = false;
  hideProgress();
  elements.resultCard.classList.remove('show');
  hideStatus();
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
  if (state.currentResult && state.currentResult.result_dir) {
    await window.electronAPI.openOutputFolder(state.currentResult.result_dir);
  }
}

// 打开历史记录文件夹
async function openHistoryFolder(index) {
  const item = state.history[index];
  if (item && item.resultDir) {
    await window.electronAPI.openOutputFolder(item.resultDir);
  }
}

// 预览当前结果
async function handlePreview() {
  if (!state.currentResult || !state.currentResult.md_file) return;

  // Reset to rendered view when opening new preview
  setViewMode('rendered');

  elements.modalOverlay.classList.add('show');
  elements.markdownContent.textContent = '加载中...';

  try {
    const response = await window.electronAPI.apiRequest(`/preview/${encodeURIComponent(state.currentResult.md_file)}`);

    if (response.success) {
      state.currentMarkdown = response.content;
      updateMarkdownContent();
    } else {
      elements.markdownContent.textContent = '加载失败: ' + (response.error || '未知错误');
    }
  } catch (error) {
    elements.markdownContent.textContent = '网络错误';
  }
}

// 预览历史记录
async function previewHistory(index) {
  const item = state.history[index];
  if (!item || !item.mdFile) return;

  state.currentResult = {
    md_file: item.mdFile,
    title: item.title
  };

  await handlePreview();
}

// 设置视图模式
window.setViewMode = function(mode) {
  state.viewMode = mode;

  if (mode === 'source') {
    elements.sourceIcon.classList.add('active');
    elements.renderedIcon.classList.remove('active');
    elements.markdownContent.classList.remove('rendered-view');
    elements.markdownContent.classList.add('source-view');
  } else {
    elements.renderedIcon.classList.add('active');
    elements.sourceIcon.classList.remove('active');
    elements.markdownContent.classList.remove('source-view');
    elements.markdownContent.classList.add('rendered-view');
  }

  updateMarkdownContent();
};

// 更新 Markdown 内容
function updateMarkdownContent() {
  if (state.viewMode === 'source') {
    elements.markdownContent.textContent = state.currentMarkdown;
  } else {
    // Render markdown using marked.js
    elements.markdownContent.innerHTML = marked.parse(state.currentMarkdown);

    // Render math formulas using KaTeX
    renderMathInElement(elements.markdownContent, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false},
        {left: '\\(', right: '\\)', display: false},
        {left: '\\[', right: '\\]', display: true}
      ],
      throwOnError: false,
      trust: true
    });
  }
}

// 关闭弹窗
window.closeModal = function(event) {
  if (event && event.target !== event.currentTarget) return;
  elements.modalOverlay.classList.remove('show');
};

// 显示状态
function showStatus(type, message) {
  elements.status.className = 'status ' + type;
  elements.statusText.textContent = message;

  if (type === 'loading') {
    elements.statusIcon.innerHTML = '<div class="spinner"></div>';
  } else if (type === 'success') {
    elements.statusIcon.textContent = '✓';
  } else if (type === 'error') {
    elements.statusIcon.textContent = '✕';
  }
}

// 隐藏状态
function hideStatus() {
  elements.status.className = 'status';
}

// 显示进度
function showProgress() {
  elements.progressContainer.classList.add('active');
  elements.resultCard.classList.remove('show');
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
