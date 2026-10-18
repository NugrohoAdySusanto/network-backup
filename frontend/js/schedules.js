// Schedules Logic - Real Backend Settings & Celery Beat Schedule Integration

window.openScheduleDialog = async function(d) {
  window.selectedDevice = d;

  const titleEl = document.getElementById("schedule-device");
  if (titleEl) {
    const modelText = window.formatDeviceModel 
      ? window.formatDeviceModel(d) 
      : ((d.vendor ? `${d.vendor} ` : '') + (d.model || '-'));
    titleEl.textContent = `Device: ${d.hostname} (${d.ip_address}) • ${modelText}`;
  }

  // Ensure Drivers list is loaded
  if (!window.driversList || window.driversList.length === 0) {
    try {
      const res = await window.api.drivers.list();
      window.driversList = res.items || [];
    } catch (_) {}
  }

  // Populate Driver Select in Modal
  const driverSelect = document.getElementById("schedule-driver");
  if (driverSelect) {
    const list = window.driversList || [];
    driverSelect.innerHTML = `<option value="">-- Select Driver --</option>` +
      list.map(driver => `<option value="${driver.key}">${driver.label || driver.name || driver.key}</option>`).join("");
    
    // Default to device's pending driver or currently assigned driver or detect from vendor / row select
    let currentDriver = d._pending?.driver_key || d.backup_settings?.driver_key || "";
    if (!currentDriver) {
      const rowSelect = document.querySelector(`tr[data-row-id="${d.id}"] .worker-select`);
      if (rowSelect && rowSelect.value) currentDriver = rowSelect.value;
    }
    if (!currentDriver && d.vendor) {
      const v = d.vendor.toLowerCase();
      if (v.includes("mikrotik")) currentDriver = "mikrotik-routeros";
      else if (v.includes("ruijie") && (d.model || "").toLowerCase().includes("ap")) currentDriver = "ruijie-ap";
      else if (v.includes("ruijie")) currentDriver = "ruijie-switch";
      else if (v.includes("sangfor")) currentDriver = "sangfor-nsf";
    }
    driverSelect.value = currentDriver;
  }

  // Populate Retention Policy
  const currentPolicy = d._pending?.retention_policy || d.backup_settings?.retention_policy || "standard_31";
  if (currentPolicy === "smart_7_4_12_3" || currentPolicy === "smart") {
    const rSmart = document.getElementById("retention-smart");
    if (rSmart) rSmart.checked = true;
  } else {
    const r31 = document.getElementById("retention-31");
    if (r31) r31.checked = true;
  }

  // Populate Daily Time (5-minute slot)
  const timeInput = document.getElementById("schedule-time");
  const pendingOrSavedTime = d._pending?.daily_time || d.backup_settings?.daily_time;
  if (timeInput) {
    if (pendingOrSavedTime) {
      timeInput.value = pendingOrSavedTime.substring(0, 5);
    } else {
      // Pick a clean 5-minute slot ~10 minutes from now as default
      const now = new Date();
      let minutes = Math.ceil((now.getMinutes() + 10) / 5) * 5;
      now.setMinutes(minutes);
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      timeInput.value = `${hh}:${mm}`;
    }
  }

  // Handle Disable button & Submit button state
  const disableBtn = document.getElementById("schedule-disable-btn");
  const submitBtn = document.getElementById("schedule-submit-btn");
  const isEnabled = d._pending?.schedule_enabled !== undefined 
    ? d._pending.schedule_enabled 
    : d.backup_settings?.schedule_enabled;

  if (isEnabled) {
    if (disableBtn) disableBtn.classList.remove("hidden");
    if (submitBtn) submitBtn.textContent = "Apply Schedule";
  } else {
    if (disableBtn) disableBtn.classList.add("hidden");
    if (submitBtn) submitBtn.textContent = "Apply Schedule";
  }

  window.openDialog(document.getElementById("schedule-dialog"), timeInput);
};

