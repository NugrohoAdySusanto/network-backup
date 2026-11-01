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

  // Populate Retention Policy
  const currentPolicy = d._pending?.retention_policy || d.backup_settings?.retention_policy || "standard_31";
  if (currentPolicy === "smart_7_4_12_3" || currentPolicy === "smart") {
    const rSmart = document.getElementById("retention-smart");
    if (rSmart) rSmart.checked = true;
  } else {
    const r31 = document.getElementById("retention-31");
    if (r31) r31.checked = true;
  }

  // Populate Daily Time (strict 5-minute slots)
  const hourSelect = document.getElementById("schedule-hour");
  const minuteSelect = document.getElementById("schedule-minute");
  const timeInput = document.getElementById("schedule-time");
  const pendingOrSavedTime = d._pending?.daily_time || d.backup_settings?.daily_time;

  let hh = "00";
  let mm = "00";
  if (pendingOrSavedTime) {
    const parts = pendingOrSavedTime.substring(0, 5).split(":");
    hh = parts[0] ? parts[0].padStart(2, "0") : "00";
    let mInt = parseInt(parts[1] || "0", 10);
    if (isNaN(mInt)) mInt = 0;
    mInt = Math.round(mInt / 5) * 5;
    if (mInt >= 60) mInt = 55;
    mm = String(mInt).padStart(2, "0");
  } else {
    // Default to upcoming 5-minute slot ~10 minutes from now
    const now = new Date();
    let minutes = Math.ceil((now.getMinutes() + 10) / 5) * 5;
    if (minutes >= 60) {
      now.setHours(now.getHours() + 1);
      minutes = 0;
    }
    hh = String(now.getHours()).padStart(2, "0");
    mm = String(minutes).padStart(2, "0");
  }

  if (hourSelect) hourSelect.value = hh;
  if (minuteSelect) minuteSelect.value = mm;
  if (timeInput) timeInput.value = `${hh}:${mm}`;

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

  window.openDialog(document.getElementById("schedule-dialog"), hourSelect || timeInput);
};

document.addEventListener("DOMContentLoaded", () => {
  const hourSelect = document.getElementById("schedule-hour");
  const minuteSelect = document.getElementById("schedule-minute");
  const timeInput = document.getElementById("schedule-time");
  const syncScheduleTime = () => {
    if (hourSelect && minuteSelect && timeInput) {
      timeInput.value = `${hourSelect.value}:${minuteSelect.value}`;
    }
  };
  if (hourSelect) hourSelect.addEventListener("change", syncScheduleTime);
  if (minuteSelect) minuteSelect.addEventListener("change", syncScheduleTime);

  const scheduleForm = document.getElementById("schedule-form");
  if (scheduleForm) {
    scheduleForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const d = window.selectedDevice;
      if (!d) return;

      const row = document.querySelector(`tr[data-row-id="${d.id}"]`);
      const rowWorker = row ? row.querySelector(".worker-select")?.value : "";
      const currentDriver = d._pending?.driver_key !== undefined
        ? d._pending.driver_key
        : (rowWorker || d.backup_settings?.driver_key);

      if (!currentDriver) {
        if (window.inform) window.inform("Please select a Backup Worker in the table before scheduling.", true);
        return;
      }

      const hVal = document.getElementById("schedule-hour")?.value || "00";
      const mVal = document.getElementById("schedule-minute")?.value || "00";
      const formattedDailyTime = `${hVal.padStart(2, "0")}:${mVal.padStart(2, "0")}:00`;

      let selectedPolicy = document.querySelector('input[name="retention"]:checked')?.value || "standard_31";
      if (selectedPolicy === "31" || selectedPolicy === "all") selectedPolicy = "standard_31";
      if (selectedPolicy === "smart") selectedPolicy = "smart_7_4_12_3";

      // Stage pending changes in memory (Must click Save on device row to persist)
      d._pending = d._pending || {};
      d._pending.schedule_enabled = true;
      d._pending.daily_time = formattedDailyTime;
      d._pending.retention_policy = selectedPolicy;
      d._pending.isDirty = true;

      // Close modal
      window.closeDialog(document.getElementById("schedule-dialog"));

      // Update table row in UI with pending state
      if (row) {

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
