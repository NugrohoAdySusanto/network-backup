// =========================================================================
// REPORTS EXPORT LOGIC (EXCEL & PDF WITH DATE RANGE PICKER & CHARTS)
// =========================================================================

let currentExportFormat = 'xlsx';

function formatLocalISOString(date) {
  const pad = num => String(num).padStart(2, '0');
  const yyyy = date.getFullYear();
  const MM = pad(date.getMonth() + 1);
  const dd = pad(date.getDate());
  const hh = pad(date.getHours());
  const mm = pad(date.getMinutes());
  return `${yyyy}-${MM}-${dd}T${hh}:${mm}`;
}

window.openExportModal = function(initialFormat = 'xlsx') {
  currentExportFormat = initialFormat;
  updateExportFormatUI();

  // Populate Device dropdown if devices exist
  const deviceSelect = document.getElementById("export-device");
  if (deviceSelect) {
    const devices = window.allDevices || [];
    deviceSelect.innerHTML = `<option value="">All Monitored Devices (${devices.length})</option>` +
      devices.map(d => `<option value="${d.id}">${d.hostname} (${d.ip_address})</option>`).join("");
  }

  // Set default: Last 7 Days
  window.setExportPreset('7days');

  // Reset status filter
  const statusSelect = document.getElementById("export-status");
  if (statusSelect) statusSelect.value = "";

  // Hide alert
  const alertEl = document.getElementById("export-error-alert");
  if (alertEl) alertEl.classList.add("hidden");

  // Open Dialog
  const dialog = document.getElementById("export-dialog");
  window.openDialog(dialog, document.getElementById("export-submit-btn"));
};

function updateExportFormatUI() {
  const tabXlsx = document.getElementById("export-tab-xlsx");
  const tabPdf = document.getElementById("export-tab-pdf");
  const descEl = document.getElementById("export-format-desc");

  const inactiveTab = "flex-1 py-2.5 px-3 rounded-xl text-xs font-semibold transition-all muted hover:text-inherit border-0";

  if (currentExportFormat === 'xlsx') {
    if (tabXlsx) {
      tabXlsx.className = "flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition-all bg-white dark:bg-slate-800 text-emerald-600 dark:text-emerald-400 shadow-sm border border-emerald-500/30";
    }
    if (tabPdf) {
      tabPdf.className = inactiveTab;
    }
    if (descEl) {
      descEl.textContent = "Exports formatted Microsoft Excel (.xlsx) spreadsheet with styled headers, KPI summary cards, SLA rates, auto-fit columns, and complete execution audit metadata.";
    }
  } else {
    currentExportFormat = 'pdf';
    if (tabPdf) {
      tabPdf.className = "flex-1 py-2.5 px-3 rounded-xl text-xs font-bold transition-all bg-white dark:bg-slate-800 text-purple-600 dark:text-purple-400 shadow-sm border border-purple-500/30";
    }
    if (tabXlsx) {
      tabXlsx.className = inactiveTab;
    }
    if (descEl) {
      descEl.textContent = "Generates a formal executive PDF audit report with vector distribution charts, KPI metrics, failure logs, and full execution records formatted for A4 landscape printing.";
    }
  }
}

window.selectExportFormat = function(format) {
  currentExportFormat = format;
  updateExportFormatUI();
};

window.setExportPreset = function(preset) {
  const now = new Date();
  const startInput = document.getElementById("export-start-date");
  const endInput = document.getElementById("export-end-date");

  let startDate = new Date();
  let endDate = new Date(now);
  endDate.setHours(23, 59, 59, 999);

  if (preset === 'today') {
    startDate.setHours(0, 0, 0, 0);
  } else if (preset === '7days') {
    startDate.setDate(now.getDate() - 7);
    startDate.setHours(0, 0, 0, 0);
  } else if (preset === '30days') {
    startDate.setDate(now.getDate() - 30);
    startDate.setHours(0, 0, 0, 0);
  } else if (preset === 'this_month') {
    startDate = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
  }

  if (startInput) startInput.value = formatLocalISOString(startDate);
  if (endInput) endInput.value = formatLocalISOString(endDate);

  // Update button active styling
  document.querySelectorAll(".preset-btn").forEach(btn => {
    if (btn.dataset.preset === preset) {
      btn.className = "preset-btn px-2.5 py-1 rounded-lg text-xs font-bold bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/30";
    } else {
      btn.className = "preset-btn px-2.5 py-1 rounded-lg text-xs font-medium soft border hover:border-sky-500";
    }
  });
};

window.handleExportSubmit = async function(event) {
  event.preventDefault();

  const startVal = document.getElementById("export-start-date")?.value;
  const endVal = document.getElementById("export-end-date")?.value;
  const statusVal = document.getElementById("export-status")?.value;
  const deviceVal = document.getElementById("export-device")?.value;

  const alertEl = document.getElementById("export-error-alert");
  if (alertEl) alertEl.classList.add("hidden");

  if (!startVal || !endVal) {
    if (alertEl) {
      alertEl.textContent = "Please select both start and end dates.";
      alertEl.classList.remove("hidden");
    }
    return;
  }

  if (new Date(startVal) > new Date(endVal)) {
    if (alertEl) {
      alertEl.textContent = "Start date cannot be after end date.";
      alertEl.classList.remove("hidden");
    }
    return;
  }

  const submitBtn = document.getElementById("export-submit-btn");
  const originalBtnHtml = submitBtn ? submitBtn.innerHTML : "";

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <span>Generating ${currentExportFormat.toUpperCase()} Report...</span>
    `;
  }

  try {
    const params = {
      format: currentExportFormat,
      start_date: startVal,
      end_date: endVal,
    };
    if (statusVal) params.status = statusVal;
    if (deviceVal) params.device_id = deviceVal;

    const downloadedFilename = await window.api.reports.download(params);

    if (window.inform) {
      window.inform(`Exported ${currentExportFormat.toUpperCase()} report: ${downloadedFilename}`);
    }

    window.closeDialog(document.getElementById("export-dialog"));
  } catch (err) {
    console.error("Export report failed:", err);
    if (alertEl) {
      alertEl.textContent = err.message || "Failed to generate report. Please try again.";
      alertEl.classList.remove("hidden");
    } else if (window.inform) {
      window.inform(`Export error: ${err.message}`, true);
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnHtml;
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  // Bind main Export button on dashboard
  const exportBtn = document.getElementById("export-btn");
  if (exportBtn) {
    exportBtn.onclick = (e) => {
      e.preventDefault();
      window.openExportModal('xlsx');
    };
  }

  // Fallback bindings if older buttons exist
  const csvBtn = document.getElementById("csv-btn");
  if (csvBtn) {
    csvBtn.onclick = (e) => {
      e.preventDefault();
      window.openExportModal('xlsx');
    };
  }

  const pdfBtn = document.getElementById("pdf-btn");
  if (pdfBtn) {
    pdfBtn.onclick = (e) => {
      e.preventDefault();
      window.openExportModal('pdf');
    };
  }

  // Bind Close buttons
  const closeBtn = document.getElementById("export-close-btn");
  if (closeBtn) closeBtn.onclick = () => window.closeDialog(document.getElementById("export-dialog"));

  const closeX = document.getElementById("export-close-x");
  if (closeX) closeX.onclick = () => window.closeDialog(document.getElementById("export-dialog"));
});