document.addEventListener("DOMContentLoaded", () => {
  const scheduleForm = document.getElementById("schedule-form");
  if (scheduleForm) {
    scheduleForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const d = window.selectedDevice;
      if (!d) return;

      const driverKey = document.getElementById("schedule-driver")?.value;
      if (!driverKey) {
        if (window.inform) window.inform("Please select a Backup Driver before scheduling.", true);
        return;
      }

      let rawTime = document.getElementById("schedule-time")?.value || "";
      if (!rawTime) {
        if (window.inform) window.inform("Please select a Daily Backup Time.", true);
        return;
      }

      // If time format is HH:MM, ensure 5-minute alignment
      const timeParts = rawTime.split(":");
      const hours = parseInt(timeParts[0], 10);
      let mins = parseInt(timeParts[1], 10);

      if (mins % 5 !== 0) {
        mins = Math.round(mins / 5) * 5;
        if (mins >= 60) mins = 55;
      }

      const formattedDailyTime = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:00`;

      let selectedPolicy = document.querySelector('input[name="retention"]:checked')?.value || "standard_31";
      if (selectedPolicy === "31" || selectedPolicy === "all") selectedPolicy = "standard_31";
      if (selectedPolicy === "smart") selectedPolicy = "smart_7_4_12_3";

      // Stage pending changes in memory (Must click Save on device row to persist)
      d._pending = d._pending || {};
      d._pending.driver_key = driverKey;
      d._pending.schedule_enabled = true;
      d._pending.daily_time = formattedDailyTime;
      d._pending.retention_policy = selectedPolicy;
      d._pending.isDirty = true;

      // Close modal
      window.closeDialog(document.getElementById("schedule-dialog"));

      // Update table row in UI with pending state
      const row = document.querySelector(`tr[data-row-id="${d.id}"]`);
      if (row) {
        const ws = row.querySelector(".worker-select");
        if (ws) ws.value = driverKey;

        const schedInd = row.querySelector(".schedule-indicator");
        if (schedInd) schedInd.textContent = `Daily @ ${formattedDailyTime.slice(0, 5)} (Unsaved)`;

        const nextInd = row.querySelector(".row-next-backup");
        if (nextInd) {
          nextInd.textContent = `Daily ${formattedDailyTime.slice(0, 5)}`;
          nextInd.className = "row-next-backup text-xs font-semibold text-amber-500 block";
        }

        const pill = row.querySelector(".device-retention-pill");
        if (pill) {
          pill.classList.remove("hidden");
          pill.textContent = selectedPolicy.includes("smart") ? "Smart Ret." : "31 Days";
        }

        const saveBtn = row.querySelector(".save-btn");
        if (saveBtn) {
          saveBtn.className = "save-btn btn-success rounded-lg px-3 py-1.5 text-xs font-bold shadow-md ring-2 ring-emerald-400 animate-pulse";
          saveBtn.textContent = "Save*";
          saveBtn.title = "Unsaved schedule! Click Save in the ACTIONS column to persist.";
        }
      }

      const policyLabel = selectedPolicy === "smart_7_4_12_3" ? "Smart Retention" : "31 Days";
      if (window.inform) {
        window.inform(`Schedule configured: Daily @ ${formattedDailyTime.slice(0, 5)} (${policyLabel}). Click "Save" in the ACTIONS column to apply changes.`);
      }
    });
  }

  // Handle Disable Schedule button
  const disableBtn = document.getElementById("schedule-disable-btn");
  if (disableBtn) {
    disableBtn.addEventListener("click", () => {
      const d = window.selectedDevice;
      if (!d) return;

      d._pending = d._pending || {};
      d._pending.schedule_enabled = false;
      d._pending.daily_time = null;
      d._pending.isDirty = true;

      window.closeDialog(document.getElementById("schedule-dialog"));

      const row = document.querySelector(`tr[data-row-id="${d.id}"]`);
      if (row) {
        const schedInd = row.querySelector(".schedule-indicator");
        if (schedInd) schedInd.textContent = "Disabled (Unsaved)";

        const nextInd = row.querySelector(".row-next-backup");
        if (nextInd) {
          nextInd.textContent = "-";
          nextInd.className = "row-next-backup text-xs font-medium muted block";
        }

        const saveBtn = row.querySelector(".save-btn");
        if (saveBtn) {
          saveBtn.className = "save-btn btn-success rounded-lg px-3 py-1.5 text-xs font-bold shadow-md ring-2 ring-emerald-400 animate-pulse";
          saveBtn.textContent = "Save*";
          saveBtn.title = "Unsaved schedule changes! Click Save in ACTIONS column to persist.";
        }
      }

      if (window.inform) {
        window.inform(`Schedule disabled for ${d.hostname}. Click "Save" in the ACTIONS column to apply changes.`);
      }
    });
  }

  const cancelBtn = document.getElementById("schedule-cancel");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      window.closeDialog(document.getElementById("schedule-dialog"));
    });
  }
});
