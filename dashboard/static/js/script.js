// DOM Elements
const dashboardSidebar = document.getElementById("dashboardSidebar");
const themeToggle = document.getElementById("theme-toggle");
const dashboardSidebarOverlay = document.getElementById(
  "dashboardSidebarOverlay",
);
const searchContainer = document.getElementById("searchContainer");
const searchInput = document.getElementById("searchInput");
const searchClose = document.getElementById("searchClose");
const mobileSearchBtn = document.getElementById("mobileSearchBtn");

// State
let sidebarCollapsed =
  localStorage.getItem("dashboard-sidebar-collapsed") === "true";
const isMobile = () => window.innerWidth <= 1024;

document.addEventListener("DOMContentLoaded", function () {
  initTheme();
  initThemeToggle();
  initSidebar();
  initMenus();
  initSearch();
  initCharts();
});

// ===================================
// SIDEBAR
// ===================================

function initSidebar() {
  if (!dashboardSidebar) return;
  applySidebarState();

  document.querySelectorAll(".dashboard-sidebar-toggle").forEach((toggle) => {
    toggle.addEventListener("click", toggleSidebar);
  });
  dashboardSidebarOverlay?.addEventListener("click", closeSidebar);

  // Only re-apply when crossing the mobile breakpoint (phones fire resize on scroll)
  let wasMobile = isMobile();
  window.addEventListener("resize", () => {
    if (isMobile() !== wasMobile) {
      wasMobile = isMobile();
      applySidebarState();
    }
  });
}

function applySidebarState() {
  if (isMobile()) {
    dashboardSidebar.classList.remove("collapsed");
    dashboardSidebarOverlay?.classList.remove("active");
  } else {
    dashboardSidebar.classList.toggle("collapsed", sidebarCollapsed);
  }
}

function toggleSidebar() {
  if (isMobile()) {
    // On mobile the "collapsed" class means the sidebar is open
    const open = dashboardSidebar.classList.toggle("collapsed");
    dashboardSidebarOverlay?.classList.toggle("active", open);
    return;
  }
  sidebarCollapsed = !sidebarCollapsed;
  dashboardSidebar.classList.toggle("collapsed", sidebarCollapsed);
  localStorage.setItem(
    "dashboard-sidebar-collapsed",
    sidebarCollapsed.toString(),
  );
}

function closeSidebar() {
  if (isMobile()) {
    dashboardSidebar.classList.remove("collapsed");
    dashboardSidebarOverlay?.classList.remove("active");
  }
}

// ===================================
// HEADER MENUS (notifications + user menu)
// ===================================

function initMenus() {
  const menus = document.querySelectorAll(".user-menu");
  const closeAll = () => menus.forEach((m) => m.classList.remove("active"));

  menus.forEach((menu) => {
    const trigger = menu.querySelector(
      ".user-menu-trigger, .notification-button",
    );
    trigger?.addEventListener("click", (e) => {
      e.stopPropagation();
      const wasOpen = menu.classList.contains("active");
      closeAll();
      menu.classList.toggle("active", !wasOpen);
    });
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".user-menu")) closeAll();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAll();
  });
}

// ===================================
// THEME
// ===================================

function initTheme() {
  const savedTheme = localStorage.getItem("dashboard-theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeToggleUI(savedTheme);
}

function initThemeToggle() {
  if (!themeToggle) return;
  themeToggle.querySelectorAll(".theme-option").forEach((option) => {
    option.addEventListener("click", (e) => {
      e.stopPropagation();
      setTheme(option.getAttribute("data-theme"));
    });
  });
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("dashboard-theme", theme);
  updateThemeToggleUI(theme);
}

function updateThemeToggleUI(theme) {
  if (!themeToggle) return;
  themeToggle.querySelectorAll(".theme-option").forEach((option) => {
    option.classList.toggle(
      "active",
      option.getAttribute("data-theme") === theme,
    );
  });
}

// ===================================
// SEARCH (the form submits to the Django search page)
// ===================================

function initSearch() {
  mobileSearchBtn?.addEventListener("click", () => {
    searchContainer.classList.add("mobile-active");
    searchInput.focus();
  });
  searchClose?.addEventListener("click", () => {
    searchContainer.classList.remove("mobile-active");
    searchInput.value = "";
  });
}

// ===================================
// CHARTS (data comes from Django through json_script)
// ===================================

const PALETTE = [
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#3b82f6",
  "#ec4899",
  "#14b8a6",
];

function cssVar(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function readData(id) {
  const el = document.getElementById(id);
  return el ? JSON.parse(el.textContent) : null;
}

function initCharts() {
  if (typeof Chart === "undefined") return;
  Chart.defaults.font.family = "Inter, sans-serif";
  Chart.defaults.color = cssVar("--color-text-secondary") || "#475569";
  Chart.defaults.borderColor = cssVar("--color-border") || "#e2e8f0";

  initProgressChart();
  initCategoryChart();
  initProjectChart();
  initPeopleChart();
}

function initProgressChart() {
  const ctx = document.getElementById("progressChart");
  const labels = readData("progress-labels");
  const data = readData("progress-data");
  if (!ctx || !labels) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Completion rate",
          data,
          borderColor: "#8b5cf6",
          backgroundColor: "rgba(139, 92, 246, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { callback: (v) => v + "%" } },
      },
    },
  });
}

function initCategoryChart() {
  const ctx = document.getElementById("categoryChart");
  const labels = readData("category-labels");
  const data = readData("category-data");
  if (!ctx || !labels) return;

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data, backgroundColor: PALETTE, borderWidth: 0 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { padding: 20, usePointStyle: true },
        },
      },
    },
  });
}

function initProjectChart() {
  const ctx = document.getElementById("projectChart");
  const labels = readData("project-labels");
  const data = readData("project-progress");
  if (!ctx || !labels) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data, backgroundColor: "#8b5cf6", borderRadius: 6 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, max: 100, ticks: { callback: (v) => v + "%" } },
      },
    },
  });
}

function initPeopleChart() {
  const ctx = document.getElementById("peopleChart");
  const labels = readData("people-labels");
  if (!ctx || !labels) return;

  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Open",
          data: readData("people-open"),
          backgroundColor: "#f59e0b",
          borderRadius: 4,
        },
        {
          label: "Done",
          data: readData("people-done"),
          backgroundColor: "#10b981",
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true } },
      },
      scales: {
        x: { stacked: true },
        y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } },
      },
    },
  });
}
