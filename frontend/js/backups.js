// =============================================================================
// BACKUP EXECUTION HISTORY & AUDIT LOG MODAL
// Displays complete execution logs across all schedules and retention cycles.
// =============================================================================

let currentHistoryDevice = null;
let allHistoryJobs = [];
let currentHistoryTab = "all";
let currentHistoryQuery = "";

// Helper to escape HTML safely
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Format bytes into readable string (B, KB, MB)
function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

// Format duration
function formatDuration(ms) {
  if (ms === null || ms === undefined || isNaN(ms)) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// Format Date to WIB (Asia/Jakarta)
function formatWibDateTime(isoStr) {
  if (!isoStr) return { dateStr: "-", timeStr: "-", fullStr: "-" };
  try {
    const dt = new Date(isoStr);
    const dateStr = dt.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "Asia/Jakarta"
    });
    const timeStr = dt.toLocaleTimeString("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      timeZone: "Asia/Jakarta"
    }) + " WIB";
    return { dateStr, timeStr, fullStr: `${dateStr}, ${timeStr}` };
  } catch (_) {
    return { dateStr: isoStr, timeStr: "", fullStr: isoStr };
  }
}

// Copy text to clipboard with notification
window.copyHistorySha = function(text, event) {
  if (event) event.stopPropagation();
  if (!navigator.clipboard) {
    const el = document.createElement("textarea");
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
  } else {
    navigator.clipboard.writeText(text);
  }
  if (window.inform) {
    window.inform("SHA-256 hash copied to clipboard!");
  }
};

// Open the Backup History Modal for a specific device
window.openBackupHistoryModal = async function(device) {
  if (!device) return;
  currentHistoryDevice = device;
  currentHistoryTab = "all";
  currentHistoryQuery = "";

  const titleEl = document.getElementById("history-modal-title");
  const hostnameBadge = document.getElementById("history-hostname-badge");
  const policyBadge = document.getElementById("history-policy-badge");
  const subtitleEl = document.getElementById("history-modal-subtitle");
  const searchInput = document.getElementById("history-search");

  if (titleEl) titleEl.textContent = `Backup History & Logs: ${device.hostname}`;
  if (hostnameBadge) hostnameBadge.textContent = device.hostname;

  const retention = device.backup_settings?.retention_policy || "standard_31";
  const retentionName = retention === "smart_7_4_12_3" ? "Smart Retention (GFS)" : "Standard 31 Days";
  if (policyBadge) {
    policyBadge.textContent = retentionName;
    policyBadge.className = retention === "smart_7_4_12_3"
      ? "font-mono text-[11px] font-bold px-2.5 py-0.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400"
      : "font-mono text-[11px] font-bold px-2.5 py-0.5 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400";
  }

  const modelText = window.formatDeviceModel 
    ? window.formatDeviceModel(device) 
    : ((device.vendor ? `${device.vendor} ` : "") + (device.model || "-"));
  const workerText = device.backup_settings?.driver_key || "Unassigned";
  const schedText = device.backup_settings?.schedule_enabled && device.backup_settings?.daily_time
    ? `Daily @ ${device.backup_settings.daily_time} WIB`
    : "Disabled";

  if (subtitleEl) {
    subtitleEl.textContent = `IP: ${device.ip_address} • Model: ${modelText} • Worker: ${workerText} • Schedule: ${schedText}`;
  }

  if (searchInput) searchInput.value = "";

  // Reset tab UI
  document.querySelectorAll(".history-tab").forEach(tab => {
    if (tab.dataset.tab === "all") {
      tab.classList.add("active", "bg-white", "dark:bg-slate-800", "shadow-sm");
    } else {
      tab.classList.remove("active", "bg-white", "dark:bg-slate-800", "shadow-sm");
    }
  });

  const tbody = document.getElementById("history-list-rows");
  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-10 muted">
          <div class="flex flex-col items-center justify-center gap-2">
            <span class="w-3 h-3 rounded-full bg-sky-500 animate-ping"></span>
            <span class="text-xs font-semibold">Loading backup execution audit logs...</span>
          </div>
        </td>
      </tr>
    `;
  }

  // Open the dialog
  window.openDialog(
    document.getElementById("backup-history-dialog"),
    document.getElementById("history-close-btn")
  );

  // Fetch jobs
  await fetchHistoryJobs();
};

// Fetch jobs for current device
async function fetchHistoryJobs() {
  if (!currentHistoryDevice) return;
  const tbody = document.getElementById("history-list-rows");

  try {
    const res = await window.api.backups.listForDevice(currentHistoryDevice.id, { limit: 200 });
    allHistoryJobs = res.data?.items || res.items || [];

    updateHistoryStats();
    renderHistoryTable();
  } catch (err) {
    console.error("Failed to load backup history:", err);
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="text-center py-10 text-rose-500">
            <div class="flex flex-col items-center justify-center gap-1.5">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span class="font-semibold text-xs">Failed to load execution audit logs: ${escapeHtml(err.message)}</span>
            </div>
          </td>
        </tr>
      `;
    }
  }
}

