// =========================================================================
// AUDIT & SECURITY LOGS MONITORING (REALTIME THREATS, KPI & MULTI-EXPORT)
// =========================================================================

let auditLogsCurrentPage = 1;
const auditLogsPageSize = 25;
let auditLogsCurrentPeriod = '7days';

function getPeriodDates(preset) {
  const now = new Date();
  const pad = num => String(num).padStart(2, '0');
  const formatISO = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  const formatDay = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  if (preset === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    return { start: formatDay(start), end: formatDay(now) };
  } else if (preset === '24hours') {
    const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    return { start: formatISO(start), end: formatISO(now) };
  } else if (preset === '7days') {
    const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    return { start: formatDay(start), end: formatDay(now) };
  } else if (preset === '30days') {
    const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    return { start: formatDay(start), end: formatDay(now) };
  }
  return { start: '', end: '' };
}

window.openAuditLogsModal = function() {
  const dialog = document.getElementById("audit-logs-dialog");
  if (!dialog) return;

  // Set default preset 7days if not set
  const periodSelect = document.getElementById("logs-period-select");
  if (periodSelect) {
    periodSelect.value = auditLogsCurrentPeriod;
    handlePeriodChange();
  }

  window.openDialog(dialog, document.getElementById("audit-logs-refresh-btn"));
  loadAuditLogs(1);
  loadAuditLogStats();
};

window.closeAuditLogsModal = function() {
  const dialog = document.getElementById("audit-logs-dialog");
  if (dialog) window.closeDialog(dialog);
};

window.handlePeriodChange = function() {
  const periodSelect = document.getElementById("logs-period-select");
  const customRangeWrap = document.getElementById("logs-custom-date-wrap");
  const startInput = document.getElementById("logs-start-date");
  const endInput = document.getElementById("logs-end-date");

  if (!periodSelect) return;
  const val = periodSelect.value;
  auditLogsCurrentPeriod = val;

  if (val === 'custom') {
    if (customRangeWrap) customRangeWrap.classList.remove("hidden");
  } else {
    if (customRangeWrap) customRangeWrap.classList.add("hidden");
    const dates = getPeriodDates(val);
    if (startInput) startInput.value = dates.start;
    if (endInput) endInput.value = dates.end;
  }
};

window.loadAuditLogStats = async function() {
  const startInput = document.getElementById("logs-start-date");
  const endInput = document.getElementById("logs-end-date");
  let url = '/api/v1/logs/stats';
  const params = new URLSearchParams();
  if (startInput && startInput.value) params.append("start_date", startInput.value);
  if (endInput && endInput.value) params.append("end_date", endInput.value);

  const query = params.toString();
  if (query) url += `?${query}`;

  try {
    const res = await window.apiFetch(url);
    if (res && res.data) {
      const stats = res.data;
      const elTotal = document.getElementById("kpi-logs-total");
      const elSec = document.getElementById("kpi-logs-security");
      const elLogins = document.getElementById("kpi-logs-failed-logins");
      const elErr = document.getElementById("kpi-logs-errors");

      if (elTotal) elTotal.textContent = stats.total_logs ?? 0;
      if (elSec) {
        elSec.textContent = stats.security_incidents ?? 0;
        if (stats.security_incidents > 0) {
          elSec.parentElement.classList.add("text-red-500");
        } else {
          elSec.parentElement.classList.remove("text-red-500");
        }
      }
      if (elLogins) elLogins.textContent = stats.failed_logins ?? 0;
      if (elErr) elErr.textContent = stats.system_errors ?? 0;
    }
  } catch (err) {
    console.error("Failed to load audit log stats:", err);
  }
};

