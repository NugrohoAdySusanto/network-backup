// Devices Rendering Logic
const inform = (...args) => (window.inform ? window.inform(...args) : console.log(...args));

let allDevices = [];
let driversList = [];

// Helper: Format Model with Brand/Vendor + Model
function formatDeviceModel(d) {
  if (!d) return "-";
  const vendor = (d.vendor || "").trim();
  const model = (d.model || "").trim();
  if (vendor && model) {
    if (model.toLowerCase().startsWith(vendor.toLowerCase())) {
      return model;
    }
    return `${vendor} ${model}`;
  }
  return vendor || model || "-";
}
window.formatDeviceModel = formatDeviceModel;

// Helper: Format Time in standard English locale
const displayTime = dateString => {
  if (!dateString) return "Not yet";
  const date = new Date(dateString);
  return date.toLocaleString("en-US", { month: "short", day: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

async function loadDrivers() {
  try {
    const res = await window.api.drivers.list();
    driversList = res.items || [];
    window.driversList = driversList;
  } catch (e) {
    console.error("Failed to load drivers", e);
  }
}

async function loadDevices(isSilent = false) {
  try {
    if (driversList.length === 0) {
      await loadDrivers();
    }
    
    const res = await window.api.devices.list({ limit: 100 });
    allDevices = res.items || [];
    window.allDevices = allDevices;
    applyDeviceSearchFilter();
    await updateSummary(allDevices);
  } catch (e) {
    console.error("Failed to load devices", e);
    if (!isSilent) {
      inform("Failed to load devices: " + e.message, true);
    }
  }
}

async function updateSummary(devices) {
  try {
    const res = await window.api.dashboard.summary();
    const summary = res || {};
    
    const countEl = document.getElementById("device-count");
    if (countEl) countEl.textContent = `${summary.total_devices ?? devices.length} devices`;

    // Zabbix sync status
    const zabbix = summary.zabbix || {};
    const isSynced = zabbix.is_synced !== undefined ? Boolean(zabbix.is_synced) : (zabbix.status === "OK");
    const zabbixStatusEl = document.getElementById("zabbix-sync-status");
    const zabbixTextEl = document.getElementById("zabbix-sync-text");
    if (zabbixStatusEl) {
      zabbixStatusEl.setAttribute("data-status", isSynced ? "active" : "non-active");
      zabbixStatusEl.title = `Zabbix Sync: ${isSynced ? "Sync" : "Not-Sync"}`;
      if (zabbixTextEl) {
        zabbixTextEl.textContent = isSynced ? "Sync" : "Not-Sync";
      } else {
        zabbixStatusEl.textContent = isSynced ? "Sync" : "Not-Sync";
      }
    }

    const successRateEl = document.getElementById("backup-success-rate");
    if (successRateEl) {
      const rateVal = (summary.scheduled_devices_today > 0) ? (summary.backup_success_rate_today ?? 0) : 0;
      successRateEl.textContent = `${rateVal}%`;
    }

    const successSubEl = document.getElementById("backup-success-sub");
    if (successSubEl) {
      successSubEl.textContent = `${summary.successful_devices_today ?? 0} / ${summary.scheduled_devices_today ?? 0}`;
    }

    // Storage Cluster / Ceph Health card visibility
    const isCeph = Boolean(summary.is_ceph_storage);
    const ceph = summary.ceph;
    const cephCard = document.getElementById("ceph-health-card");
    const summarySection = cephCard ? cephCard.closest("section") : null;

    if (cephCard) {
      if (isCeph && ceph) {
        cephCard.classList.remove("hidden");
        if (summarySection) {
          summarySection.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 sm:gap-4 pt-4 sm:pt-6 pb-2";
        }
        const cephDot = document.getElementById("ceph-health-dot");
        const cephLabel = document.getElementById("ceph-health-label");
        const cephStatus = ceph.status || "UNKNOWN";

        if (cephLabel && cephDot) {
          cephLabel.textContent = cephStatus;
          cephCard.title = `Ceph Health: ${cephStatus}\nSummary: ${ceph.summary || 'Cluster status'}`;
          if (cephStatus === "HEALTH_OK") {
            cephDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block";
            cephLabel.className = "text-emerald-600 dark:text-emerald-400 font-bold";
          } else if (cephStatus === "HEALTH_WARN") {
            cephDot.className = "w-2.5 h-2.5 rounded-full bg-amber-500 inline-block animate-pulse";
            cephLabel.className = "text-amber-600 dark:text-amber-400 font-bold";
          } else if (cephStatus === "HEALTH_ERR") {
            cephDot.className = "w-2.5 h-2.5 rounded-full bg-red-500 inline-block animate-pulse";
            cephLabel.className = "text-red-600 dark:text-red-400 font-bold";
          } else {
            cephDot.className = "w-2.5 h-2.5 rounded-full bg-slate-400 inline-block";
            cephLabel.className = "text-slate-500 font-bold";
          }
        }
      } else {
        // Hide Ceph Cluster Health card if active storage is not Ceph (e.g. MinIO or disconnected)
        cephCard.classList.add("hidden");
        if (summarySection) {
          summarySection.className = "grid grid-cols-1 sm:grid-cols-2 gap-3.5 sm:gap-4 pt-4 sm:pt-6 pb-2";
        }
      }
    }

    // Update bottom notice bar
    const noticeEl = document.getElementById("notice");
    const noticeDot = document.getElementById("notice-dot");
    if (noticeEl) {
      const timeStr = new Date().toLocaleTimeString();
      let storageNote = "Storage: Not Connected";
      if (isCeph && ceph) {
        storageNote = `Ceph: ${ceph.status || 'UNKNOWN'}`;
      } else if (summary.active_storage && summary.active_storage.name) {
        storageNote = `Storage: ${summary.active_storage.name}`;
      }
      noticeEl.textContent = `Auto-synchronized with Zabbix (${summary.total_devices ?? devices.length} devices) • ${storageNote} • Last refreshed at ${timeStr}`;
    }
    if (noticeDot) {
      noticeDot.classList.remove("hidden");
      noticeDot.className = "w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse";
    }
  } catch (err) {
    console.warn("Failed to fetch dashboard summary, fallback to local counts:", err);
    const countEl = document.getElementById("device-count");
    if (countEl) countEl.textContent = `${devices.length} devices`;
    const zabbixStatusEl = document.getElementById("zabbix-sync-status");
    const zabbixTextEl = document.getElementById("zabbix-sync-text");
    if (zabbixStatusEl) {
      const isSynced = devices.length > 0;
      zabbixStatusEl.setAttribute("data-status", isSynced ? "active" : "non-active");
      zabbixStatusEl.title = `Zabbix Sync: ${isSynced ? "Sync" : "Not-Sync"}`;
      if (zabbixTextEl) {
        zabbixTextEl.textContent = isSynced ? "Sync" : "Not-Sync";
      } else {
        zabbixStatusEl.textContent = isSynced ? "Sync" : "Not-Sync";
      }
    }
  }
}

const isDeviceActive = d => (d.availability_status === "up");

function renderDevicesTable(devices, searchQuery = "") {
  const tbody = document.getElementById("device-rows");
  tbody.innerHTML = "";
  
  if (devices.length === 0) {
    if (searchQuery) {
      const safeQuery = searchQuery.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      tbody.innerHTML = `<tr><td colspan="11" class="text-center muted py-8">
        No devices found matching "<span class="font-semibold text-ink">${safeQuery}</span>".
        <button type="button" class="ml-2 text-sky-500 hover:underline font-semibold text-xs" onclick="window.clearDeviceSearch && window.clearDeviceSearch()">Clear search</button>
      </td></tr>`;
    } else {
      tbody.innerHTML = `<tr><td colspan="11" class="text-center muted py-8">No devices found. Run Zabbix Sync to import devices.</td></tr>`;
    }
    return;
  }
  
  const template = document.getElementById("row-template");
  
  devices.forEach(d => {
    let row;
    if (template) {
      row = template.content.firstElementChild.cloneNode(true);
    } else {
      row = document.createElement("tr");
      // Fallback row creation... (simplified)
      return;
    }
    
    row.dataset.rowId = d.id;

    const hostnameEl = row.querySelector(".row-hostname");
    if (hostnameEl) {
      hostnameEl.textContent = d.hostname || '-';
      hostnameEl.title = d.hostname || '-';
    }
    row.querySelector(".row-ip").textContent = d.ip_address || '-';
    row.querySelector(".row-model").textContent = formatDeviceModel(d);

    // Status (Active / Non-Active)
    const statusWrap = row.querySelector(".status-cell-wrapper");
    const statusLabel = row.querySelector(".status-label");
    const deviceStatusPrint = row.querySelector(".status-print");
    const isActive = isDeviceActive(d);
    
    const displayStatus = isActive ? "Active" : "Non-Active";
    if (statusWrap) {
      statusWrap.setAttribute("data-status", isActive ? "active" : "non-active");
      statusWrap.title = `Device status: ${displayStatus}`;
    }
    if (statusLabel) {
      statusLabel.textContent = displayStatus;
    }
    if (deviceStatusPrint) {
      deviceStatusPrint.textContent = displayStatus;
    }

    // Worker select (Driver)
    const workerSelect = row.querySelector(".worker-select");
    workerSelect.innerHTML = `<option value="">-- Unassigned --</option>` + 
      driversList.map(driver => `<option value="${driver.key}">${driver.label || driver.name || driver.key}</option>`).join("");
    
    if (d.backup_settings && d.backup_settings.driver_key) {
      workerSelect.value = d.backup_settings.driver_key;
    }

    // Role-based restrictions
    const currentUser = window.authModule ? window.authModule.currentUser() : null;
    const isViewer = currentUser && currentUser.role === 'viewer';
    
    if (isViewer) {
      workerSelect.disabled = true;
      row.querySelector(".backup-now-btn").disabled = true;
      row.querySelector(".backup-schedule-btn").disabled = true;
      row.querySelector(".save-btn").disabled = true;
      row.querySelector(".clear-btn").disabled = true;
    }

    // Backup Status Column
    const statusBadge = row.querySelector(".backup-status-badge");
    const statusDot = row.querySelector(".backup-status-dot");
    const backupStatusTextEl = row.querySelector(".backup-status-text");
    const statusPrint = row.querySelector(".backup-status-print");

    if (statusBadge) {
      if (d.last_backup) {
        const isSuccess = d.last_backup.status === "success" || 
          d.last_backup.state === "SUCCESS_NO_CHANGE" || 
          d.last_backup.state === "SUCCESS_CHANGED" ||
          d.last_backup.state === "SUCCESS" ||
          (!d.last_backup.status && d.last_backup.captured_at && !d.last_backup.failure_message);

        const isFailed = d.last_backup.status === "failed" ||
          d.last_backup.state === "FAILED" ||
          (d.last_backup.state && d.last_backup.state.startsWith("SKIPPED"));

        const isRunning = d.last_backup.status === "running" ||
          ["QUEUED", "RUNNING", "CONNECTING", "AUTHENTICATING", "DISCOVERING", "EXTRACTING", "VALIDATING", "HASHING", "UPLOADING"].includes(d.last_backup.state);

        if (isSuccess) {
          const change = (d.last_backup.change_status || "").toLowerCase();
          let label = "Success";
          if (change === "no_change") label = "Success (No Change)";
          else if (change === "changed") label = "Success (Changed)";
          else if (change === "baseline") label = "Success (Baseline)";

          statusBadge.className = "backup-status-badge no-print rounded-full px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20 active:scale-95";
          if (statusDot) statusDot.className = "backup-status-dot w-2 h-2 rounded-full bg-emerald-500 inline-block";
          if (backupStatusTextEl) backupStatusTextEl.textContent = label;
          statusBadge.title = `Last backup succeeded (${label}) • Click to view full backup history log`;
          if (statusPrint) statusPrint.textContent = label;
        } else if (isFailed) {
          const rawCode = (d.last_backup.failure_code || d.last_backup.state || "").toUpperCase();
          const errMsg = d.last_backup.failure_message || d.last_backup.failure_code || "Failed";
          
          let label = "Failed";
          let badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          let dotColorClass = "bg-rose-500 animate-pulse";

          if (rawCode === "STORAGE_DISCONNECTED") {
            label = "Storage Disconnected";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "STORAGE_UNAVAILABLE") {
            label = "Storage Unavailable";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "CONNECTION_TIMEOUT") {
            label = "Connection Timeout";
            badgeBorderClass = "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20";
            dotColorClass = "bg-amber-500 animate-pulse";
          } else if (rawCode === "COMMAND_TIMEOUT") {
            label = "Command Timeout";
            badgeBorderClass = "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20";
            dotColorClass = "bg-amber-500 animate-pulse";
          } else if (rawCode === "AUTHENTICATION_FAILED") {
            label = "Auth Failed";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "DEVICE_DOWN" || rawCode === "SKIPPED_DEVICE_DOWN") {
            label = "Device Down";
            badgeBorderClass = "border-slate-500/30 bg-slate-500/10 text-slate-700 dark:text-slate-400 hover:bg-slate-500/20";
            dotColorClass = "bg-slate-400";
          } else if (rawCode === "STATUS_UNKNOWN" || rawCode === "SKIPPED_STATUS_UNKNOWN") {
            label = "Status Unknown";
            badgeBorderClass = "border-slate-500/30 bg-slate-500/10 text-slate-700 dark:text-slate-400 hover:bg-slate-500/20";
            dotColorClass = "bg-slate-400";
          } else if (rawCode === "DRIVER_NOT_ASSIGNED") {
            label = "Worker Unassigned";
            badgeBorderClass = "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20";
            dotColorClass = "bg-amber-500 animate-pulse";
          } else if (rawCode === "DRIVER_NOT_FOUND") {
            label = "Worker Not Found";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "SSH_TRANSPORT_ERROR") {
            label = "SSH Transport Error";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "S3_VERIFICATION_FAILED") {
            label = "S3 Verify Failed";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "OBJECT_NOT_FOUND_IN_STORAGE") {
            label = "Object Not In S3";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode === "COMMAND_FAILED") {
            label = "Command Failed";
            badgeBorderClass = "border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-400 hover:bg-rose-500/20";
          } else if (rawCode) {
            label = rawCode.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
          }

          statusBadge.className = `backup-status-badge no-print rounded-full px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer border ${badgeBorderClass} active:scale-95`;
          if (statusDot) statusDot.className = `backup-status-dot w-2 h-2 rounded-full ${dotColorClass} inline-block`;
          if (backupStatusTextEl) backupStatusTextEl.textContent = label;
          statusBadge.title = `Last backup failed: ${errMsg} (${label}) • Click to view full backup history log`;
          if (statusPrint) statusPrint.textContent = label;
        } else if (isRunning) {
          statusBadge.className = "backup-status-badge no-print rounded-full px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400 hover:bg-amber-500/20 active:scale-95";
          if (statusDot) statusDot.className = "backup-status-dot w-2 h-2 rounded-full bg-amber-500 inline-block animate-ping";
          if (backupStatusTextEl) backupStatusTextEl.textContent = "Running";
          statusBadge.title = "Backup execution in progress • Click to view history log";
          if (statusPrint) statusPrint.textContent = "Running";
        } else {
          statusBadge.className = "backup-status-badge no-print rounded-full px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer border border-slate-500/20 bg-slate-500/10 text-slate-600 dark:text-slate-400 hover:bg-slate-500/20 active:scale-95";
          if (statusDot) statusDot.className = "backup-status-dot w-2 h-2 rounded-full bg-slate-400 inline-block";
          if (backupStatusTextEl) backupStatusTextEl.textContent = d.last_backup.state || "Unknown";
          statusBadge.title = `Status: ${d.last_backup.state} • Click to view full backup history log`;
          if (statusPrint) statusPrint.textContent = d.last_backup.state || "-";
        }
      } else {
        // No backup recorded yet
        statusBadge.className = "backup-status-badge no-print rounded-full px-2.5 py-1 text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm cursor-pointer border border-slate-500/20 bg-slate-500/10 text-slate-500 dark:text-slate-400 hover:bg-slate-500/20 active:scale-95";
        if (statusDot) statusDot.className = "backup-status-dot w-2 h-2 rounded-full bg-slate-400 inline-block";
        if (backupStatusTextEl) backupStatusTextEl.textContent = "No Backup";
        statusBadge.title = "No backup record yet • Click to view device history";
        if (statusPrint) statusPrint.textContent = "No Backup";
      }

      // Click handler: opens full backup execution history modal
      statusBadge.onclick = (e) => {
        e.stopPropagation();
        if (window.openBackupHistoryModal) {
          window.openBackupHistoryModal(d);
        }
      };
    }

    // Last Backup
    const rowLast = row.querySelector(".row-last");
    const schedIndicator = row.querySelector(".schedule-indicator");
    if (d.last_backup && d.last_backup.captured_at) {
      const dt = new Date(d.last_backup.captured_at);
      const timePart = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const datePart = dt.toLocaleDateString([], { month: 'short', day: 'numeric' });
      const status = (d.last_backup.change_status || "").toLowerCase();
      let statusTag = "";
      if (status === "baseline") statusTag = " • Baseline";
      else if (status === "changed") statusTag = " • Changed";
      else if (status === "no_change") statusTag = " • No Change";
      rowLast.textContent = `${datePart} ${timePart}${statusTag}`;
      if (d.last_backup.status === "failed") {
        rowLast.className = "row-last text-xs font-semibold block text-rose-600 dark:text-rose-400";
      } else {
        rowLast.className = "row-last text-xs font-semibold block text-emerald-600 dark:text-emerald-400";
      }
    } else {
      rowLast.textContent = "Not yet";
      rowLast.className = "row-last text-xs font-medium muted block";
    }

    if (d.backup_settings && d.backup_settings.schedule_enabled && d.backup_settings.daily_time) {
      schedIndicator.textContent = `Daily @ ${d.backup_settings.daily_time}`;
    } else {
      schedIndicator.textContent = "";
    }

    // Next Backup (integrated with DB next_run_at & retention)
    const rowNext = row.querySelector(".row-next-backup");
    const nextIndicator = row.querySelector(".next-schedule-indicator");
    if (d.backup_settings && d.backup_settings.next_run_at) {
      const nextDt = new Date(d.backup_settings.next_run_at);
      const now = new Date();
      const diffMin = Math.round((nextDt - now) / 60000);
      let relText = "";
      if (diffMin <= 1 && diffMin >= 0) relText = "in 1 min";
      else if (diffMin > 1 && diffMin < 60) relText = `in ${diffMin} mins`;
      else if (diffMin < 0 && diffMin >= -5) relText = "due now";
      else relText = `${nextDt.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${nextDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

      const retBadge = d.backup_settings.retention_policy === "smart_7_4_12_3" ? "Smart Ret." : "31 Days";
      if (rowNext) {
        rowNext.textContent = `${nextDt.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${nextDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
        rowNext.className = "row-next-backup text-xs font-semibold text-sky-600 dark:text-sky-400 block";
      }
      if (nextIndicator) {
        nextIndicator.textContent = `${relText} • ${retBadge}`;
      }
    } else if (d.backup_settings && d.backup_settings.schedule_enabled && d.backup_settings.daily_time) {
      if (rowNext) {
        rowNext.textContent = `Daily ${d.backup_settings.daily_time}`;
        rowNext.className = "row-next-backup text-xs font-medium text-amber-600 dark:text-amber-400 block";
      }
      if (nextIndicator) {
        const retBadge = d.backup_settings.retention_policy === "smart_7_4_12_3" ? "Smart Ret." : "31 Days";
        nextIndicator.textContent = retBadge;
      }
    } else {
      if (rowNext) {
        rowNext.textContent = "-";
        rowNext.className = "row-next-backup text-xs font-medium muted block";
      }
      if (nextIndicator) {
        nextIndicator.textContent = "";
      }
    }

    // Retention badge (only show if automated schedule is active for this device)
    const pill = row.querySelector(".device-retention-pill");
    const isSchedActive = d._pending?.schedule_enabled !== undefined 
      ? Boolean(d._pending.schedule_enabled) 
      : Boolean(d.backup_settings?.schedule_enabled && d.backup_settings?.daily_time);

    if (pill) {
      if (isSchedActive) {
        pill.classList.remove("hidden");
        const retention = (d._pending?.retention_policy !== undefined 
          ? d._pending.retention_policy 
          : d.backup_settings?.retention_policy) || "standard_31";
        if (retention.includes("smart")) {
          pill.textContent = "Smart Ret.";
          pill.title = "Smart Retention Policy (7D / 4W / 12M / 3Y)";
          pill.className = "device-retention-pill font-mono text-[10px] px-2.5 py-0.5 rounded-md border border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400 font-semibold flex-shrink-0 ml-auto text-right";
        } else {
          pill.textContent = "31 Days";
          pill.title = "31 Days Retention Policy (31 daily snapshots)";
          pill.className = "device-retention-pill font-mono text-[10px] px-2.5 py-0.5 rounded-md border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400 font-semibold flex-shrink-0 ml-auto text-right";
        }
      } else {
        pill.textContent = "";
        pill.classList.add("hidden");
      }
    }

    // Events: workerSelect marks row as dirty (requires clicking Save to persist)
    workerSelect.addEventListener("change", e => {
      d._pending = d._pending || {};
      d._pending.driver_key = workerSelect.value || null;
      d._pending.isDirty = true;

      const saveBtn = row.querySelector(".save-btn");
      if (saveBtn) {
        saveBtn.className = "save-btn btn-success rounded-lg px-2.5 py-1.5 text-xs font-semibold shadow-sm";
        saveBtn.textContent = "Save Changes";
        saveBtn.title = "You have unsaved changes. Click to persist.";
      }
      inform(`Selected worker: ${workerSelect.value || 'None'}. Click "Save" in the ACTIONS column to apply changes.`);
    });

    const trigger = row.querySelector(".backup-trigger");
    const backupMenu = row.querySelector(".backup-menu");
    if (trigger && backupMenu) {
      trigger.addEventListener("click", e => {
        e.stopPropagation();
        toggleMenu(trigger, backupMenu);
      });
    }

    row.querySelector(".backup-now-btn").addEventListener("click", async () => {
      closeMenus();
      try {
        inform(`Queuing backup task for ${d.hostname}...`);
        await window.api.devices.backupNow(d.id);
        inform(`Backup task for ${d.hostname} queued. Execution will begin in 1 minute.`);
        setTimeout(() => loadDevices(false), 1500);
        setTimeout(() => loadDevices(false), 65000);
      } catch (err) {
        inform(`Failed to trigger backup for ${d.hostname}: ${err.message}`, true);
        await loadDevices(false);
      }
    });

    row.querySelector(".backup-schedule-btn").addEventListener("click", () => {
      closeMenus();
      if (!isDeviceActive(d)) {
        inform(`${d.hostname} is DOWN. Cannot schedule backup for an offline device.`, true);
        return;
      }
      openScheduleDialog(d);
    });

    const downloadBtn = row.querySelector(".download-btn");
    const hasDownloadableSnapshot = Boolean(d.last_backup && d.last_backup.id);
    if (!hasDownloadableSnapshot) {
      downloadBtn.disabled = true;
      downloadBtn.classList.add("opacity-30", "cursor-not-allowed");
      downloadBtn.title = "No backup archive available to download for this repository";
    } else {
      downloadBtn.disabled = false;
      downloadBtn.classList.remove("opacity-30", "cursor-not-allowed");
      downloadBtn.title = "View and download backup archives for this device";
    }

    downloadBtn.addEventListener("click", () => {
      if (!hasDownloadableSnapshot) {
        inform("No backup archive available to download for this repository.", true);
        return;
      }
      if (isViewer) {
         inform("Viewer role cannot download archives", true);
         return;
      }
      openDownloadModal(d);
    });

    const saveBtn = row.querySelector(".save-btn");
    saveBtn.addEventListener("click", async () => {
      try {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        const finalDriver = d._pending?.driver_key !== undefined 
          ? d._pending.driver_key 
          : (workerSelect.value || d.backup_settings?.driver_key || null);

        const finalScheduleEnabled = d._pending?.schedule_enabled !== undefined 
          ? d._pending.schedule_enabled 
          : (d.backup_settings?.schedule_enabled || false);

        const finalDailyTime = d._pending?.daily_time !== undefined 
          ? d._pending.daily_time 
          : (d.backup_settings?.daily_time || null);

        const finalRetention = finalScheduleEnabled
          ? (d._pending?.retention_policy !== undefined 
              ? d._pending.retention_policy 
              : (d.backup_settings?.retention_policy || 'standard_31'))
          : 'standard_31';

        await window.api.settings.update(
          d.id, 
          finalDriver, 
          finalScheduleEnabled, 
          finalDailyTime, 
          finalRetention
        );

        d._pending = null;
        inform(`Settings for ${d.hostname} saved.`);
        await loadDevices();
      } catch (err) {
        inform(`Error saving settings: ${err.message}`, true);
        saveBtn.disabled = false;
        saveBtn.textContent = "Save Changes";
      }
    });

    const clearBtn = row.querySelector(".clear-btn");
    if (clearBtn) {
      clearBtn.addEventListener("click", async () => {
        try {
          clearBtn.disabled = true;
          workerSelect.value = "";
          d._pending = null;
          await window.api.settings.update(
            d.id, 
            null, 
            false, 
            null, 
            'standard_31'
          );
          inform(`Settings for ${d.hostname} reset to default.`);
          await loadDevices();
        } catch (err) {
          inform(`Error clearing settings: ${err.message}`, true);
          clearBtn.disabled = false;
        }
      });
    }

    tbody.appendChild(row);
  });
}

// Dialog open helpers
function openScheduleDialog(d) {
  if (window.openScheduleDialog) {
    window.openScheduleDialog(d);
  }
}

// Auto-refresh timer (polls every 20s according to API-CONTRACT-v1.0.md spec)
const AUTO_REFRESH_INTERVAL_MS = 20000;
let autoRefreshTimer = null;

function hasUnsavedChanges() {
  return allDevices.some(d => d._pending && d._pending.isDirty);
}

function startAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(async () => {
    const isAuth = window.authModule && window.authModule.currentUser();
    const isTabVisible = !document.hidden;
    const isModalOpen = !!document.querySelector('.dialog-backdrop:not(.hidden)');
    const isMenuOpen = !!document.querySelector('.pop-menu:not([hidden])');
    const hasUnsaved = hasUnsavedChanges();

    if (isAuth && isTabVisible && !isModalOpen && !isMenuOpen && !hasUnsaved) {
      try {
        await loadDevices(true);
      } catch (e) {
        console.warn("Auto-refresh silent error:", e);
      }
    }
  }, AUTO_REFRESH_INTERVAL_MS);
}

// =========================================================================
// SEARCH & FILTER DEVICES (Responsive Expandable Search)
// =========================================================================
function applyDeviceSearchFilter() {
  const searchInput = document.getElementById("device-search-input");
  const query = (searchInput ? searchInput.value : "").trim().toLowerCase();
  
  // Toggle clear button visibility
  const clearBtn = document.getElementById("device-search-clear-btn");
  if (clearBtn) {
    if (query) {
      clearBtn.classList.remove("hidden");
    } else {
      clearBtn.classList.add("hidden");
    }
  }

  // Active indicator dot on expandable toggle button for mobile/tablet
  const activeDot = document.getElementById("device-search-active-dot");
  if (activeDot) {
    if (query) {
      activeDot.classList.remove("hidden");
    } else {
      activeDot.classList.add("hidden");
    }
  }

  if (!query) {
    renderDevicesTable(allDevices);
    return;
  }

  const filtered = allDevices.filter(d => {
    const hostname = (d.hostname || "").toLowerCase();
    const ip = (d.ip_address || "").toLowerCase();
    const model = formatDeviceModel(d).toLowerCase();
    const vendor = (d.vendor || "").toLowerCase();
    const status = (d.availability_status === "up" ? "active" : "non-active");
    const driver = (d.backup_settings?.driver_key || "").toLowerCase();
    
    return hostname.includes(query) ||
           ip.includes(query) ||
           model.includes(query) ||
           vendor.includes(query) ||
           status.includes(query) ||
           driver.includes(query);
  });

  renderDevicesTable(filtered, query);
}
window.applyDeviceSearchFilter = applyDeviceSearchFilter;

function clearDeviceSearch() {
  const input = document.getElementById("device-search-input");
  if (input) {
    input.value = "";
    applyDeviceSearchFilter();
    input.focus();
  }
}
window.clearDeviceSearch = clearDeviceSearch;

function initDeviceSearch() {
  const toggleBtn = document.getElementById("device-search-toggle-btn");
  const container = document.getElementById("device-search-container");
  const input = document.getElementById("device-search-input");
  const closeBtn = document.getElementById("device-search-close-btn");
  const clearBtn = document.getElementById("device-search-clear-btn");

  if (!toggleBtn || !container || !input) return;

  function openMobileSearch() {
    toggleBtn.classList.add("hidden");
    container.classList.remove("hidden");
    container.classList.add("flex");
    toggleBtn.setAttribute("aria-expanded", "true");
    input.focus();
  }

  function closeMobileSearch() {
    container.classList.add("hidden");
    container.classList.remove("flex");
    toggleBtn.classList.remove("hidden");
    toggleBtn.setAttribute("aria-expanded", "false");
  }

  toggleBtn.addEventListener("click", openMobileSearch);

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      closeMobileSearch();
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      clearDeviceSearch();
    });
  }

  input.addEventListener("input", () => {
    applyDeviceSearchFilter();
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (input.value) {
        clearDeviceSearch();
      } else {
        closeMobileSearch();
      }
    }
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth >= 1024) {
      container.classList.remove("hidden");
      container.classList.add("lg:flex");
    } else {
      if (!input.value && document.activeElement !== input) {
        closeMobileSearch();
      }
    }
  });
}
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDeviceSearch);
} else {
  initDeviceSearch();
}

