// Archives Logic - Real Snapshot & S3 Download Integration
let currentDownloadDevice = null;
let currentDownloadPolicy = "standard_31";
let allDeviceSnapshots = [];

window.openDownloadModal = async function(device) {
  currentDownloadDevice = device;
  currentDownloadPolicy = device.backup_settings?.retention_policy || "standard_31";

  const statusText = (device.availability_status || "UNKNOWN").toUpperCase();
  const modelText = window.formatDeviceModel 
    ? window.formatDeviceModel(device) 
    : ((device.vendor ? `${device.vendor} ` : '') + (device.model || '-'));
    
  document.getElementById("download-title").textContent = `Backup Archives: ${device.hostname}`;
  document.getElementById("download-subtitle").textContent = 
    `IP: ${device.ip_address} • Model: ${modelText} • Worker: ${device.backup_settings?.driver_key || 'None'} • Status: ${statusText}`;

  document.getElementById("download-search").value = "";

  // Set initial policy tab styling
  updatePolicyTabUI();

  const tbodyList = document.getElementById("download-list-rows");
  if (tbodyList) {
    tbodyList.innerHTML = `
      <tr>
        <td colspan="6" class="text-center py-8 muted">
          <div class="flex items-center justify-center gap-2">
            <span class="w-2 h-2 rounded-full bg-sky-500 animate-ping"></span>
            <span>Loading backup archives from Ceph S3...</span>
          </div>
        </td>
      </tr>
    `;
  }

  window.openDialog(
    document.getElementById("download-dialog"), 
    document.getElementById("download-close-btn")
  );

  // Fetch real snapshots from API
  try {
    const res = await window.api.snapshots.listForDevice(device.id);
    allDeviceSnapshots = res.items || [];
    updatePolicyCounts();
    renderSnapshotsList();
  } catch (err) {
    console.error("Failed to load snapshots:", err);
    if (tbodyList) {
      tbodyList.innerHTML = `
        <tr>
          <td colspan="6" class="text-center py-8 text-red-500">
            Failed to retrieve backup archives: ${err.message}
          </td>
        </tr>
      `;
    }
  }
};

function updatePolicyCounts() {
  const count31 = allDeviceSnapshots.filter(s => s.retention_policy_at_capture === "standard_31").length;
  const countSmart = allDeviceSnapshots.filter(s => s.retention_policy_at_capture === "smart_7_4_12_3").length;

  const b31 = document.getElementById("count-badge-31");
  const bSmart = document.getElementById("count-badge-smart");
  if (b31) b31.textContent = `${count31} files`;
  if (bSmart) bSmart.textContent = `${countSmart} files`;
}

function updatePolicyTabUI() {
  const tab31 = document.getElementById("tab-policy-31");
  const tabSmart = document.getElementById("tab-policy-smart");
  const badge = document.getElementById("download-policy-badge");
  const bannerText = document.getElementById("policy-banner-text");

  if (currentDownloadPolicy === "standard_31") {
    if (tab31) tab31.className = "policy-tab active px-3.5 py-1.5 rounded-lg transition-all text-sky-600 dark:text-sky-400 font-bold bg-white dark:bg-slate-800 shadow-sm";
    if (tabSmart) tabSmart.className = "policy-tab px-3.5 py-1.5 rounded-lg transition-all muted hover:text-inherit";
    if (badge) {
      badge.textContent = "31 Days Retention";
      badge.className = "font-mono text-[11px] font-bold px-2.5 py-0.5 rounded-full border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400";
    }
    if (bannerText) {
      bannerText.textContent = "Displaying consecutive daily backup snapshots for 31-day retention.";
    }
  } else {
    if (tabSmart) tabSmart.className = "policy-tab active px-3.5 py-1.5 rounded-lg transition-all text-purple-600 dark:text-purple-400 font-bold bg-white dark:bg-slate-800 shadow-sm";
    if (tab31) tab31.className = "policy-tab px-3.5 py-1.5 rounded-lg transition-all muted hover:text-inherit";
    if (badge) {
      badge.textContent = "Smart Retention (7D/4W/12M/3Y)";
      badge.className = "font-mono text-[11px] font-bold px-2.5 py-0.5 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-600 dark:text-purple-400";
    }
    if (bannerText) {
      bannerText.textContent = "Displaying Grandfather-Father-Son (GFS) tiered smart retention snapshots.";
    }
  }
}

window.switchDownloadPolicy = function(policyKey) {
  if (policyKey === "31") {
    currentDownloadPolicy = "standard_31";
  } else {
    currentDownloadPolicy = "smart_7_4_12_3";
  }
  updatePolicyTabUI();
  renderSnapshotsList();
};

window.filterBackupsList = function() {
  renderSnapshotsList();
};

