// Theme handling logic
function applyTheme(isDark) {
  const themeBtn = document.getElementById("theme-btn");
  const themeBtnIcon = document.getElementById("theme-btn-icon");
  const themeBtnText = document.getElementById("theme-btn-text");

  if (isDark) {
    document.documentElement.classList.add("dark");
    document.body.classList.add("dark-mode");
    if (themeBtn) themeBtn.setAttribute("aria-pressed", "true");
    if (themeBtnIcon) themeBtnIcon.textContent = "☼";
    if (themeBtnText) themeBtnText.textContent = "Light mode";
    document.querySelectorAll(".theme-icon").forEach(el => el.textContent = "☼");
    document.querySelectorAll(".theme-label-short").forEach(el => el.textContent = "Light mode");
  } else {
    document.documentElement.classList.remove("dark");
    document.body.classList.remove("dark-mode");
    if (themeBtn) themeBtn.setAttribute("aria-pressed", "false");
    if (themeBtnIcon) themeBtnIcon.textContent = "◐";
    if (themeBtnText) themeBtnText.textContent = "Dark mode";
    document.querySelectorAll(".theme-icon").forEach(el => el.textContent = "◐");
    document.querySelectorAll(".theme-label-short").forEach(el => el.textContent = "Dark mode");
  }
  localStorage.setItem("theme_preference", isDark ? "dark" : "light");
}

function toggleTheme() {
  const isCurrentlyDark = document.body.classList.contains("dark-mode") || document.documentElement.classList.contains("dark");
  applyTheme(!isCurrentlyDark);
}

document.addEventListener("DOMContentLoaded", () => {
  const themeBtn = document.getElementById("theme-btn");
  if (themeBtn) {
    themeBtn.addEventListener("click", toggleTheme);
  }

  // Initial theme preference check (localStorage or system)
  const savedTheme = localStorage.getItem("theme_preference");
  if (savedTheme === "dark" || (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    applyTheme(true);
  } else {
    applyTheme(false);
  }
});

// Helper for UI notice updates
window.inform = function(message, isError = false) {
  const notice = document.getElementById("notice");
  const noticeDot = document.getElementById("notice-dot");
  if (notice && noticeDot) {
    notice.textContent = message;
    noticeDot.classList.remove("hidden");
    noticeDot.className = isError ? "w-2 h-2 rounded-full bg-rose-500 inline-block" : "w-2 h-2 rounded-full bg-sky-500 inline-block";
  } else {
    console.log(isError ? "Error: " : "Info: ", message);
  }
};

window.closeDialog = function(dialog) {
  if (dialog) {
    dialog.classList.remove("flex");
    dialog.classList.add("hidden");
  }
};

window.openDialog = function(dialog, focusTarget) {
  window.closeMenus();
  if (dialog) {
    dialog.classList.remove("hidden");
    dialog.classList.add("flex");
    if (focusTarget) focusTarget.focus();
  }
};

window.closeMenus = function() {
  document.querySelectorAll(".pop-menu").forEach(menu => menu.hidden = true);
  document.querySelectorAll('[aria-expanded="true"]').forEach(button => button.setAttribute("aria-expanded", "false"));
};

window.toggleMenu = function(button, menu) {
  const opening = menu.hidden;
  window.closeMenus();
  menu.hidden = !opening;
  button.setAttribute("aria-expanded", String(opening));
};

// Dismiss popovers on outside click
document.addEventListener("click", e => {
  if (!e.target.closest(".backup-wrap") && !e.target.closest("#admin-wrap")) {
    window.closeMenus();
  }
  // Click backdrop outside modal container to dismiss
  if (e.target.classList.contains("dialog-backdrop")) {
    window.closeDialog(e.target);
  }
});

// Keyboard accessibility: Escape key closes menus and active dialogs (R-32)
document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    window.closeMenus();
    document.querySelectorAll(".dialog-backdrop:not(.hidden)").forEach(dialog => {
      window.closeDialog(dialog);
    });
  }
});
