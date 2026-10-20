/**
 * ============================================================================
 * SMART TRAVEL PLANNER - DASHBOARD CONTROLLER
 * Real FastAPI Backend Data Binding
 * ============================================================================
 */

let cachedTrips = [];

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();
});

async function initDashboard() {
  setupDashboardFilters();
  await loadDashboardData("all");
}

async function loadDashboardData(filter = "all") {
  const container = document.getElementById("trips-grid-container");
  const emptyState = document.getElementById("trips-empty-state");

  if (container) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 3rem;">
        <span class="spinner" style="border-top-color: var(--primary); width: 32px; height: 32px;"></span>
        <p style="color: var(--text-muted); margin-top: 0.75rem;">Loading your travel workspaces...</p>
      </div>
    `;
  }

  try {
    cachedTrips = await ApiService.trips.list();
    if (cachedTrips && cachedTrips.length > 0) {
      const activeStoredId = localStorage.getItem("active_trip_id");
      let activeObj = null;
      if (activeStoredId && activeStoredId !== "101") {
        activeObj = cachedTrips.find(t => String(t.trip_id) === String(activeStoredId));
      }
      if (!activeObj) {
        activeObj = cachedTrips.find(t => (t.destination || '').toLowerCase().includes("mysur")) || cachedTrips[cachedTrips.length - 1];
      }
      if (activeObj && typeof setActiveTrip === "function") {
        setActiveTrip(activeObj.trip_id, activeObj.destination, activeObj);
      }
    }
    renderDashboardStats(cachedTrips);
    renderTripsList(cachedTrips, filter);
  } catch (err) {
    console.warn("Failed to fetch trips from API, falling back to local demo state", err);
    if (typeof DemoStore !== "undefined") {
      cachedTrips = DemoStore.getTrips();
      renderDashboardStats(cachedTrips);
      renderTripsList(cachedTrips, filter);
    } else {
      if (container) {
        container.innerHTML = `
          <div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--danger);">
            <p>Could not connect to backend server. Make sure FastAPI is running.</p>
          </div>
        `;
      }
    }
  }
}

function renderDashboardStats(trips) {
  const totalTripsElem = document.getElementById("stat-total-trips");
  const totalBudgetElem = document.getElementById("stat-total-budget");
  const activeDestElem = document.getElementById("stat-active-dest");
  const tripsSubtextElem = document.getElementById("stat-trips-subtext");
  const budgetSubtextElem = document.getElementById("stat-budget-subtext");
  const destSubtextElem = document.getElementById("stat-dest-subtext");

  if (!totalTripsElem) return;

  const today = new Date().toISOString().split("T")[0];
  const activeCount = trips.filter(t => t.start_date <= today && t.end_date >= today).length;
  const upcomingCount = trips.filter(t => t.start_date > today).length;
  const completedCount = trips.filter(t => t.end_date < today).length;

  const totalBudget = trips.reduce((acc, t) => acc + (Number(t.budget) || 0), 0);
  const totalSpent = trips.reduce((acc, t) => acc + (Number(t.total_spent) || 0), 0);
  const totalRemaining = Math.max(0, totalBudget - totalSpent);

  const featuredTrip = trips.length > 0 ? trips[0] : null;

  const formatFn = (typeof formatINR === "function") ? formatINR : (val) => "₹" + Number(val || 0).toLocaleString("en-IN");
  const formatDateFn = (typeof formatDateDisplay === "function") ? formatDateDisplay : (d) => String(d || "");

  totalTripsElem.textContent = trips.length;
  if (tripsSubtextElem) {
    tripsSubtextElem.textContent = `${activeCount} Active • ${upcomingCount} Upcoming • ${completedCount} Completed`;
  }

  totalBudgetElem.textContent = formatFn(totalBudget);
  if (budgetSubtextElem) {
    budgetSubtextElem.textContent = `${formatFn(totalSpent)} spent • ${formatFn(totalRemaining)} remaining`;
  }

  if (featuredTrip) {
    activeDestElem.textContent = featuredTrip.destination || "Trip #" + featuredTrip.trip_id;
    if (destSubtextElem) {
      destSubtextElem.textContent = `${formatDateFn(featuredTrip.start_date)} – ${formatDateFn(featuredTrip.end_date)}`;
    }
  } else {
    activeDestElem.textContent = "None";
    if (destSubtextElem) destSubtextElem.textContent = "No travel plans created yet";
  }
}

function renderTripsList(trips, filter = "all") {
  const container = document.getElementById("trips-grid-container");
  const emptyState = document.getElementById("trips-empty-state");
  if (!container) return;

  const formatFn = (typeof formatINR === "function") ? formatINR : (val) => "₹" + Number(val || 0).toLocaleString("en-IN");
  const formatDateFn = (typeof formatDateDisplay === "function") ? formatDateDisplay : (d) => String(d || "");

  let filtered = [...trips];

  if (filter !== "all") {
    const today = new Date().toISOString().split("T")[0];
    filtered = filtered.filter(t => {
      if (filter === "completed") return t.end_date < today;
      if (filter === "upcoming") return t.start_date > today;
      if (filter === "active") return t.start_date <= today && t.end_date >= today;
      return true;
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = "";
    if (emptyState) emptyState.style.display = "flex";
    return;
  }

  if (emptyState) emptyState.style.display = "none";

  container.innerHTML = filtered.map(trip => {
    const budget = Number(trip.budget) || 0;
    const spent = Number(trip.total_spent) || 0;
    const remaining = Math.max(0, budget - spent);
    const percentage = budget > 0 ? Math.min(100, Math.round((spent / budget) * 100)) : 0;

    let progressColorClass = "fill-safe";
    if (trip.budget_exceeded || percentage > 90) progressColorClass = "fill-danger";
    else if (percentage > 70) progressColorClass = "fill-warn";

    const isExceeded = trip.budget_exceeded || spent > budget;
    const destStr = (trip.destination || '').toLowerCase();
    const themeClass = destStr.includes("goa") ? "goa-theme" :
                       destStr.includes("kerala") ? "kerala-theme" : "ladakh-theme";

    return `
      <div class="trip-card" data-trip-id="${trip.trip_id}">
        <div class="trip-card-banner ${themeClass}">
          <span class="badge ${isExceeded ? 'badge-danger' : 'badge-primary'} trip-status-badge">
            ${isExceeded ? 'Budget Exceeded' : (trip.interests ? trip.interests.split(',')[0] : 'Travel')}
          </span>
          <h3 class="trip-destination-title">${trip.destination || 'Unnamed Trip'}</h3>
        </div>
        <div class="trip-card-body">
          <div class="trip-meta-row">
            <span class="trip-meta-item">
              📅 ${formatDateFn(trip.start_date)} – ${formatDateFn(trip.end_date)}
            </span>
            <span class="trip-meta-item">
              👥 ${trip.travellers} Travelers
            </span>
          </div>

          <div class="trip-budget-preview">
            <div class="budget-preview-labels">
              <span>Budget Spent</span>
              <span>${formatINR(spent)} / ${formatINR(budget)} (${percentage}%)</span>
            </div>
            <div class="progress-bar-track">
              <div class="progress-bar-fill ${progressColorClass}" style="width: ${percentage}%"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.35rem;">
              <span>Remaining: <strong>${formatINR(remaining)}</strong></span>
              ${isExceeded ? '<span style="color: var(--danger); font-weight: bold;">⚠ Exceeded</span>' : ''}
            </div>
          </div>

          <p style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.4;">
            ${trip.description || "Custom planned vacation"}
          </p>
        </div>

        <div class="trip-card-footer">
          <a href="trip.html?id=${trip.trip_id}" onclick="handleSelectTrip(${trip.trip_id});" class="btn btn-outline btn-sm">
            View Trip &rarr;
          </a>
          <button class="btn btn-ghost btn-sm text-danger" onclick="handleDeleteTrip(${trip.trip_id})">
            Delete
          </button>
        </div>
      </div>
    `;
  }).join("");
}

window.handleSelectTrip = function(tripId) {
  if (cachedTrips && cachedTrips.length > 0) {
    const t = cachedTrips.find(item => item.trip_id === tripId);
    if (t && typeof setActiveTrip === 'function') {
      setActiveTrip(t.trip_id, t.destination, t);
      return;
    }
  }
  if (typeof setActiveTrip === 'function') {
    setActiveTrip(tripId);
  }
};

function setupDashboardFilters() {
  const tabs = document.querySelectorAll(".filter-tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const filter = tab.getAttribute("data-filter") || "all";
      renderTripsList(cachedTrips, filter);
    });
  });
}

async function handleDeleteTrip(tripId) {
  if (confirm("Are you sure you want to permanently delete this trip and its itinerary?")) {
    try {
      await ApiService.trips.delete(tripId);
      showToast("Trip deleted successfully", "warning");
      await loadDashboardData("all");
    } catch (err) {
      showToast(err.message || "Failed to delete trip", "error");
    }
  }
}