function renderSnapshotsList() {
  const tbody = document.getElementById("download-list-rows");
  if (!tbody) return;

  const searchQuery = (document.getElementById("download-search")?.value || "").toLowerCase().trim();

  // Filter by retention policy and search query
  let filtered = allDeviceSnapshots.filter(s => {
    // If device only has standard_31 snapshots and user clicks smart or vice-versa, allow showing all if none match policy
    const matchesPolicy = s.retention_policy_at_capture === currentDownloadPolicy;
    if (!matchesPolicy && allDeviceSnapshots.some(x => x.retention_policy_at_capture === currentDownloadPolicy)) {
      return false;
    }

    if (!searchQuery) return true;
    return (
      (s.display_filename || "").toLowerCase().includes(searchQuery) ||
      (s.change_status || "").toLowerCase().includes(searchQuery) ||
      (s.captured_at || "").toLowerCase().includes(searchQuery) ||
      (s.object?.object_sha256 || "").toLowerCase().includes(searchQuery)
    );
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center py-8 muted">
          No backup archives match the current filter.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map(s => {
    const d = new Date(s.captured_at);
    const dateStr = d.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    let statusPill = "";
    if (s.change_status === "baseline") {
      statusPill = `<span class="px-2 py-0.5 rounded text-[10px] font-bold border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">Baseline</span>`;
    } else if (s.change_status === "changed") {
      statusPill = `<span class="px-2 py-0.5 rounded text-[10px] font-bold border border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400">Changed</span>`;
    } else {
      statusPill = `<span class="px-2 py-0.5 rounded text-[10px] font-bold border border-slate-500/30 bg-slate-500/10 text-slate-600 dark:text-slate-400">No Change</span>`;
    }

    const sizeKb = s.object?.size_bytes ? (s.object.size_bytes / 1024).toFixed(1) + " KB" : "-";
    const sha = s.object?.object_sha256 || "";
    const shortSha = sha ? sha.substring(0, 8) : "-";

    const isViewer = window.authModule?.currentUser()?.role === "viewer";
    const lockTitle = isViewer 
      ? "Read-only (Viewer role cannot download backup files)" 
      : "Download unavailable (S3 storage is disconnected or unmounted)";
    const lockText = isViewer ? "Locked (Viewer)" : "Unavailable (Storage Disconnected)";

    const downloadBtn = s.download_available
      ? `<a href="/api/v1/snapshots/${s.id}/download" download="${s.display_filename}"
           class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold btn-primary shadow-sm transition-transform active:scale-95"
           title="Download config object from Ceph S3 storage">
           <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
             <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
           </svg>
           <span>Download</span>
         </a>`
      : `<span class="text-xs muted px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-medium" title="${lockTitle}">${lockText}</span>`;

    return `
      <tr class="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
        <td class="py-2.5 px-3.5 whitespace-nowrap">
          <div class="font-medium text-xs">${dateStr}</div>
          <div class="muted text-[11px] font-mono">${timeStr}</div>
        </td>
        <td class="py-2.5 px-3.5 whitespace-nowrap">
          ${statusPill}
        </td>
        <td class="py-2.5 px-3.5 font-mono text-xs text-sky-700 dark:text-sky-300 font-semibold">
          ${s.display_filename}
        </td>
        <td class="py-2.5 px-3.5 font-mono text-xs">
          ${sizeKb}
        </td>
        <td class="py-2.5 px-3.5 font-mono text-xs text-muted" title="Full SHA-256: ${sha}">
          <span class="inline-flex items-center gap-1 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border line">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>${shortSha}</span>
          </span>
        </td>
        <td class="py-2.5 px-3.5 text-right whitespace-nowrap">
          ${downloadBtn}
        </td>
      </tr>
    `;
  }).join("");
}

window.downloadManifest = function() {
  if (!currentDownloadDevice || allDeviceSnapshots.length === 0) {
    if (window.inform) window.inform("No snapshots available to export manifest.", true);
    return;
  }

  let content = `========================================================================\n`;
  content += `NETWORK BACKUP MANIFEST ARCHIVE INDEX\n`;
  content += `========================================================================\n`;
  content += `Hostname       : ${currentDownloadDevice.hostname}\n`;
  content += `IP Address     : ${currentDownloadDevice.ip_address}\n`;
  content += `Model          : ${currentDownloadDevice.vendor || ''} ${currentDownloadDevice.model || ''}\n`;
  content += `Driver Key     : ${currentDownloadDevice.backup_settings?.driver_key || 'unassigned'}\n`;
  content += `Generated At   : ${new Date().toISOString()}\n`;
  content += `Total Snapshots: ${allDeviceSnapshots.length}\n`;
  content += `========================================================================\n\n`;

  allDeviceSnapshots.forEach((s, idx) => {
    content += `[Snapshot #${idx + 1}]\n`;
    content += `ID             : ${s.id}\n`;
    content += `Captured At    : ${s.captured_at}\n`;
    content += `Filename       : ${s.display_filename}\n`;
    content += `Status         : ${s.change_status}\n`;
    content += `Retention      : ${s.retention_policy_at_capture}\n`;
    content += `Size Bytes     : ${s.object?.size_bytes ?? 0}\n`;
    content += `SHA-256 Object : ${s.object?.object_sha256 ?? '-'}\n`;
    content += `SHA-256 Content: ${s.object?.content_sha256 ?? '-'}\n`;
    content += `------------------------------------------------------------------------\n`;
  });

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `manifest_${currentDownloadDevice.hostname}_${new Date().toISOString().slice(0, 10)}.txt`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  if (window.inform) window.inform("Backup manifest index downloaded.");
};

document.addEventListener("DOMContentLoaded", () => {
  const closeBtn = document.getElementById("download-close-btn");
  if (closeBtn) closeBtn.addEventListener("click", () => window.closeDialog(document.getElementById("download-dialog")));

  const closeX = document.getElementById("download-close-x");
  if (closeX) closeX.addEventListener("click", () => window.closeDialog(document.getElementById("download-dialog")));
});