// Refresh current history live
window.refreshCurrentHistory = async function() {
  const btn = document.getElementById("history-refresh-btn");
  if (btn) btn.classList.add("animate-spin");
  await fetchHistoryJobs();
  if (btn) {
    setTimeout(() => btn.classList.remove("animate-spin"), 500);
  }
  if (window.inform) window.inform("Backup execution history refreshed.");
};

// Update top statistics cards and tab badges
function updateHistoryStats() {
  const total = allHistoryJobs.length;
  const successJobs = allHistoryJobs.filter(j => 
    j.state === "SUCCESS_CHANGED" || j.state === "SUCCESS_NO_CHANGE" || j.state === "SUCCESS"
  );
  const failedJobs = allHistoryJobs.filter(j => 
    j.state === "FAILED" || (j.state && j.state.startsWith("SKIPPED"))
  );
  const scheduledJobs = allHistoryJobs.filter(j => j.trigger_type === "scheduled");
  const manualJobs = allHistoryJobs.filter(j => j.trigger_type === "manual");

  const successRate = total > 0 ? Math.round((successJobs.length / total) * 100) : 0;

  // Stat Cards
  const statTotal = document.getElementById("history-stat-total");
  const statSuccessRate = document.getElementById("history-stat-success-rate");
  const statFailed = document.getElementById("history-stat-failed");
  const statLast = document.getElementById("history-stat-last");

  if (statTotal) statTotal.textContent = total;
  if (statSuccessRate) statSuccessRate.textContent = total > 0 ? `${successRate}%` : "-";
  if (statFailed) statFailed.textContent = failedJobs.length;

  if (statLast) {
    if (total > 0 && allHistoryJobs[0]) {
      const lastJob = allHistoryJobs[0];
      const isSuccess = lastJob.state === "SUCCESS_CHANGED" || lastJob.state === "SUCCESS_NO_CHANGE" || lastJob.state === "SUCCESS";
      const wib = formatWibDateTime(lastJob.finished_at || lastJob.created_at);
      statLast.textContent = `${isSuccess ? "✓ Success" : "✗ Failed"} (${wib.dateStr})`;
      statLast.className = `text-xs font-semibold mt-1 truncate ${isSuccess ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}`;
    } else {
      statLast.textContent = "No Records";
      statLast.className = "text-xs font-semibold mt-1 truncate muted";
    }
  }

  // Tab Badge Counters
  const countAll = document.getElementById("history-count-all");
  const countSched = document.getElementById("history-count-sched");
  const countManual = document.getElementById("history-count-manual");
  const countSuccess = document.getElementById("history-count-success");
  const countFailed = document.getElementById("history-count-failed");

  if (countAll) countAll.textContent = total;
  if (countSched) countSched.textContent = scheduledJobs.length;
  if (countManual) countManual.textContent = manualJobs.length;
  if (countSuccess) countSuccess.textContent = successJobs.length;
  if (countFailed) countFailed.textContent = failedJobs.length;
}

// Switch Filter Tab
window.filterHistoryTab = function(tabName) {
  currentHistoryTab = tabName;
  document.querySelectorAll(".history-tab").forEach(tab => {
    if (tab.dataset.tab === tabName) {
      tab.classList.add("active", "bg-white", "dark:bg-slate-800", "shadow-sm");
    } else {
      tab.classList.remove("active", "bg-white", "dark:bg-slate-800", "shadow-sm");
    }
  });
  renderHistoryTable();
};

// Live Search Input Handler
window.handleHistorySearch = function(query) {
  currentHistoryQuery = (query || "").trim().toLowerCase();
  renderHistoryTable();
};