// Handle Zabbix Sync manually & Auto-refresh startup
document.addEventListener("DOMContentLoaded", () => {
  initDeviceSearch();
  startAutoRefresh();

  if (window.authModule && window.authModule.currentUser()) {
    loadDevices();
  }

  // Sync button on notice bar
  const noticeDot = document.getElementById("notice-dot");
  if (noticeDot) {
    noticeDot.parentElement.addEventListener('click', async () => {
       inform("Starting manual Zabbix sync...");
       try {
         await window.api.devices.syncZabbix();
         inform("Zabbix sync queued. Devices will update soon.");
         setTimeout(() => loadDevices(false), 3000);
       } catch (err) {
         inform("Zabbix sync failed: " + err.message, true);
       }
    });
    noticeDot.parentElement.style.cursor = 'pointer';
    noticeDot.parentElement.title = 'Click to trigger manual sync with Zabbix';
  }
});


window.devicesModule = {
  loadDevices,
  startAutoRefresh,
  applyDeviceSearchFilter,
  clearDeviceSearch,
  initDeviceSearch,
  getDeviceById: (id) => allDevices.find(d => d.id === id)
};

// =========================================================================
// EXPORT CSV & PRINT PDF CONTROLS (Handled by reports.js)
// =========================================================================
// CSV and PDF export modal with date range and analytical charts
// is managed in reports.js.
