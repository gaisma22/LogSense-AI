// app/static/js/android_terminal.js
(function () {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* CONSTANTS                                                           */
  /* ------------------------------------------------------------------ */
  const ROOT_ID    = 'ls-android-terminal';
  const PILL_ID    = 'ls-terminal-pill';
  const POPOVER_ID = 'ls-ai-popover';
  const SSE_URL    = '/android/stream/live';
  const STATUS_URL = '/android/status';
  const MAX_ROWS   = 1000;
  const BATCH_SIZE = 8;
  const STATUS_MS  = 2500;
  const THEME_KEY  = 'ls-terminal-theme';

  /* ------------------------------------------------------------------ */
  /* CLEANUP                                                             */
  /* ------------------------------------------------------------------ */
  const SESSION_KEY = 'ls-terminal-state';

  function saveState() {
    const termEl = document.getElementById('ls-android-terminal');
    if (!termEl) return;
    const isVisible = !termEl.classList.contains('lsa-hidden');
    const isPill = pill?.style.display === 'flex';
    if (isVisible || isPill) {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({
        minimized: isPill && !isVisible,
        serial: ui.serial,
        deviceModel: ui.deviceModel,
      }));
    }
  }

  document.getElementById(ROOT_ID)?.remove();
  document.getElementById(PILL_ID)?.remove();
  document.getElementById(POPOVER_ID)?.remove();

  /* ------------------------------------------------------------------ */
  /* MODULE STATE                                                        */
  /* ------------------------------------------------------------------ */
  let es              = null;
  let statusTimer     = null;
  let userStopped     = false;
  let reconnectTimer  = null;
  let renderScheduled = false;
  let initialLoad     = false;
  let batchTimer      = null;
  let popoverTimer    = null;
  let renderQueue     = [];
  let statusClearTimer = null;
  let dragState       = null;
  let resizeState     = false;
  let msgTimers       = [];

  const levelActive = { V: false, D: false, I: false, W: true, E: true, F: true };

  const ui = {
    visible: false,
    minimized: false,
    maximized: false,
    paused: false,
    autoScroll: true,
    inspectorOpen: false,
    selectedEntry: null,
    logCount: 0,
    position: { x: null, y: null },
    theme: localStorage.getItem(THEME_KEY) || 'dark',
    serial: null,
    deviceModel: 'Android'
  };

  /* ------------------------------------------------------------------ */
  /* BUILD DOM                                                           */
  /* ------------------------------------------------------------------ */
  const root = document.createElement('div');
  root.id = ROOT_ID;
  root.className = 'lsa-hidden';
  root.setAttribute('data-theme', ui.theme);

  root.innerHTML = `
    <div class="lsa-header" id="lsa-header">
      <div class="lsa-title-block">
        <span class="lsa-title">Android Monitor</span>
        <span class="lsa-device" id="lsa-device">No device</span>
      </div>
      <div class="lsa-controls" id="lsa-controls">
        <button class="lsa-btn" id="lsa-pause" title="Pause stream">Pause</button>
        <button class="lsa-btn" id="lsa-auto" title="Toggle auto-scroll">Auto: On</button>
        <button class="lsa-btn lsa-btn-danger" id="lsa-stop" title="Stop stream">Stop</button>
        <button class="lsa-btn" id="lsa-save" title="Save session">Save</button>
        <button class="lsa-btn" id="lsa-clear" title="Clear logs">Clear</button>
        <div class="lsa-sep"></div>
        <button class="lsa-btn" id="lsa-theme" title="Toggle theme">Theme</button>
        <button class="lsa-btn" id="lsa-min" title="Minimize">\u2014</button>
        <button class="lsa-btn" id="lsa-max" title="Maximize">\u25a1</button>
        <button class="lsa-btn lsa-btn-close" id="lsa-close" title="Close">\u2715</button>
      </div>
    </div>

    <div class="lsa-stats" id="lsa-stats"></div>

    <div class="lsa-toolbar">
      <input class="lsa-filter" id="lsa-filter" placeholder="Filter by tag or keyword" autocomplete="off" spellcheck="false" />
      <div class="lsa-levels" id="lsa-levels"></div>
    </div>

    <div class="lsa-body-wrap">
      <div class="lsa-stream" id="lsa-stream"></div>
      <div class="lsa-inspector lsa-hidden" id="lsa-inspector">
        <div class="lsa-inspector-header">
          <span class="lsa-inspector-title">Entry detail</span>
          <button class="lsa-btn lsa-btn-close" id="lsa-insp-close" title="Close">\u2715</button>
        </div>
        <div class="lsa-inspector-body" id="lsa-inspector-body"></div>
      </div>
    </div>

    <div class="lsa-status-bar" id="lsa-status-bar"></div>
  `;

  document.body.appendChild(root);

  const popover = document.createElement('div');
  popover.id = POPOVER_ID;
  popover.className = 'lsa-popover';
  popover.style.display = 'none';
  document.body.appendChild(popover);

  const pill = document.createElement('div');
  pill.id = PILL_ID;
  pill.className = 'lsa-pill';
  pill.style.display = 'none';
  document.body.appendChild(pill);

  /* ------------------------------------------------------------------ */
  /* DOM REFS                                                            */
  /* ------------------------------------------------------------------ */
  const headerEl    = root.querySelector('#lsa-header');
  const controlsEl  = root.querySelector('#lsa-controls');
  const deviceEl    = root.querySelector('#lsa-device');
  const statsEl     = root.querySelector('#lsa-stats');
  const filterEl    = root.querySelector('#lsa-filter');
  const levelsEl    = root.querySelector('#lsa-levels');
  const streamEl    = root.querySelector('#lsa-stream');
  const inspEl      = root.querySelector('#lsa-inspector');
  const inspBodyEl  = root.querySelector('#lsa-inspector-body');
  const statusBar   = root.querySelector('#lsa-status-bar');

  const btnPause = root.querySelector('#lsa-pause');
  const btnAuto  = root.querySelector('#lsa-auto');
  const btnStop  = root.querySelector('#lsa-stop');
  const btnSave  = root.querySelector('#lsa-save');
  const btnClear = root.querySelector('#lsa-clear');
  const btnTheme = root.querySelector('#lsa-theme');
  btnTheme.textContent = ui.theme === 'dark' ? 'Day' : 'Night';
  const btnMin   = root.querySelector('#lsa-min');
  const btnMax   = root.querySelector('#lsa-max');
  const btnClose = root.querySelector('#lsa-close');

  /* ------------------------------------------------------------------ */
  /* INSPECTOR RESIZE                                                    */
  /* ------------------------------------------------------------------ */
  const resizeHandle = document.createElement('div');
  resizeHandle.className = 'lsa-resize-handle';
  inspEl.prepend(resizeHandle);

  resizeHandle.addEventListener('pointerdown', e => {
    resizeState = true;
    resizeHandle.setPointerCapture(e.pointerId);
    e.preventDefault();
  });

  document.addEventListener('pointermove', e => {
    if (!resizeState) return;
    const termRect = root.getBoundingClientRect();
    const w = termRect.right - e.clientX;
    inspEl.style.width = Math.min(Math.max(220, w), termRect.width * 0.55) + 'px';
  });

  document.addEventListener('pointerup', () => { resizeState = false; });
  document.addEventListener('pointercancel', () => { resizeState = false; });

  /* ------------------------------------------------------------------ */
  /* DRAGGING                                                            */
  /* ------------------------------------------------------------------ */
  headerEl.addEventListener('pointerdown', e => {
    if (ui.maximized) return;
    if (controlsEl.contains(e.target)) return;

    dragState = {
      ox: e.clientX - (ui.position.x ?? root.offsetLeft),
      oy: e.clientY - (ui.position.y ?? root.offsetTop)
    };
    headerEl.setPointerCapture(e.pointerId);
  });

  headerEl.addEventListener('pointermove', e => {
    if (!dragState) return;
    const rect = root.getBoundingClientRect();
    const maxX = window.innerWidth - rect.width;
    const maxY = window.innerHeight - 48;
    ui.position.x = Math.min(Math.max(0, e.clientX - dragState.ox), maxX);
    ui.position.y = Math.min(Math.max(0, e.clientY - dragState.oy), maxY);
    applyPosition();
  });

  headerEl.addEventListener('pointerup', () => { dragState = null; });
  headerEl.addEventListener('pointercancel', () => { dragState = null; });

  /* ------------------------------------------------------------------ */
  /* POSITION                                                            */
  /* ------------------------------------------------------------------ */
  function centerOverlay() {
    const w = Math.min(980, window.innerWidth - 40);
    const h = Math.min(540, window.innerHeight - 80);
    root.style.width = w + 'px';
    root.style.height = h + 'px';
    ui.position.x = (window.innerWidth - w) / 2;
    ui.position.y = (window.innerHeight - h) / 2;
    applyPosition();
  }

  function applyPosition() {
    if (ui.position.x == null) return;
    root.style.left = ui.position.x + 'px';
    root.style.top = ui.position.y + 'px';
    root.style.transform = 'none';
  }

  /* ------------------------------------------------------------------ */
  /* THEME                                                               */
  /* ------------------------------------------------------------------ */
  btnTheme.onclick = () => {
    ui.theme = ui.theme === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', ui.theme);
    localStorage.setItem(THEME_KEY, ui.theme);
    btnTheme.textContent = ui.theme === 'dark' ? 'Day' : 'Night';
  };

  /* ------------------------------------------------------------------ */
  /* LEVEL FILTER BUTTONS                                                */
  /* ------------------------------------------------------------------ */
  const levelNames = { V: 'Verbose', D: 'Debug', I: 'Info', W: 'Warning', E: 'Error', F: 'Fatal' };

  ['V', 'D', 'I', 'W', 'E', 'F'].forEach(l => {
    const btn = document.createElement('button');
    btn.textContent = l;
    btn.title = levelNames[l];
    if (!levelActive[l]) btn.classList.add('lsa-level-off');
    btn.onclick = () => {
      levelActive[l] = !levelActive[l];
      btn.classList.toggle('lsa-level-off', !levelActive[l]);
      applyFilters();
    };
    levelsEl.appendChild(btn);
  });

  /* ------------------------------------------------------------------ */
  /* FILTER                                                              */
  /* ------------------------------------------------------------------ */
  function applyFilters() {
    const q = filterEl.value.toLowerCase();
    const rows = streamEl.children;
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      const lvl = r.dataset.lvl;
      const show = levelActive[lvl] && (!q || r.textContent.toLowerCase().includes(q));
      r.style.display = show ? '' : 'none';
    }
  }

  filterEl.oninput = applyFilters;

  /* ------------------------------------------------------------------ */
  /* STATUS BAR                                                          */
  /* ------------------------------------------------------------------ */
  function setStatus(msg, type) {
    statusBar.textContent = msg;
    statusBar.className = 'lsa-status-bar lsa-status-' + (type || 'info');
    clearTimeout(statusClearTimer);
    if (type !== 'persistent') {
      statusClearTimer = setTimeout(() => { statusBar.textContent = ''; }, 4000);
    }
    if (type === 'warn' || type === 'error') {
      const loading = streamEl.querySelector('.lsa-loading');
      if (loading) loading.remove();
      msgTimers.forEach(t => clearTimeout(t));
      msgTimers = [];
    }
  }

  /* ------------------------------------------------------------------ */
  /* WINDOW STATE                                                        */
  /* ------------------------------------------------------------------ */
  function show() {
    ui.visible = true;
    ui.minimized = false;
    root.classList.remove('lsa-hidden');
    pill.style.display = 'none';
    if (ui.position.x == null) centerOverlay();
    applyPosition();
    saveState();
  }

  function minimize() {
    ui.minimized = true;
    ui.paused = true;
    root.querySelector('#lsa-pause').textContent = 'Resume';
    root.classList.add('lsa-hidden');
    pill.style.display = 'flex';
    updatePill();
    saveState();
  }

  function restore() {
    ui.paused = false;
    root.querySelector('#lsa-pause').textContent = 'Pause';
    sessionStorage.removeItem(SESSION_KEY);
    show();
  }

  function toggleMaximize() {
    ui.maximized = !ui.maximized;
    if (ui.maximized) {
      root.classList.add('lsa-maximized');
      root.style.left = '';
      root.style.top = '';
      root.style.width = '';
      root.style.height = '';
    } else {
      root.classList.remove('lsa-maximized');
      applyPosition();
    }
  }

  function closeTerminal() {
    userStopped = true;
    clearTimeout(reconnectTimer);
    clearTimeout(batchTimer);
    clearInterval(statusTimer);
    es?.close();
    es = null;
    root.classList.add('lsa-hidden');
    pill.style.display = 'none';
    ui.visible = false;
    ui.minimized = false;
    sessionStorage.removeItem(SESSION_KEY);
  }

  function updatePill() {
    pill.textContent = ui.deviceModel + (ui.paused ? ' \u00b7 paused' : ' \u00b7 live');
  }

  /* ------------------------------------------------------------------ */
  /* BUTTON WIRING                                                       */
  /* ------------------------------------------------------------------ */
  btnPause.onclick = () => {
    ui.paused = !ui.paused;
    ui.autoScroll = !ui.paused;
    btnPause.textContent = ui.paused ? 'Resume' : 'Pause';
    btnPause.title = ui.paused ? 'Resume stream' : 'Pause stream';
    btnAuto.textContent = ui.autoScroll ? 'Auto: On' : 'Auto: Off';
  };

  btnAuto.onclick = () => {
    ui.autoScroll = !ui.autoScroll;
    btnAuto.textContent = ui.autoScroll ? 'Auto: On' : 'Auto: Off';
  };

  btnStop.onclick = () => {
    closeTerminal();
    if (typeof window.androidStopStream === 'function') window.androidStopStream();
  };

  btnSave.onclick = () => {
    const rows = streamEl.querySelectorAll('.lsa-row');
    if (!rows.length) return;
    const lines = [];
    rows.forEach(row => {
      const ts  = row.dataset.ts || '';
      const lvl = row.dataset.lvl || '';
      const tag = row.dataset.tag || '';
      const msg = row.querySelector('.lsa-msg')?.textContent?.trim() || '';
      lines.push([ts, lvl, tag, msg].filter(Boolean).join('  '));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'logsense_' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  btnClear.onclick = () => {
    streamEl.innerHTML = '';
    ui.logCount = 0;
    closeInspector();
  };

  btnMin.onclick = minimize;
  btnMax.onclick = toggleMaximize;

  btnClose.onclick = () => {
    closeTerminal();
    if (typeof window.androidStopStream === 'function') window.androidStopStream();
  };

  pill.onclick = restore;

  /* ------------------------------------------------------------------ */
  /* STATS                                                               */
  /* ------------------------------------------------------------------ */
  async function pollStatus() {
    try {
      const r = await fetch(STATUS_URL, { cache: 'no-store' });
      const j = await r.json();
      const dev = j.devices?.[0];
      if (!dev) {
        statsEl.innerHTML =
          stat('Battery', null) +
          stat('CPU', null) +
          stat('RAM', null, '') +
          stat('Storage', null, '') +
          stat('Network', null) +
          stat('Signal', null) +
          stat('Logs', ui.logCount);
        return;
      }

      ui.deviceModel = dev.model || 'Android';
      deviceEl.textContent = ui.deviceModel + (dev.serial ? ' \u00b7 ' + dev.serial : '');
      updatePill();

      statsEl.innerHTML =
        stat('Battery', dev.battery, '%') +
        stat('CPU', dev.cpu, '%') +
        stat('RAM', dev.ram_used, dev.ram_total ? '/' + dev.ram_total + ' MB' : '') +
        stat('Storage', dev.storage_used, dev.storage_total ? '/' + dev.storage_total + ' GB' : '') +
        stat('Network', dev.net, '') +
        stat('Signal', dev.signal, '%') +
        stat('Logs', ui.logCount, '');
    } catch (_) {}
  }

  function stat(label, value, suffix) {
    const v = value != null ? value + (suffix || '') : '-';
    return '<div class="lsa-stat">' +
      '<div class="lsa-stat-label">' + label + '</div>' +
      '<div class="lsa-stat-value">' + v + '</div>' +
      '</div>';
  }

  /* ------------------------------------------------------------------ */
  /* INSPECTOR                                                           */
  /* ------------------------------------------------------------------ */
  function openInspector(entry) {
    ui.inspectorOpen = true;
    ui.selectedEntry = entry;
    ui.autoScroll = false;
    ui.paused = true;
    if (btnPause) { btnPause.textContent = 'Resume'; btnPause.title = 'Resume stream'; }
    if (btnAuto) btnAuto.textContent = 'Auto: Off';

    inspEl.classList.remove('lsa-hidden');

    const msg = entry.message || entry.raw || '';
    const raw = JSON.stringify(entry, null, 2);

    inspBodyEl.innerHTML = `
      <div class="lsa-isection lsa-itriage lsa-itriage-${entry.triage || 'ignore'}">
        <div class="lsa-itriage-label">${entry.triage_label || 'Safe to ignore'}</div>
        ${entry.triage_reason ? `<div class="lsa-itriage-reason">${entry.triage_reason}</div>` : ''}
        ${entry.action ? `<div class="lsa-itriage-action">${entry.action}</div>` : ''}
      </div>

      ${entry.what_happened ? `
      <div class="lsa-isection">
        <div class="lsa-ilabel">What happened</div>
        <div class="lsa-ivalue">${entry.what_happened}</div>
      </div>` : ''}

      <div class="lsa-isection">
        <div class="lsa-ilabel">Component</div>
        <div class="lsa-ivalue">${entry.tag || 'unknown'}</div>
      </div>

      <div class="lsa-isection">
        <div class="lsa-ilabel">When</div>
        <div class="lsa-ivalue">${entry.timestamp || 'unknown'}</div>
      </div>

      <div class="lsa-isection">
        <div class="lsa-ilabel">Raw message</div>
        <div class="lsa-imessage">${escapeHtml(msg)}</div>
        <button class="lsa-icopy" id="lsa-copy-msg">Copy</button>
      </div>

      <button class="lsa-raw-toggle" id="lsa-raw-toggle">Show raw JSON</button>
      <pre class="lsa-raw-pre" id="lsa-raw-pre" style="display:none">${escapeHtml(raw)}</pre>
    `;

    inspEl.querySelector('#lsa-insp-close').onclick = closeInspector;

    inspBodyEl.querySelector('#lsa-copy-msg').onclick = async () => {
      try {
        await navigator.clipboard.writeText(msg);
      } catch (_) {
        const t = document.createElement('textarea');
        t.value = msg;
        document.body.appendChild(t);
        t.select();
        document.execCommand('copy');
        document.body.removeChild(t);
      }
    };

    const toggleBtn = inspBodyEl.querySelector('#lsa-raw-toggle');
    const rawPre = inspBodyEl.querySelector('#lsa-raw-pre');
    toggleBtn.onclick = () => {
      const vis = rawPre.style.display === 'block';
      rawPre.style.display = vis ? 'none' : 'block';
      toggleBtn.textContent = vis ? 'Show raw JSON' : 'Hide raw JSON';
    };
  }

  function closeInspector() {
    ui.inspectorOpen = false;
    ui.selectedEntry = null;
    ui.autoScroll = true;
    ui.paused = false;
    if (btnPause) { btnPause.textContent = 'Pause'; btnPause.title = 'Pause stream'; }
    if (btnAuto) btnAuto.textContent = 'Auto: On';
    inspEl.classList.add('lsa-hidden');
    streamEl.querySelectorAll('.lsa-selected').forEach(r => r.classList.remove('lsa-selected'));
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* ------------------------------------------------------------------ */
  /* POPOVER                                                             */
  /* ------------------------------------------------------------------ */
  function showPopover(entry, rowEl, mouseX, mouseY) {
    if (!entry) return;

    const triage = entry.triage || 'ignore';
    const label  = entry.triage_label || 'Safe to ignore';
    const reason = entry.triage_reason || '';
    const action = entry.action || '';

    const labelColor = triage === 'investigate' ? '#f87171' : triage === 'monitor' ? '#fbbf24' : '#71717a';

    let html = '<div class="lsa-pop-triage" style="color:' + labelColor + ';font-weight:600;margin-bottom:8px;">' + label + '</div>';
    if (reason) html += '<div class="lsa-pop-reason">' + reason + '</div>';
    if (action) html += '<div class="lsa-pop-action">' + action + '</div>';

    popover.innerHTML = html;
    popover.style.display = 'block';

    requestAnimationFrame(() => {
      const popRect  = popover.getBoundingClientRect();
      const termRect = root.getBoundingClientRect();
      const inspOpen = !inspEl.classList.contains('lsa-hidden');
      const inspLeft = inspOpen ? inspEl.getBoundingClientRect().left : termRect.right;

      const offset = 20;
      let left = mouseX + offset;
      let top  = mouseY - (popRect.height / 2) + 10;

      if (left + popRect.width > inspLeft - 4) {
        left = mouseX - popRect.width - offset;
      }
      if (left < termRect.left + 4) left = termRect.left + 4;

      if (top < termRect.top + 4) top = termRect.top + 4;
      if (top + popRect.height > termRect.bottom - 4) top = termRect.bottom - popRect.height - 4;

      popover.style.position = 'fixed';
      popover.style.left = left + 'px';
      popover.style.top  = top  + 'px';
    });
  }

  function hidePopover() {
    popover.style.display = 'none';
    clearTimeout(popoverTimer);
  }

  /* ------------------------------------------------------------------ */
  /* EVENT DELEGATION                                                    */
  /* ------------------------------------------------------------------ */
  streamEl.addEventListener('mouseover', e => {
    const row = e.target.closest('.lsa-row');
    if (!row) return;
    clearTimeout(popoverTimer);
    const mouseX = e.clientX;
    const mouseY = e.clientY;
    popoverTimer = setTimeout(() => {
      const entry = row._entry;
      if (entry && entry.triage) showPopover(entry, row, mouseX, mouseY);
    }, 280);
  });

  streamEl.addEventListener('mouseout', e => {
    const row = e.target.closest('.lsa-row');
    if (!row) return;
    hidePopover();
  });

  streamEl.addEventListener('click', e => {
    const row = e.target.closest('.lsa-row');
    if (!row || !row._entry) return;
    hidePopover();
    streamEl.querySelectorAll('.lsa-selected').forEach(r => r.classList.remove('lsa-selected'));
    row.classList.add('lsa-selected');
    openInspector(row._entry);
  });

  /* ------------------------------------------------------------------ */
  /* RENDER PIPELINE                                                     */
  /* ------------------------------------------------------------------ */
  function render(entry) {
    if (ui.paused) return;
    renderQueue.push(entry);
    if (renderScheduled) return;
    renderScheduled = true;
    if (initialLoad) {
      batchTimer = setTimeout(() => requestAnimationFrame(flushBatch), 80);
    } else {
      requestAnimationFrame(flushBatch);
    }
  }

  function flushBatch() {
    const frag = document.createDocumentFragment();
    const wasAtBottom = streamEl.scrollHeight - streamEl.scrollTop - streamEl.clientHeight < 5;

    let count = BATCH_SIZE;
    while (renderQueue.length && count-- > 0) {
      const entry = renderQueue.shift();
      const lvlChar = (entry.level || 'V')[0].toUpperCase();
      const lvlClass = levelClass(entry.level);

      const row = document.createElement('div');
      row.className = 'lsa-row ' + lvlClass;
      row.dataset.lvl = lvlChar;
      row.dataset.ts = entry.timestamp || '';
      row.dataset.tag = entry.tag || '';
      row._entry = entry;

      row.innerHTML =
        '<div class="lsa-ts">' + (entry.timestamp || '') + '</div>' +
        '<div class="lsa-lvl">' + lvlChar + '</div>' +
        '<div class="lsa-tag">' + (entry.tag || '') + '</div>' +
        '<div class="lsa-msg">' + escapeHtml(entry.message || entry.raw || '') + '</div>';

      frag.appendChild(row);
      ui.logCount++;
    }

    streamEl.appendChild(frag);

    while (streamEl.children.length > MAX_ROWS) {
      const removed = streamEl.firstChild;
      streamEl.removeChild(removed);
      if (removed.classList?.contains('lsa-selected')) {
        closeInspector();
      }
    }

    if (wasAtBottom && ui.autoScroll) {
      streamEl.scrollTop = streamEl.scrollHeight;
    }

    applyFilters();

    if (renderQueue.length > 0) {
      if (initialLoad) {
        batchTimer = setTimeout(() => requestAnimationFrame(flushBatch), 80);
      } else {
        requestAnimationFrame(flushBatch);
      }
    } else {
      renderScheduled = false;
    }
  }

  function levelClass(level) {
    if (!level) return 'lsa-level-verbose';
    const l = level.toLowerCase();
    if (l === 'error' || l === 'e') return 'lsa-level-error';
    if (l === 'fatal' || l === 'f') return 'lsa-level-fatal';
    if (l === 'warn' || l === 'warning' || l === 'w') return 'lsa-level-warn';
    if (l === 'info' || l === 'i') return 'lsa-level-info';
    if (l === 'debug' || l === 'd') return 'lsa-level-debug';
    return 'lsa-level-verbose';
  }

  /* ------------------------------------------------------------------ */
  /* SSE                                                                 */
  /* ------------------------------------------------------------------ */
  function start(serial, skipLoader = false) {
    userStopped = false;
    initialLoad = true;
    setTimeout(() => { initialLoad = false; }, 3000);
    clearTimeout(reconnectTimer);
    es?.close();

    msgTimers.forEach(t => clearTimeout(t));
    msgTimers = [];

    if (!skipLoader) {
      streamEl.innerHTML = `<div class="lsa-loading">
  <div class="lsa-loader-card">
    <div class="lsa-loading-svg">
      <svg width="74" height="90" viewBox="0 0 74 90" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M40 76.5L72 57V69.8615C72 70.5673 71.628 71.2209 71.0211 71.5812L40 90V76.5Z" fill="#396CAA" />
        <path d="M34 75.7077L2 57V69.8615C2 70.5673 2.37203 71.2209 2.97892 71.5812L34 90V75.7077Z" fill="#396DAC" />
        <path d="M34 76.5H40V90H34V76.5Z" fill="#396CAA" />
        <path d="M3.27905 55.593L35.2806 37.5438C36.3478 36.9419 37.6522 36.9419 38.7194 37.5438L70.721 55.593C71.7294 56.1618 71.7406 57.6102 70.7411 58.1945L39.2712 76.593C37.8682 77.4133 36.1318 77.4133 34.7288 76.593L3.25887 58.1945C2.25937 57.6102 2.27061 56.1618 3.27905 55.593Z" fill="#163C79" stroke="#396CAA" />
        <path d="M40 79L72 60V70.4001C72 71.1151 71.6183 71.7758 70.9987 72.1329L40 90V79Z" fill="#173D7A" />
        <path d="M34 79L3 61V71.5751L34 90V79Z" fill="#0665B2" />
        <path id="lsa-strobe1" style="animation: lsa-strobe 0.8s infinite;" d="M58 72.5L60.5 71V74L58 75.5V72.5Z" fill="#FF715E" />
        <path id="lsa-strobe2" style="animation: lsa-strobe-green 0.8s infinite;" d="M63 69.5L65.5 68V71L63 72.5V69.5Z" fill="#17e300b4" />
        <path d="M68 66.5L70.5 65V68L68 69.5V66.5Z" fill="#FF715E" />
        <path d="M40 58.5L72 39V51.8615C72 52.5673 71.628 53.2209 71.0211 53.5812L40 72V58.5Z" fill="#396CAA" />
        <path d="M34 57.7077L2 39V51.8615C2 52.5673 2.37203 53.2209 2.97892 53.5812L34 72V57.7077Z" fill="#396DAC" />
        <path d="M34 58.5H40V72H34V58.5Z" fill="#396CAA" />
        <path d="M3.27905 37.593L35.2806 19.5438C36.3478 18.9419 37.6522 18.9419 38.7194 19.5438L70.721 37.593C71.7294 38.1618 71.7406 39.6102 70.7411 40.1945L39.2712 58.593C37.8682 59.4133 36.1318 59.4133 34.7288 58.593L3.25887 40.1945C2.25937 39.6102 2.27061 38.1618 3.27905 37.593Z" fill="#163C79" stroke="#396CAA" />
        <path d="M40 61L72 42V52.4001C72 53.1151 71.6183 53.7758 70.9987 54.1329L40 72V61Z" fill="#173D7A" />
        <path d="M34 61L3 43V53.5751L34 72V61Z" fill="#0665B2" />
        <path d="M58 54.5L60.5 53V56L58 57.5V54.5Z" fill="#FF715E" />
        <path id="lsa-strobe3" style="animation: lsa-strobe 0.8s infinite; animation-delay: 0.4s;" d="M63 51.5L65.5 50V53L63 54.5V51.5Z" fill="#FF715E" />
        <path d="M68 48.5L70.5 47V50L68 51.5V48.5Z" fill="#FF715E" />
        <path d="M40 40.5L72 21V33.8615C72 34.5673 71.628 35.2209 71.0211 35.5812L40 54V40.5Z" fill="#396CAA" />
        <path d="M34 39.7077L2 21V33.8615C2 34.5673 2.37203 35.2209 2.97892 35.5812L34 54V39.7077Z" fill="#396DAC" />
        <path d="M34 40.5H40V54H34V40.5Z" fill="#396CAA" />
        <path d="M3.27905 19.593L35.2806 1.54381C36.3478 0.941872 37.6522 0.941872 38.7194 1.54381L70.721 19.593C71.7294 20.1618 71.7406 21.6102 70.7411 22.1945L39.2712 40.593C37.8682 41.4133 36.1318 41.4133 34.7288 40.593L3.25887 22.1945C2.25937 21.6102 2.27061 20.1618 3.27905 19.593Z" fill="#124E89" stroke="#396CAA" />
        <path d="M40 43L72 24V34.4001C72 35.1151 71.6183 35.7758 70.9987 36.1329L40 54V43Z" fill="#173D7A" />
        <path d="M34 43L3 25V35.5751L34 54V43Z" fill="#0665B2" />
        <path d="M68 30.5L70.5 29V32L68 33.5V30.5Z" fill="#FF715E" />
        <path id="lsa-strobe4" style="animation: lsa-strobe 0.8s infinite; animation-delay: 0.2s;" d="M58 36.5L60.5 35V38L58 39.5V36.5Z" fill="#FF715E" />
        <path d="M63 33.5L65.5 32V35L63 36.5V33.5Z" fill="#FF715E" />
        <path id="lsa-led1" style="animation: lsa-strobe 0.5s infinite;" d="M55.1521 27.1464L53.2538 26.054L55.3602 24.9661L57.2585 26.0586L55.1521 27.1464Z" fill="#3A6DAB" />
      </svg>
    </div>
    <div class="lsa-loading-text">Connecting...</div>
  </div>
</div>`;
      setStatus('Connecting...', 'info');
      const loadingMessages = [
      { text: 'Connecting...',                        delay: 0 },
      { text: 'Cooking...',                           delay: 2000 },
      { text: 'Still cooking...',                     delay: 4000 },
      { text: 'Buffering the aura...',                delay: 6000 },
      { text: 'Asking your phone nicely...',          delay: 8000 },
      { text: 'Low-key waiting...',                   delay: 10000 },
      { text: 'Main character energy loading...',     delay: 13000 },
      { text: 'No cap, your phone is quiet rn...',    delay: 16000 },
      { text: 'It\'s giving... nothing yet...',       delay: 19000 },
      { text: 'We\'re cooked. Check your cable.',     delay: 24000 },
    ];
      loadingMessages.forEach(({ text, delay }) => {
        const t = setTimeout(() => {
          const textEl = streamEl.querySelector('.lsa-loading-text');
          if (textEl) textEl.textContent = text;
        }, delay);
        msgTimers.push(t);
      });
    }

    ui.logCount = 0;

    es = new EventSource(serial ? SSE_URL + '?serial=' + serial + '&fresh=1' : SSE_URL + '?fresh=1');
    saveState();

    es.addEventListener('log', e => {
      const loading = streamEl.querySelector('.lsa-loading');
      if (loading) loading.remove();
      msgTimers.forEach(t => clearTimeout(t));
      msgTimers = [];
      render(JSON.parse(e.data));
    });

    es.addEventListener('meta', e => {
      setStatus('Connected. Live from now.', 'ok');
    });

    es.onerror = () => {
      es?.close();
      if (userStopped) return;
      setStatus('Connection lost. Retrying in 3s.', 'warn');
      reconnectTimer = setTimeout(() => {
        if (!userStopped) start(serial);
      }, 3000);
    };
  }

  /* ------------------------------------------------------------------ */
  /* PUBLIC API                                                          */
  /* ------------------------------------------------------------------ */
  window.LogSenseTerminal = {
    open(serial) {
      ui.serial = serial;
      show();
      start(serial);
      pollStatus();
      clearInterval(statusTimer);
      statusTimer = setInterval(pollStatus, STATUS_MS);
    },
    stop() {
      closeTerminal();
    },
    clear() {
      streamEl.innerHTML = '';
      ui.logCount = 0;
    },
    get autoScroll() { return ui.autoScroll; },
    set autoScroll(v) { ui.autoScroll = v; }
  };

  const savedState = (() => { try { return JSON.parse(sessionStorage.getItem(SESSION_KEY)); } catch(_) { return null; } })();
  if (savedState && savedState.serial) {
    ui.serial = savedState.serial;
    ui.deviceModel = savedState.deviceModel || 'Android';
    if (savedState.minimized) {
      minimize();
      if (ui.serial) {
        start(ui.serial);
        pollStatus();
        clearInterval(statusTimer);
        statusTimer = setInterval(pollStatus, STATUS_MS);
      }
    } else {
      start(ui.serial);
      show();
      pollStatus();
      clearInterval(statusTimer);
      statusTimer = setInterval(pollStatus, STATUS_MS);
    }
  }

})();