// Render Table Rows based on filters
function renderHistoryTable() {
  const tbody = document.getElementById("history-list-rows");
  if (!tbody) return;

  const currentUser = window.authModule ? window.authModule.currentUser() : null;
  const isViewer = currentUser && currentUser.role === "viewer";

  // Filter by Tab
  let filtered = allHistoryJobs.filter(job => {
    const isSuccess = job.state === "SUCCESS_CHANGED" || job.state === "SUCCESS_NO_CHANGE" || job.state === "SUCCESS";
    const isFailed = job.state === "FAILED" || (job.state && job.state.startsWith("SKIPPED"));

    if (currentHistoryTab === "scheduled") return job.trigger_type === "scheduled";
    if (currentHistoryTab === "manual") return job.trigger_type === "manual";
    if (currentHistoryTab === "success") return isSuccess;
    if (currentHistoryTab === "failed") return isFailed;
    return true; // 'all'
  });

  // Filter by Query
  if (currentHistoryQuery) {
    filtered = filtered.filter(job => {
      const trigger = (job.trigger_type || "").toLowerCase();
      const state = (job.state || "").toLowerCase();
      const change = (job.change_status || "").toLowerCase();
      const sha = (job.content_sha256 || "").toLowerCase();
      const failMsg = (job.failure?.message || "").toLowerCase();
      const failCode = (job.failure?.code || "").toLowerCase();
      const failStage = (job.failure?.stage || "").toLowerCase();
      const dateStr = (job.created_at || "").toLowerCase();

      return trigger.includes(currentHistoryQuery) ||
             state.includes(currentHistoryQuery) ||
             change.includes(currentHistoryQuery) ||
             sha.includes(currentHistoryQuery) ||
             failMsg.includes(currentHistoryQuery) ||
             failCode.includes(currentHistoryQuery) ||
             failStage.includes(currentHistoryQuery) ||
             dateStr.includes(currentHistoryQuery);
    });
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-10 muted">
          <div class="flex flex-col items-center justify-center gap-1.5">
            <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span class="font-semibold text-xs">No backup execution logs match your filter criteria.</span>
            <span class="text-[11px]">Try switching filter tabs or clearing your search term.</span>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map(job => {
    const isSuccess = job.state === "SUCCESS_CHANGED" || job.state === "SUCCESS_NO_CHANGE" || job.state === "SUCCESS";
    const isFailed = job.state === "FAILED" || (job.state && job.state.startsWith("SKIPPED"));
    const isRunning = ["QUEUED", "RUNNING", "CONNECTING", "AUTHENTICATING", "DISCOVERING", "EXTRACTING", "VALIDATING", "HASHING", "UPLOADING"].includes(job.state);

    // Execution Time (WIB)
    const timeInfo = formatWibDateTime(job.finished_at || job.created_at);

    // Trigger Pill
    let triggerPill = "";
    if (job.trigger_type === "scheduled") {
      triggerPill = `
        <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/30" title="Executed by automated Celery Beat schedule">
          <svg class="w-3 h-3 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Schedule</span>
        </span>
      `;
    } else {
      triggerPill = `
        <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-sky-500/10 text-sky-700 dark:text-sky-400 border border-sky-500/30" title="Manually triggered via Backup Now">
          <svg class="w-3 h-3 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Manual</span>
        </span>
      `;
    }

    // Status Badge
    let statusPill = "";
    if (isSuccess) {
      statusPill = `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>SUCCESS</span>
        </span>
      `;
    } else if (isFailed) {
      const label = job.state && job.state.startsWith("SKIPPED") ? "SKIPPED" : "FAILED";
      statusPill = `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/30">
          <span class="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
          <span>${label}</span>
        </span>
      `;
    } else if (isRunning) {
      statusPill = `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30">
          <span class="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
          <span>${job.state}</span>
        </span>
      `;
    } else {
      statusPill = `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20">
          <span class="w-2 h-2 rounded-full bg-slate-400"></span>
          <span>${job.state || "UNKNOWN"}</span>
        </span>
      `;
    }

    // Change Status
    let changePill = "-";
    const change = (job.change_status || "").toLowerCase();
    if (change === "baseline") {
      changePill = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/20 font-mono">Baseline</span>`;
    } else if (change === "changed") {
      changePill = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20 font-mono">Changed</span>`;
    } else if (change === "no_change") {
      changePill = `<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20 font-mono">No Change</span>`;
    }

    // Size
    const sizeStr = formatBytes(job.raw_size_bytes);

    // Duration
    const durationStr = formatDuration(job.duration_ms);

    // Retention & SHA-256
    let retentionHtml = "";
    if (job.snapshot) {
      const policyName = job.snapshot.retention_policy === "smart_7_4_12_3" ? "Smart Ret." : "31 Days";
      const marks = job.snapshot.retention_marks && job.snapshot.retention_marks.length > 0
        ? ` [${job.snapshot.retention_marks.join(", ")}]`
        : "";
      retentionHtml = `<div class="font-semibold text-[10px] text-purple-600 dark:text-purple-400 font-mono">${policyName}${marks}</div>`;
    } else {
      retentionHtml = `<div class="text-[10px] muted font-mono">No snapshot</div>`;
    }

    const sha = job.content_sha256 || "";
    const shortSha = sha ? `${sha.slice(0, 8)}...${sha.slice(-6)}` : "-";
    const shaHtml = sha
      ? `
        <div class="flex items-center gap-1 font-mono text-[10px] muted mt-0.5" title="Full SHA-256: ${sha}">
          <span class="font-bold text-slate-700 dark:text-slate-300">${shortSha}</span>
          <button type="button" class="muted hover:text-sky-500 p-0.5" onclick="copyHistorySha('${sha}', event)" title="Copy SHA-256">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
        </div>
      `
      : "";

    // Diagnostics / Log Message
    let diagHtml = "";
    if (isFailed && job.failure) {
      diagHtml = `
        <div class="p-2 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-300 space-y-0.5 max-w-[260px]">
          <div class="font-bold text-[10px] uppercase tracking-wider text-rose-600 dark:text-rose-400 flex items-center gap-1">
            <svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>${escapeHtml(job.failure.stage || "EXECUTION")}</span>
            <span class="opacity-60">•</span>
            <span>${escapeHtml(job.failure.code || "FAIL")}</span>
          </div>
          <div class="text-[11px] leading-tight break-words font-mono line-clamp-2" title="${escapeHtml(job.failure.message || '')}">
            ${escapeHtml(job.failure.message || "Failed without specific error")}
          </div>
        </div>
      `;
    } else if (isSuccess) {
      const changeMsg = change === "no_change" 
        ? "CAS Deduplicated (Config unchanged)" 
        : change === "baseline" 
          ? "Initial baseline snapshot created" 
          : "Configuration changed & backed up";
      diagHtml = `
        <div class="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
          <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          <span class="truncate max-w-[240px]" title="${changeMsg}">${changeMsg}</span>
        </div>
      `;
    } else if (isRunning) {
      diagHtml = `
        <div class="flex items-center gap-1.5 text-xs text-sky-600 dark:text-sky-400 font-medium animate-pulse">
          <span class="w-2 h-2 rounded-full bg-sky-500 animate-ping"></span>
          <span>Running backup worker...</span>
        </div>
      `;
    } else {
      diagHtml = `<span class="muted text-xs">-</span>`;
    }

    // Action: Download Snapshot
    let actionHtml = `<span class="text-muted block text-right pr-2">-</span>`;
    if (job.snapshot && job.snapshot.id) {
      if (!isViewer) {
        const downloadUrl = window.api.snapshots.downloadUrl(job.snapshot.id);
        const filename = escapeHtml(job.snapshot.display_filename || "backup_config");
        actionHtml = `
          <div class="flex items-center justify-end gap-1.5 ml-auto">
            <a href="${downloadUrl}" download="${filename}"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold btn-primary shadow-sm hover:opacity-90 active:scale-95 transition-transform"
              title="Download ${filename} from Ceph S3">
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              <span>Download</span>
            </a>
          </div>
        `;
      } else {
        actionHtml = `
          <div class="flex items-center justify-end gap-1.5 ml-auto">
            <span class="text-[10px] muted px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border line" title="Viewer cannot download files">Locked</span>
          </div>
        `;
      }
    }

    return `
      <tr class="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
        <td class="py-2.5 px-3 whitespace-nowrap">
          <div class="font-semibold text-xs text-slate-800 dark:text-slate-200">${timeInfo.dateStr}</div>
          <div class="muted text-[10px] font-mono">${timeInfo.timeStr}</div>
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          ${triggerPill}
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          ${statusPill}
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          ${changePill}
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap font-mono text-xs">
          ${sizeStr}
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap font-mono text-xs">
          ${durationStr}
        </td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          ${retentionHtml}
          ${shaHtml}
        </td>
        <td class="py-2.5 px-3">
          ${diagHtml}
        </td>
        <td class="py-2.5 px-3 text-right whitespace-nowrap">
          ${actionHtml}
        </td>
      </tr>
    `;
  }).join("");
}

// Bind modal close buttons
document.addEventListener("DOMContentLoaded", () => {
  const closeBtn = document.getElementById("history-close-btn");
  const closeX = document.getElementById("history-close-x");
  const dialog = document.getElementById("backup-history-dialog");

  if (closeBtn && dialog) {
    closeBtn.addEventListener("click", () => window.closeDialog(dialog));
  }
  if (closeX && dialog) {
    closeX.addEventListener("click", () => window.closeDialog(dialog));
  }
  if (dialog) {
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) {
        window.closeDialog(dialog);
      }
    });
  }
});