window.loadAuditLogs = async function(page = 1) {
  auditLogsCurrentPage = page;
  const tbody = document.getElementById("audit-logs-rows");
  const statusEl = document.getElementById("audit-logs-loading-status");
  const paginationInfo = document.getElementById("logs-pagination-info");
  const prevBtn = document.getElementById("logs-prev-btn");
  const nextBtn = document.getElementById("logs-next-btn");

  if (!tbody) return;
  tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 muted text-xs font-mono">Memuat rekaman log audit...</td></tr>`;
  if (statusEl) statusEl.textContent = "Loading...";

  const catSelect = document.getElementById("logs-category-select");
  const sevSelect = document.getElementById("logs-severity-select");
  const searchInput = document.getElementById("logs-search-input");
  const startInput = document.getElementById("logs-start-date");
  const endInput = document.getElementById("logs-end-date");

  const params = new URLSearchParams({
    page: String(page),
    page_size: String(auditLogsPageSize)
  });

  if (catSelect && catSelect.value) params.append("category", catSelect.value);
  if (sevSelect && sevSelect.value) params.append("severity", sevSelect.value);
  if (searchInput && searchInput.value.trim()) params.append("search", searchInput.value.trim());
  if (startInput && startInput.value) params.append("start_date", startInput.value);
  if (endInput && endInput.value) params.append("end_date", endInput.value);

  try {
    const res = await window.apiFetch(`/api/v1/logs?${params.toString()}`);
    if (!res || !res.data) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500 text-xs">Gagal memuat log.</td></tr>`;
      return;
    }

    const { items, total, total_pages } = res.data;

    if (paginationInfo) {
      paginationInfo.textContent = `Halaman ${page} dari ${total_pages || 1} (${total} rekaman)`;
    }
    if (prevBtn) prevBtn.disabled = (page <= 1);
    if (nextBtn) nextBtn.disabled = (page >= total_pages || total_pages <= 1);

    if (!items || items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 muted text-xs">Tidak ada log yang sesuai dengan filter.</td></tr>`;
      return;
    }

    tbody.innerHTML = items.map(log => {
      const sev = (log.severity || "").toUpperCase();
      let badgeClass = "bg-slate-500/10 text-slate-400 border-slate-500/30";
      if (sev === 'CRITICAL') {
        badgeClass = "bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/40 font-bold";
      } else if (sev === 'WARNING') {
        badgeClass = "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/40 font-semibold";
      } else if (sev === 'ERROR') {
        badgeClass = "bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/40 font-semibold";
      } else if (sev === 'INFO') {
        badgeClass = "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30";
      }

      let localTime = log.created_at;
      try {
        const d = new Date(log.created_at);
        localTime = d.toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'medium' });
      } catch (e) {}

      const safeMessage = (log.message || "").replace(/"/g, '&quot;');
      const encodedDetails = encodeURIComponent(JSON.stringify(log.details || {}, null, 2));

      return `
        <tr class="hover:bg-soft transition-colors border-b line text-xs">
          <td class="px-3 py-2.5 font-mono text-[11px] whitespace-nowrap text-muted">${localTime}</td>
          <td class="px-3 py-2.5 whitespace-nowrap">
            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold border font-mono ${badgeClass}">${sev}</span>
          </td>
          <td class="px-3 py-2.5 font-mono text-[11px] font-semibold">${log.category}</td>
          <td class="px-3 py-2.5 font-mono text-[11px] text-sky-600 dark:text-sky-400">${log.event_type}</td>
          <td class="px-3 py-2.5 font-mono text-[11px] text-muted whitespace-nowrap">${log.source_ip || '-'}</td>
          <td class="px-3 py-2.5 text-muted">${log.username || '-'}</td>
          <td class="px-3 py-2.5 max-w-xs truncate" title="${safeMessage}">${log.message}</td>
          <td class="px-3 py-2.5 text-right whitespace-nowrap">
            <button type="button" onclick="openLogDetailModal('${log.id}', '${log.event_type}', '${encodedDetails}')"
              class="px-2 py-1 rounded-lg soft border line text-[10px] font-semibold text-sky-600 dark:text-sky-400 hover:border-sky-500 transition-colors">
              Detail JSON
            </button>
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.error("Failed to load audit logs:", err);
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-red-500 text-xs">Error: ${err.message}</td></tr>`;
  }
};

window.openLogDetailModal = function(logId, eventType, encodedDetails) {
  const modal = document.getElementById("log-detail-dialog");
  const titleEl = document.getElementById("log-detail-title");
  const jsonPre = document.getElementById("log-detail-json");

  if (!modal || !jsonPre) return;

  if (titleEl) titleEl.textContent = `Event Detail: ${eventType} (ID #${logId})`;

  try {
    const raw = decodeURIComponent(encodedDetails);
    jsonPre.textContent = raw;
  } catch (e) {
    jsonPre.textContent = encodedDetails;
  }

  window.openDialog(modal);
};

window.closeLogDetailModal = function() {
  const modal = document.getElementById("log-detail-dialog");
  if (modal) window.closeDialog(modal);
};

window.exportAuditLogs = async function(format = 'xlsx') {
  const catSelect = document.getElementById("logs-category-select");
  const sevSelect = document.getElementById("logs-severity-select");
  const searchInput = document.getElementById("logs-search-input");
  const startInput = document.getElementById("logs-start-date");
  const endInput = document.getElementById("logs-end-date");

  const params = new URLSearchParams({ format });

  if (catSelect && catSelect.value) params.append("category", catSelect.value);
  if (sevSelect && sevSelect.value) params.append("severity", sevSelect.value);
  if (searchInput && searchInput.value.trim()) params.append("search", searchInput.value.trim());
  if (startInput && startInput.value) params.append("start_date", startInput.value);
  if (endInput && endInput.value) params.append("end_date", endInput.value);

  const downloadUrl = `/api/v1/logs/export?${params.toString()}`;

  try {
    const res = await fetch(downloadUrl, {
      method: 'GET',
      credentials: 'same-origin',
    });

    if (!res.ok) {
      throw new Error(`Export failed with HTTP ${res.status}`);
    }

    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition");
    let filename = `NetBackup_Audit_Log.${format}`;
    if (disposition && disposition.includes('filename="')) {
      filename = disposition.split('filename="')[1].split('"')[0];
    }

    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(blobUrl);

  } catch (err) {
    alert(`Gagal mengekspor log audit: ${err.message}`);
  }
};
