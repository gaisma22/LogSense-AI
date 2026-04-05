/* app/static/js/main.js */

(function () {
  document.addEventListener('dragover', function(e) { e.preventDefault(); });
  document.addEventListener('drop', function(e) { e.preventDefault(); });

  const $ = id => document.getElementById(id);

  /* THEME (localStorage only) */
  (function themeModule() {
    const themeToggle = $('theme-toggle');
    function applyTheme(t) {
      document.documentElement.setAttribute('data-theme', t || 'dark');
      try { localStorage.setItem('theme', t); } catch (_) {}
      const terminalThemeKey = 'ls-terminal-theme';
      localStorage.setItem(terminalThemeKey, t);
      const termRoot = document.getElementById('ls-android-terminal');
      if (termRoot) termRoot.setAttribute('data-theme', t || 'dark');
      const btnTheme = termRoot?.querySelector('#lsa-theme');
      if (btnTheme) btnTheme.textContent = (t === 'dark') ? 'Day' : 'Night';
      if (termRoot) {
        const insp = termRoot.querySelector('.lsa-inspector');
        const wrap = insp?.querySelector('.lsa-timeline-wrap');
        if (wrap && insp && !insp.classList.contains('lsa-hidden')) {
            termRoot.dispatchEvent(new Event('lsa-rebuild-timeline'));
        }
      }
    }
    const saved = localStorage.getItem('theme') || 'dark';
    applyTheme(saved);
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const cur = document.documentElement.getAttribute('data-theme') || 'dark';
        const next = cur === 'dark' ? 'light' : 'dark';
        applyTheme(next);
      });
    }
  })();

  /* ANDROID MODULE */
  (function androidModule() {

    const btnCheck = $('btn-check'),
          btnStart = $('btn-start'),
          btnStop = $('btn-stop'),
          btnDisconnect = $('btn-disconnect'),
          dot = $('android-status-dot'),
          statusText = $('android-status-text'),
          infoBox = $('android-device-info'),
          dModel = $('d-model'),
          dVer = $('d-version'),
          dSerial = $('d-serial'),
          guidance = $('android-guidance'),
          deviceSelectRow = $('device-select-row'),
          deviceSelect = $('device-select'),
          actionRow = document.querySelector('.action-row');

    if (!dot) return;

    let currentSerial = null;

    function setDot(s) {
      if (!dot) return;
      dot.classList.remove('on', 'off', 'wait');
      dot.classList.add(s);
    }

    function setStatus(t) {
      if (statusText) statusText.textContent = t;
    }

    function setGuidance(t) {
      if (guidance) guidance.innerHTML = t;
    }

    function showDeviceInfo(dev) {
      if (dModel) dModel.textContent = dev.model || dev.raw || 'Unknown';
      if (dVer) dVer.textContent = dev.android_version || '';
      if (dSerial) dSerial.textContent = dev.serial || '';
      if (infoBox) infoBox.classList.remove('hidden');
    }

    function clearDeviceInfo() {
      if (dModel) dModel.textContent = '';
      if (dVer) dVer.textContent = '';
      if (dSerial) dSerial.textContent = '';
      if (infoBox) infoBox.classList.add('hidden');
    }

    function showActionRow() {
      if (actionRow) actionRow.classList.remove('hidden');
      if (btnStart) btnStart.disabled = false;
      if (btnStop) btnStop.disabled = true;
      if (btnDisconnect) btnDisconnect.classList.remove('hidden');
    }

    function hideActionRow() {
      if (actionRow) actionRow.classList.add('hidden');
      if (btnStart) btnStart.disabled = true;
      if (btnStop) btnStop.disabled = true;
    }

    function disableAll() {
      hideActionRow();
      clearDeviceInfo();
      if (deviceSelectRow) deviceSelectRow.classList.add('hidden');
      if (btnDisconnect) btnDisconnect.classList.add('hidden');
    }


    async function checkDevice() {
      try {
        const r = await fetch('/android/status', { cache: 'no-store' });
        const j = await r.json();

        // State 1: ADB not installed
        if (!j || !j.adb_available) {
          setDot('off');
          setStatus('ADB not available');
          const ua = navigator.userAgent.toLowerCase();
          if (ua.includes('win')) {
              setGuidance('ADB not found. Download Platform Tools from <strong>developer.android.com</strong> and add to <strong>PATH</strong>.');
          } else if (ua.includes('mac')) {
              setGuidance('ADB not found. Run <code>brew install android-platform-tools</code> then restart the app.');
          } else {
              setGuidance('ADB not found. Run <code>sudo apt install adb</code> then restart the app.');
          }
          if (deviceSelectRow) deviceSelectRow.classList.add('hidden');
          hideActionRow();
          clearDeviceInfo();
          currentSerial = null;
          return;
        }

        const devices = Array.isArray(j.devices) ? j.devices : [];

        // State 2: no devices at all
        if (devices.length === 0) {
          setDot('off');
          setStatus('No device');
          setGuidance('No device found. Connect your phone via USB and enable USB debugging in Developer Options.');
          if (deviceSelectRow) deviceSelectRow.classList.add('hidden');
          hideActionRow();
          clearDeviceInfo();
          currentSerial = null;
          return;
        }

        const connected = devices.filter(d => d.connected);

        // State 3: devices present but none authorized/online
        if (connected.length === 0) {
          setDot('off');
          setStatus('Unauthorized');
          setGuidance('Device found but not authorized. Unlock your phone and tap Allow on the USB debugging prompt.');
          if (deviceSelectRow) deviceSelectRow.classList.add('hidden');
          hideActionRow();
          clearDeviceInfo();
          currentSerial = null;
          return;
        }

        setGuidance('');

        // State 4: exactly one connected device
        if (connected.length === 1) {
          const dev = connected[0];
          currentSerial = dev.serial;
          setDot('on');
          setStatus('Device connected');
          if (deviceSelectRow) deviceSelectRow.classList.add('hidden');
          showDeviceInfo(dev);
          showActionRow();
          return;
        }

        // State 5: multiple connected devices
        setDot('on');
        setStatus('Multiple devices');

        // Rebuild options only if the device list changed
        const serials = connected.map(d => d.serial);
        const existing = deviceSelect ? Array.from(deviceSelect.options).map(o => o.value) : [];
        const changed = serials.length !== existing.length || serials.some((s, i) => s !== existing[i]);

        if (deviceSelect && changed) {
          deviceSelect.innerHTML = '';
          connected.forEach(dev => {
            const opt = document.createElement('option');
            opt.value = dev.serial;
            opt.textContent = (dev.model || dev.raw || 'Unknown') + ' (' + dev.serial + ')';
            deviceSelect.appendChild(opt);
          });
        }

        if (deviceSelectRow) deviceSelectRow.classList.remove('hidden');

        // Set currentSerial from current selection
        if (deviceSelect) {
          if (!currentSerial || !serials.includes(currentSerial)) {
            currentSerial = deviceSelect.value;
          } else {
            deviceSelect.value = currentSerial;
          }
        }

        const selectedDev = connected.find(d => d.serial === currentSerial) || connected[0];
        showDeviceInfo(selectedDev);
        showActionRow();

      } catch (e) {
        setDot('off');
        setStatus('Error');
        setGuidance('');
        disableAll();
        currentSerial = null;
      }
    }

    function startStream() {
      if (!currentSerial) {
        setStatus('No device selected');
        return;
      }

      try {
        if (window.LogSenseTerminal) {
          window.LogSenseTerminal.clear();
          window.LogSenseTerminal.open(currentSerial);
        }
      } catch (e) {
        console.error('Failed to start overlay stream', e);
      }

      setDot('wait');
      setStatus('Streaming…');

      if (btnStart) btnStart.disabled = true;
      if (btnStop) btnStop.disabled = false;
    }

    function stopStream() {
      try {
        if (window.LogSenseTerminal) window.LogSenseTerminal.stop();
      } catch (e) { console.error(e); }

      setDot('off');
      setStatus('Stream stopped');
      if (btnStart) btnStart.disabled = false;
      if (btnStop) btnStop.disabled = true;
    }

    document.addEventListener('DOMContentLoaded', () => {
      disableAll();
      setStatus('Not connected');

      if (btnCheck) btnCheck.onclick = checkDevice;
      if (btnStart) btnStart.onclick = startStream;
      if (btnStop) btnStop.onclick = stopStream;
      if (btnDisconnect) btnDisconnect.onclick = async () => {
        try {
          if (currentSerial) {
            const csrf = document.querySelector('meta[name="csrf-token"]');
            await fetch('/android/disconnect?serial=' + encodeURIComponent(currentSerial), {
              method: 'POST',
              headers: { 'X-CSRFToken': csrf ? csrf.getAttribute('content') : '' },
            });
          }
        } catch (_) {}
        if (window.LogSenseTerminal) window.LogSenseTerminal.stop();
        disableAll();
        setDot('off');
        setStatus('Disconnected');
        currentSerial = null;
      };

      if (deviceSelect) {
        deviceSelect.addEventListener('change', () => {
          currentSerial = deviceSelect.value;
          checkDevice();
        });
      }

      checkDevice();
      setInterval(checkDevice, 3500);
    });

    window.androidStopStream = stopStream;
  })();

 /* UPLOAD MODULE */
  (function uploadModule() {
    const zone = $('upload-zone'); if (!zone) return;
    const input = $('file-input'); const fileInfo = $('file-info'); const fName = $('fi-name'); const fSize = $('fi-size'); const fType = $('fi-type');
    const btnDiscard = $('btn-discard'); const uploadForm = $('upload-form'); const uploadError = $('upload-error');
    function showFile(file) {
      if (!file) return;
      if (fName) fName.textContent = file.name;
      if (fSize) fSize.textContent = Math.round(file.size / 1024) + ' KB';
      const extMap = { 'log': 'text/plain', 'txt': 'text/plain', 'xml': 'text/xml', 'evtx': 'Windows Event Log' };
      const ext = file.name.split('.').pop().toLowerCase();
      if (fType) fType.textContent = extMap[ext] || file.type || 'Unknown';
      if (fileInfo) fileInfo.classList.remove('hidden');
      if (btnDiscard) btnDiscard.classList.remove('hidden');
      if (uploadForm) uploadForm.classList.remove('hidden');
      if (uploadError) uploadError.textContent = '';
    }

    function clearFile() {
      if (input) input.value = '';
      if (fileInfo) fileInfo.classList.add('hidden');
      if (btnDiscard) btnDiscard.classList.add('hidden');
      if (uploadForm) uploadForm.classList.add('hidden');
      if (uploadError) uploadError.textContent = '';
    }

    function valid(file) {
      const name = (file.name || '').toLowerCase();
      if (!(name.endsWith('.txt') || name.endsWith('.log') || name.endsWith('.xml') || name.endsWith('.evtx'))) {
        if (uploadError) uploadError.textContent = 'Unsupported file type.';
        return false;
      }
      return true;
    }

    zone.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
      if (input.files.length === 0) return;
      const file = input.files[0];
      if (!valid(file)) return clearFile();
      showFile(file);
    });

    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
      e.preventDefault(); zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0]; if (!file) return;
      if (!valid(file)) return clearFile();
      input.files = e.dataTransfer.files;
      showFile(file);
    });

    if (btnDiscard) btnDiscard.onclick = clearFile;

    if (uploadForm) {
      uploadForm.addEventListener('submit', async (ev) => {
        ev.preventDefault();
        if (!input.files || input.files.length === 0) { if (uploadError) uploadError.textContent = 'No file selected.'; return; }
        window.showLoader();
        const loaderShownAt = Date.now();

        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

        const file = input.files[0];
        const fd = new FormData();
        fd.append('file', file);
        try {
          const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
          const res = await fetch('/upload', { method: 'POST', body: fd, headers: { 'X-CSRFToken': csrfToken } });
          if (!res.ok) {
            window.hideLoader();
            if (uploadError) uploadError.textContent = 'Upload failed';
            return;
          }
          const elapsed = Date.now() - loaderShownAt;
          const wait = Math.max(0, 800 - elapsed);
          setTimeout(() => { window.location.href = '/results'; }, wait);
        } catch (err) {
          window.hideLoader();
          if (uploadError) uploadError.textContent = 'Upload failed';
        }
      });
    }
  })();

  /* RESULTS MODULE */
  (function resultsModule() {
    function escapeHtml(s) {
        if (!s) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    const initial = $('initial-entries'); if (!initial) return;
    let entries = JSON.parse(initial.textContent || '[]');

    const filterSel = $('filter-severity'); const searchInp = $('results-search'); const toggleSimpl = $('toggle-simplified');
    const exportBtn = $('export-btn'); const exportOptions = $('export-options'); const collapseAll = $('collapse-all'); const downloadOriginal = $('download-original');
    const resultsControls = document.querySelector('.results-controls'); const summaryRow = document.querySelector('.summary-row');

    let simplified = false; let currentFilter = 'moderate'; let currentQuery = '';
    let currentThreshold = 'normal';

    if (entries.length === 0) {
      if (resultsControls) resultsControls.classList.add('hidden');
      if (summaryRow) summaryRow.classList.add('hidden');
      const subtitle = document.querySelector('.card p.text-muted');
      if (subtitle) subtitle.classList.add('hidden');
      const disclaimer = document.querySelector('.disclaimer');
      if (disclaimer) disclaimer.classList.add('hidden');
      const resultsList = $('results-list');
      if (resultsList) {
        const emptyState = document.createElement('div');
        emptyState.style.textAlign = 'center';
        emptyState.style.padding = '48px 24px';
        emptyState.style.color = 'var(--c-text-muted)';
        emptyState.innerHTML = '<p>No results yet. Upload a log file to run the analysis.</p>';
        const btn = document.createElement('a');
        btn.href = '/upload';
        btn.className = 'btn-primary';
        btn.textContent = 'Go to Upload';
        btn.style.marginTop = '16px';
        btn.style.display = 'inline-block';
        emptyState.appendChild(btn);
        resultsList.innerHTML = '';
        resultsList.appendChild(emptyState);
      }
      return;
    }

    function groupBySection(items) {
      const map = {};
      items.forEach(it => { const sec = it.section || 'General'; if (!map[sec]) map[sec] = []; map[sec].push(it); });
      return map;
    }

    function renderSummary(items) {
      const errors = items.filter(i => i.severity === 'high').length;
      const warnings = items.filter(i => i.severity === 'moderate').length;
      const info = items.filter(i => i.severity === 'low').length;
      const suspicious = items.filter(i => i.severity !== 'low').length;
      const elErrors = $('summary-errors'); if (elErrors) elErrors.textContent = errors;
      const elWarnings = $('summary-warnings'); if (elWarnings) elWarnings.textContent = warnings;
      const elInfo = $('summary-info'); if (elInfo) elInfo.textContent = info;
      const elSusp = $('summary-suspicious'); if (elSusp) elSusp.textContent = suspicious;
      const total = $('results-total'); if (total) total.textContent = items.length;
    }

    function filterItems() {
      let filtered = entries.slice();
      if (currentFilter === 'high') {
        filtered = filtered.filter(i => i.severity === 'high');
      } else if (currentFilter === 'moderate') {
        filtered = filtered.filter(i => i.severity === 'high' || i.severity === 'moderate');
      } else if (currentFilter === 'low') {
        filtered = filtered.filter(i => i.severity === 'low');
      }
      if (currentQuery && currentQuery.trim().length) { const q = currentQuery.toLowerCase(); filtered = filtered.filter(i => (i.entry || '').toLowerCase().includes(q) || (i.explanation || '').toLowerCase().includes(q)); }
      return filtered;
    }

    function applyThreshold(items) {
        if (currentThreshold === 'normal') return items;
        return items.map(item => {
            const base = item._baseSeverity || item.severity;
            const confidence = item.confidence || 0;
            let severity = base;

            if (currentThreshold === 'strict') {
                // Promote moderate to high if confidence >= 0.6
                if (base === 'moderate' && confidence >= 0.6) severity = 'high';
                // Promote low to moderate if confidence >= 0.7
                if (base === 'low' && confidence >= 0.7) severity = 'moderate';
            } else if (currentThreshold === 'relaxed') {
                // Demote high to moderate if confidence < 0.7
                if (base === 'high' && confidence < 0.7) severity = 'moderate';
                // Demote moderate to low if confidence < 0.5
                if (base === 'moderate' && confidence < 0.5) severity = 'low';
            }

            return { ...item, severity, _baseSeverity: base };
        });
    }

    function simplifyText(text) {
      let t = text;
      t = t.replace(/\b([a-z0-9_]+\.)+([a-z0-9_]+)\b/gi, (m, p1, p2) => p2);
      t = t.replace(/\bANR\b/gi, 'App not responding');
      t = t.replace(/\bNullPointerException\b/gi, 'Null pointer error');
      if (t.length > 220) t = t.slice(0, 220) + '…';
      return t;
    }

    function render() {
      const list = applyThreshold(filterItems());
      renderSummary(list);
      const grouped = groupBySection(list);
      const container = document.createElement('div');
      for (const sec of Object.keys(grouped)) {
        const items = grouped[sec];
        const sectionEl = document.createElement('div'); sectionEl.className = 'section'; sectionEl.setAttribute('data-section', sec);
        const header = document.createElement('div'); header.className = 'section-header'; header.innerHTML = `<strong>${escapeHtml(sec)}</strong><span class="section-count">(${items.length})</span>`;
        const toggleBtn = document.createElement('button'); toggleBtn.className = 'section-toggle btn-secondary'; toggleBtn.textContent = 'Collapse'; header.appendChild(toggleBtn); sectionEl.appendChild(header);
        const body = document.createElement('div'); body.className = 'section-body';
        items.forEach(it => {
          const item = document.createElement('div'); item.className = 'result-item'; item.setAttribute('data-severity', it.severity);
          const meta = document.createElement('div'); meta.className = 'item-meta'; meta.style.display = 'flex'; meta.style.justifyContent = 'space-between'; meta.style.alignItems = 'center';
          const left = document.createElement('div'); left.style.display = 'flex'; left.style.alignItems = 'center'; left.style.gap = '12px';
          const badge = document.createElement('span'); badge.className = 'sev-badge ' + it.severity; badge.textContent = it.severity;
          const itemText = document.createElement('div'); itemText.className = 'item-text'; const raw = document.createElement('div'); raw.className = 'raw-text'; raw.textContent = simplified ? (it.simplified || simplifyText(it.entry)) : it.entry; itemText.appendChild(raw);
          left.appendChild(badge); left.appendChild(itemText);
          const right = document.createElement('div'); right.style.display = 'flex'; right.style.gap = '6px'; right.style.flexShrink = '0';
          const explainBtn = document.createElement('button'); explainBtn.className = 'explain-btn btn-secondary'; explainBtn.textContent = 'Explain';
          const copyBtn = document.createElement('button'); copyBtn.className = 'copy-btn btn-secondary'; copyBtn.textContent = 'Copy';
          right.appendChild(explainBtn); right.appendChild(copyBtn);
          meta.appendChild(left); meta.appendChild(right);
          item.appendChild(meta);
          const expanded = document.createElement('div'); expanded.className = 'item-expanded hidden'; expanded.innerHTML = `<div class="explanation"><strong>Explanation:</strong> ${simplified ? escapeHtml((it.explanation || '').split('.')[0] + '.') || 'No explanation available.' : escapeHtml(it.explanation || 'No explanation available.')}</div><div class="extra" style="margin-top:8px;color:var(--c-text-muted)"><strong>Raw:</strong> <code style="white-space:pre-wrap">${escapeHtml(it.raw_data || it.entry)}</code></div>`;
          item.appendChild(expanded);
          explainBtn.addEventListener('click', () => expanded.classList.toggle('hidden'));
          copyBtn.addEventListener('click', () => { navigator.clipboard.writeText(it.entry).then(() => { copyBtn.textContent = 'Copied'; setTimeout(() => copyBtn.textContent = 'Copy', 900); }); });
          body.appendChild(item);
        });
        sectionEl.appendChild(body);
        toggleBtn.addEventListener('click', () => { if (body.classList.contains('hidden')) { body.classList.remove('hidden'); toggleBtn.textContent = 'Collapse'; } else { body.classList.add('hidden'); toggleBtn.textContent = 'Expand'; } });
        container.appendChild(sectionEl);
      }
      const resultsList = $('results-list');
      if (resultsList) { resultsList.innerHTML = ''; resultsList.appendChild(container); }
    }

    render();

    if (filterSel) filterSel.value = 'moderate';

    if (filterSel) filterSel.addEventListener('change', () => { currentFilter = filterSel.value; render(); });
    const thresholdSel = $('threshold-level');
    if (thresholdSel) thresholdSel.addEventListener('change', () => { currentThreshold = thresholdSel.value; render(); });
    if (searchInp) { let tmo = null; searchInp.addEventListener('input', () => { clearTimeout(tmo); tmo = setTimeout(() => { currentQuery = searchInp.value; render(); }, 220); }); }
    if (toggleSimpl) toggleSimpl.addEventListener('click', () => { simplified = !simplified; toggleSimpl.textContent = simplified ? 'Show Raw' : 'Show Simplified'; render(); });

    let allCollapsed = false;
    if (collapseAll) collapseAll.addEventListener('click', () => {
        allCollapsed = !allCollapsed;
        if (allCollapsed) {
            document.querySelectorAll('.section-body').forEach(b => b.classList.add('hidden'));
            document.querySelectorAll('.section-toggle').forEach(btn => btn.textContent = 'Expand');
            collapseAll.textContent = 'Expand all';
        } else {
            document.querySelectorAll('.section-body').forEach(b => b.classList.remove('hidden'));
            document.querySelectorAll('.section-toggle').forEach(btn => btn.textContent = 'Collapse');
            collapseAll.textContent = 'Collapse all';
        }
    });

    if (downloadOriginal) downloadOriginal.addEventListener('click', () => {
      const blob = new Blob([entries.map(e => e.entry).join('\n')], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = 'logsense_original.txt'; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    });

    if (exportBtn) {
      exportBtn.addEventListener('click', () => exportOptions.classList.toggle('hidden'));
      exportOptions.querySelectorAll('.dropdown-item').forEach(btn => {
        btn.addEventListener('click', async () => {
          const fmt = btn.getAttribute('data-format');
          try {
            const payload = { format: fmt, filter: { severity: currentFilter } };
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const res = await fetch('/export', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
              body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error('export failed');
            const blob = await res.blob();
            const cd = res.headers.get('Content-Disposition') || '';
            let filename = 'export.txt';
            const m = /filename="?([^";]+)"?/.exec(cd);
            if (m) filename = m[1];
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
            URL.revokeObjectURL(url);
            exportOptions.classList.add('hidden');
          } catch (err) {
            alert('Export failed');
          }
        });
      });
    }

  })();

})();
