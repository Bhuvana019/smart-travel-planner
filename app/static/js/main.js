/**
 * ============================================================================
 * SMART TRAVEL PLANNER - MAIN JAVASCRIPT & DEMO DATA STORE
 * Phase 1: Frontend Only
 * ============================================================================
 */

// Immediately eliminate any stale Goa or 101 data across localStorage
(function purgeLegacyGoaData() {
  try {
    const activeId = localStorage.getItem("active_trip_id");
    const activeDest = localStorage.getItem("active_trip_destination");
    if (activeId === "101" || !activeId) {
      localStorage.setItem("active_trip_id", "130");
    }
    if (activeDest === "Goa" || !activeDest) {
      localStorage.setItem("active_trip_destination", "Mysuru");
    }
    const metaStr = localStorage.getItem("active_trip_meta");
    if (metaStr && (metaStr.includes('"destination":"Goa"') || metaStr.includes('"trip_id":101') || metaStr.includes('Goa'))) {
      localStorage.removeItem("active_trip_meta");
    }
  } catch (e) {}
})();

// Initial Seed Demo Data according to specification
const INITIAL_DEMO_DATA = {
  user: {
    id: 1,
    name: "Arun Kumar",
    email: "arun.kumar@example.com",
    avatar: "AK",
    bio: "Passionate traveler & explorer. Exploring heritage cities, coastal wonders and mountain trails across India.",
    home_currency: "INR (₹)"
  },
  trips: [
    {
      trip_id: 130,
      destination: "Mysuru",
      trip_name: "friends",
      theme: "mysuru-theme",
      start_date: "2026-10-23",
      end_date: "2026-10-26",
      travellers: 2,
      budget: 30000,
      status: "Active",
      description: "Heritage exploration, Mysore Palace tour, Chamundi hills and South Indian culture."
    },
    {
      trip_id: 102,
      destination: "Kerala Backwaters",
      theme: "kerala-theme",
      start_date: "2026-11-05",
      end_date: "2026-11-10",
      travellers: 2,
      budget: 32000,
      status: "Upcoming",
      description: "Serene houseboat cruising in Alleppey and spice plantation trails."
    },
    {
      trip_id: 103,
      destination: "Ladakh Roadtrip",
      theme: "ladakh-theme",
      start_date: "2026-08-12",
      end_date: "2026-08-20",
      travellers: 4,
      budget: 55000,
      status: "Completed",
      description: "High mountain passes, Pangong Tso camp, and ancient monasteries."
    }
  ],
  itinerary: {
    130: [
      {
        item_id: 25,
        date: "2026-10-23",
        time: "10:00",
        activity: "Mysore Palace Visit & Audio Tour",
        location: "Agrahara, Mysuru",
        estimated_cost: 200,
        notes: "Explore grand royal halls, darbar hall, and palace architecture"
      },
      {
        item_id: 26,
        date: "2026-10-23",
        time: "15:30",
        activity: "Chamundi Hills & Sri Chamundeshwari Temple",
        location: "Chamundi Hill, Mysuru",
        estimated_cost: 100,
        notes: "Scenic hilltop viewpoint and heritage temple"
      },
      {
        item_id: 27,
        date: "2026-10-24",
        time: "17:00",
        activity: "Brindavan Gardens & Musical Fountain",
        location: "KRS Dam, Mysuru",
        estimated_cost: 150,
        notes: "Evening illuminated fountain show and botanical garden"
      }
    ]
  },
  expenses: {
    130: [
      {
        expense_id: 1,
        category: "Activities",
        amount: 400,
        description: "Palace tickets and audio guides",
        expense_date: "2026-10-23"
      },
      {
        expense_id: 2,
        category: "Food",
        amount: 850,
        description: "Traditional Mysore Pak & South Indian Thali",
        expense_date: "2026-10-23"
      }
    ]
  },
  recommendations: [
    {
      id: 1,
      name: "Scuba Diving",
      category: "Adventure",
      price: 2500,
      rating: 4.7,
      description: "Explore the vibrant underwater marine life around Grande Island with certified PADI dive instructors.",
      image_tag: "scuba"
    },
    {
      id: 2,
      name: "Dolphin Watching",
      category: "Adventure",
      price: 1200,
      rating: 4.5,
      description: "Cruise into the morning waters off Sinquerim to spot wild dolphins playing in their natural habitat.",
      image_tag: "dolphin"
    },
    {
      id: 3,
      name: "Baga Beach",
      category: "Beach",
      price: 0,
      rating: 4.6,
      description: "Classic golden sands with lively beach shacks, refreshing drinks, and watersports activities.",
      image_tag: "baga"
    },
    {
      id: 4,
      name: "Dudhsagar Waterfalls Trek",
      category: "Nature",
      price: 1800,
      rating: 4.8,
      description: "A breathtaking four-tiered cascade deep in the Western Ghats reachable by scenic jungle jeep trail.",
      image_tag: "waterfall"
    },
    {
      id: 5,
      name: "Old Goa Heritage Walk",
      category: "Culture",
      price: 600,
      rating: 4.4,
      description: "Step back into the 16th century visiting the Basilica of Bom Jesus and majestic colonial cathedrals.",
      image_tag: "heritage"
    },
    {
      id: 6,
      name: "Sunset Cruise at Mandovi",
      category: "Leisure",
      price: 950,
      rating: 4.6,
      description: "Enjoy a twilight cruise along the Mandovi River featuring Goan folk music, dance, and scenic views.",
      image_tag: "cruise"
    }
  ]
};

/**
 * Demo Data Store (In-Memory with LocalStorage fallback)
 */
const DemoStore = {
  STORAGE_KEY: "smart_travel_planner_demo_v1",

  _getState() {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.warn("LocalStorage access failed, fallback to in-memory state", e);
    }
    // Seed and save
    this._saveState(INITIAL_DEMO_DATA);
    return JSON.parse(JSON.stringify(INITIAL_DEMO_DATA));
  },

  _saveState(state) {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn("LocalStorage save failed", e);
    }
  },

  reset() {
    this._saveState(INITIAL_DEMO_DATA);
    showToast("Demo data reset to initial defaults", "info");
    return INITIAL_DEMO_DATA;
  },

  getUser() {
    return this._getState().user;
  },

  updateUser(userData) {
    const state = this._getState();
    state.user = { ...state.user, ...userData };
    this._saveState(state);
    return state.user;
  },

  getTrips() {
    return this._getState().trips;
  },

  getTripById(id) {
    const trips = this.getTrips();
    return trips.find(t => String(t.trip_id) === String(id)) || trips[0];
  },

  addTrip(tripData) {
    const state = this._getState();
    const newId = Date.now();
    const newTrip = {
      trip_id: newId,
      destination: tripData.destination,
      theme: "goa-theme",
      start_date: tripData.start_date,
      end_date: tripData.end_date,
      travellers: Number(tripData.travellers),
      budget: Number(tripData.budget),
      status: "Upcoming",
      description: tripData.description || `Exciting getaway to ${tripData.destination}!`
    };
    state.trips.unshift(newTrip);
    state.itinerary[newId] = [];
    state.expenses[newId] = [];
    this._saveState(state);
    return newTrip;
  },

  deleteTrip(tripId) {
    const state = this._getState();
    state.trips = state.trips.filter(t => String(t.trip_id) !== String(tripId));
    delete state.itinerary[tripId];
    delete state.expenses[tripId];
    this._saveState(state);
    return true;
  },

  getItinerary(tripId = 130) {
    const state = this._getState();
    return state.itinerary[tripId] || state.itinerary[130] || [];
  },

  addItineraryItem(tripId = 130, itemData) {
    const state = this._getState();
    if (!state.itinerary[tripId]) state.itinerary[tripId] = [];
    const newItem = {
      item_id: Date.now(),
      date: itemData.date,
      time: itemData.time,
      activity: itemData.activity,
      location: itemData.location || "City Area",
      estimated_cost: Number(itemData.estimated_cost || 0),
      notes: itemData.notes || ""
    };
    state.itinerary[tripId].push(newItem);
    // Sort chronologically
    state.itinerary[tripId].sort((a, b) => {
      const dateTimeA = `${a.date}T${a.time}`;
      const dateTimeB = `${b.date}T${b.time}`;
      return dateTimeA.localeCompare(dateTimeB);
    });
    this._saveState(state);
    return newItem;
  },

  deleteItineraryItem(tripId = 130, itemId) {
    const state = this._getState();
    if (state.itinerary[tripId]) {
      state.itinerary[tripId] = state.itinerary[tripId].filter(
        i => String(i.item_id) !== String(itemId)
      );
      this._saveState(state);
    }
    return true;
  },

  getExpenses(tripId = 130) {
    const state = this._getState();
    return state.expenses[tripId] || state.expenses[130] || [];
  },

  addExpense(tripId = 130, expenseData) {
    const state = this._getState();
    if (!state.expenses[tripId]) state.expenses[tripId] = [];
    const newExpense = {
      expense_id: Date.now(),
      category: expenseData.category,
      amount: Number(expenseData.amount),
      description: expenseData.description || "General expense",
      expense_date: expenseData.expense_date
    };
    state.expenses[tripId].push(newExpense);
    this._saveState(state);
    return newExpense;
  },

  deleteExpense(tripId = 130, expenseId) {
    const state = this._getState();
    if (state.expenses[tripId]) {
      state.expenses[tripId] = state.expenses[tripId].filter(
        e => String(e.expense_id) !== String(expenseId)
      );
      this._saveState(state);
    }
    return true;
  },

  getRecommendations(destination = "Mysuru", category = "All") {
    const state = this._getState();
    let list = state.recommendations;
    if (category && category !== "All") {
      list = list.filter(r => r.category.toLowerCase() === category.toLowerCase());
    }
    return list;
  }
};

/**
 * Currency & Date Formatters
 */
function formatINR(amount) {
  const num = Number(amount) || 0;
  return "₹" + num.toLocaleString("en-IN");
}

function formatDateDisplay(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      day: "numeric",
      month: "short",
      year: "numeric"
    });
  } catch (e) {
    return dateStr;
  }
}

/**
 * Toast Notification System
 */
function showToast(message, type = "info", duration = 3500) {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  const iconMap = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ"
  };

  toast.innerHTML = `
    <span class="toast-icon">${iconMap[type] || "ℹ"}</span>
    <span class="toast-message">${message}</span>
    <button class="toast-close" aria-label="Close">&times;</button>
  `;

  toast.querySelector(".toast-close").addEventListener("click", () => {
    toast.remove();
  });

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentNode) {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(50px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }
  }, duration);
}

/**
 * Modal Handling
 */
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// Global click-outside modal close & escape key listener
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        closeModal(backdrop.id);
      }
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.active").forEach(modal => {
        closeModal(modal.id);
      });
    }
  });

  // Mobile navigation drawer toggle for public navbar
  const mobileNavBtn = document.querySelector(".mobile-nav-toggle");
  const siteNavbar = document.querySelector(".site-navbar");
  if (mobileNavBtn && siteNavbar) {
    mobileNavBtn.addEventListener("click", () => {
      siteNavbar.classList.toggle("menu-open");
    });
  }

  // App sidebar toggle for mobile authenticated views
  const sidebarToggleBtn = document.querySelector(".sidebar-toggle-btn");
  const appSidebar = document.querySelector(".app-sidebar");
  const mobileOverlay = document.querySelector(".mobile-overlay");
  if (sidebarToggleBtn && appSidebar) {
    sidebarToggleBtn.addEventListener("click", () => {
      appSidebar.classList.toggle("sidebar-open");
      if (mobileOverlay) mobileOverlay.classList.toggle("active");
    });
  }
  if (mobileOverlay) {
    mobileOverlay.addEventListener("click", () => {
      if (appSidebar) appSidebar.classList.remove("sidebar-open");
      mobileOverlay.classList.remove("active");
    });
  }

  // Active navigation highlight based on current path
  highlightActiveNavLinks();

  // Enforce authentication on private pages
  enforcePrivatePageAuth();

  // Sync user badge across app sidebar
  syncSidebarUserBadge();

  // Synchronize active trip ID across sidebar and navigation
  initActiveTripNavigation();
});

function enforcePrivatePageAuth() {
  const currentPath = window.location.pathname.split("/").pop() || "index.html";
  const privatePages = [
    "dashboard.html",
    "create_trip.html",
    "trip.html",
    "itinerary.html",
    "expenses.html",
    "recommendations.html",
    "profile.html",
    "exchange.html"
  ];

  if (privatePages.some(page => currentPath.toLowerCase().includes(page.toLowerCase()))) {
    if (typeof ApiService !== "undefined" && ApiService.auth) {
      ApiService.auth.requireAuth();
    }
  }
}

async function syncSidebarUserBadge() {
  if (typeof ApiService === "undefined" || !ApiService.auth || !ApiService.auth.isLoggedIn()) {
    return;
  }
  try {
    const user = await ApiService.auth.getMe();
    if (!user) return;

    const initials = user.name ? user.name.trim().split(/\s+/).map(n => n[0]).join("").slice(0, 2).toUpperCase() : "AK";
    document.querySelectorAll("#sidebar-avatar, .sidebar-footer .user-avatar").forEach(el => {
      el.textContent = initials;
    });
    document.querySelectorAll("#sidebar-user-name, .sidebar-footer .user-name").forEach(el => {
      el.textContent = user.name;
    });
    document.querySelectorAll(".sidebar-footer .user-role").forEach(el => {
      el.textContent = "Explorer (Logged In)";
    });
  } catch (e) {
    // Non-blocking on network hiccup
  }
}

function highlightActiveNavLinks() {
  const currentPath = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll(".sidebar-link, .nav-links a").forEach(link => {
    const href = link.getAttribute("href");
    if (href && (href === currentPath || href.endsWith(currentPath))) {
      link.classList.add("active");
    }
  });
}


/**
 * Validation Helpers
 */
const Validator = {
  setFieldError(inputElem, message) {
    const formGroup = inputElem.closest(".form-group");
    if (!formGroup) return;
    formGroup.classList.add("has-error");
    let errorElem = formGroup.querySelector(".form-error-msg");
    if (!errorElem) {
      errorElem = document.createElement("div");
      errorElem.className = "form-error-msg";
      formGroup.appendChild(errorElem);
    }
    errorElem.innerHTML = `<span>⚠</span> ${message}`;
  },

  clearFieldError(inputElem) {
    const formGroup = inputElem.closest(".form-group");
    if (!formGroup) return;
    formGroup.classList.remove("has-error");
    const errorElem = formGroup.querySelector(".form-error-msg");
    if (errorElem) {
      errorElem.textContent = "";
    }
  },

  isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
  }
};

/**
 * ============================================================================
 * UNIFIED ACTIVE TRIP & FLEXIBLE BUDGET CONTROLLER
 * Synchronizes active trip across Overview, Itinerary, Expenses & Recommendations
 * ============================================================================
 */

function parseBudgetInput(val) {
  if (typeof val === "number") return isNaN(val) ? NaN : val;
  if (!val || typeof val !== "string") return NaN;
  let clean = val.trim().replace(/₹/g, "").replace(/INR/i, "").replace(/\s+/g, "");
  // Support shorthand like "25k" or "25.5k"
  if (/^[0-9]+(\.[0-9]+)?[kK]$/.test(clean)) {
    const num = parseFloat(clean.slice(0, -1));
    return isNaN(num) ? NaN : num * 1000;
  }
  clean = clean.replace(/,/g, "");
  return parseFloat(clean);
}
function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getActiveTripId() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlId = urlParams.get("id");
  
  // If a valid user trip ID is passed in the URL (and not dummy 101), store and return it
  if (urlId && !isNaN(parseInt(urlId, 10)) && parseInt(urlId, 10) !== 101) {
    const parsed = parseInt(urlId, 10);
    localStorage.setItem("active_trip_id", String(parsed));
    return parsed;
  }
  
  // Otherwise check localStorage for the active trip
  const saved = localStorage.getItem("active_trip_id");
  if (saved && !isNaN(parseInt(saved, 10)) && parseInt(saved, 10) !== 101) {
    return parseInt(saved, 10);
  }

  // Purge any stale 101 in storage
  if (saved === "101") {
    localStorage.removeItem("active_trip_id");
    localStorage.removeItem("active_trip_destination");
    localStorage.removeItem("active_trip_meta");
  }

  // Default to Mysuru (130) instead of dummy Goa (101)
  return 130;
}

function setActiveTrip(tripId, destination, tripMeta = null) {
  // Prevent dummy Goa from overriding active user trips
  if (String(tripId) === "101" || destination === "Goa") {
    const currentActive = localStorage.getItem("active_trip_id");
    if (currentActive && String(currentActive) !== "101") {
      return;
    }
  }

  if (tripId && String(tripId) !== "101") {
    localStorage.setItem("active_trip_id", String(tripId));
  } else if (!localStorage.getItem("active_trip_id")) {
    localStorage.setItem("active_trip_id", "130");
  }

  if (destination && destination !== "Goa") {
    localStorage.setItem("active_trip_destination", destination);
  } else if (!localStorage.getItem("active_trip_destination") || localStorage.getItem("active_trip_destination") === "Goa") {
    localStorage.setItem("active_trip_destination", "Mysuru");
    destination = "Mysuru";
  }

  if (tripMeta && typeof tripMeta === "object") {
    try {
      localStorage.setItem("active_trip_meta", JSON.stringify(tripMeta));
      if (!destination && tripMeta.destination) {
        destination = tripMeta.destination;
        localStorage.setItem("active_trip_destination", destination);
      }
    } catch (e) {}
  }
  updateActiveTripNavigation(tripId, destination, tripMeta);
}

function updateActiveTripNavigation(activeTripId, activeDest, tripMeta = null) {
  const tid = (activeTripId && String(activeTripId) !== "101") ? activeTripId : (getActiveTripId() || 130);
  let dest = (activeDest && activeDest !== "Goa") ? activeDest : (localStorage.getItem("active_trip_destination") || "");

  // If meta is provided, store it
  if (tripMeta && typeof tripMeta === "object") {
    try {
      localStorage.setItem("active_trip_meta", JSON.stringify(tripMeta));
    } catch (e) {}
  }

  // Load stored meta if not passed
  let meta = tripMeta;
  if (!meta) {
    try {
      const savedMeta = localStorage.getItem("active_trip_meta");
      if (savedMeta) meta = JSON.parse(savedMeta);
    } catch (e) {}
  }

  if ((!dest || dest === "Goa") && meta && meta.destination && meta.destination !== "Goa") {
    dest = meta.destination;
  }
  if (!dest || dest === "Goa") {
    dest = "Mysuru";
  }

  // 1. Dynamically rewire sidebar navigation links and trip-subnav links to carry the active trip ID and contextual destination text
  document.querySelectorAll('.app-sidebar .sidebar-link, .trip-subnav-link').forEach(link => {
    const href = link.getAttribute("href");
    if (!href) return;

    const isSidebarLink = link.classList.contains("sidebar-link");

    if (href.startsWith("trip.html") || href.includes("/trip.html")) {
      link.setAttribute("href", `trip.html?id=${tid}`);
      if (isSidebarLink) {
        const span = link.querySelector("span");
        if (span) span.textContent = dest ? `${dest} Overview` : "Trip Overview";
      }
    } else if (href.startsWith("itinerary.html") || href.includes("/itinerary.html")) {
      link.setAttribute("href", `itinerary.html?id=${tid}`);
      if (isSidebarLink) {
        const span = link.querySelector("span");
        if (span) span.textContent = dest ? `${dest} Itinerary` : "Itinerary";
      }
    } else if (href.startsWith("expenses.html") || href.includes("/expenses.html")) {
      link.setAttribute("href", `expenses.html?id=${tid}`);
      if (isSidebarLink) {
        const span = link.querySelector("span");
        if (span) span.textContent = dest ? `${dest} Expenses` : "Expenses & Budget";
      }
    } else if (href.startsWith("recommendations.html") || href.includes("/recommendations.html")) {
      link.setAttribute("href", `recommendations.html?id=${tid}`);
      if (isSidebarLink) {
        const span = link.querySelector("span");
        if (span) span.textContent = dest ? `${dest} Recommendations` : "Recommendations";
      }
    }
  });

  // 2. Ensure active highlighting on sidebar navigation reflects the current page accurately
  const currentPath = window.location.pathname.toLowerCase();
  document.querySelectorAll('.app-sidebar .sidebar-link').forEach(link => {
    const rawHref = link.getAttribute("href") || "";
    const pageName = rawHref.split("?")[0].split("/").pop().toLowerCase();
    if (!pageName || pageName === "#") return;

    const isMatch = currentPath.endsWith("/" + pageName) || currentPath.endsWith(pageName) ||
                    (pageName === "dashboard.html" && (currentPath.endsWith("/") || currentPath.endsWith("/index.html") === false && currentPath === ""));
    if (isMatch) {
      link.classList.add("active");
    }
  });

  // 3. Update sidebar section title and render active trip summary mini-card
  document.querySelectorAll(".sidebar-section-title").forEach(span => {
    if (span.textContent.includes("Active Trip")) {
      span.innerHTML = dest 
        ? `Active Trip &bull; <span style="color: var(--primary); font-weight: 700;">${escapeHtml(dest)}</span>` 
        : "Active Trip";

      let card = span.nextElementSibling;
      const isCard = card && card.classList.contains("sidebar-active-trip-card");

      if (!dest) {
        if (isCard) card.remove();
        return;
      }

      if (!isCard) {
        card = document.createElement("div");
        card.className = "sidebar-active-trip-card";
        span.parentNode.insertBefore(card, span.nextSibling);
      }

      const tripName = meta && meta.trip_name && meta.trip_name !== dest ? meta.trip_name : "";
      const datesText = (meta && meta.start_date && meta.end_date)
        ? `${formatDateDisplay(meta.start_date)} – ${formatDateDisplay(meta.end_date)}`
        : "";
      const travellersText = (meta && meta.travellers) ? `${meta.travellers} Travelers` : "1 Traveler";
      const budgetText = (meta && meta.budget) ? formatINR(meta.budget) : "";

      card.innerHTML = `
        <div style="margin: 0.35rem 0.5rem 0.75rem; padding: 0.75rem 0.85rem; background: linear-gradient(135deg, rgba(37,99,235,0.08) 0%, rgba(14,165,233,0.08) 100%); border: 1px solid rgba(37,99,235,0.22); border-radius: var(--radius-md); box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.3rem;">
            <strong style="color: var(--primary-dark); font-size: 0.88rem; display: flex; align-items: center; gap: 0.35rem; font-weight: 700;">
              <span>📍</span> <span>${escapeHtml(dest)}</span>
            </strong>
            <span class="badge badge-primary" style="font-size: 0.65rem; padding: 0.15rem 0.45rem; font-weight: 700; border-radius: 999px;">Current Trip</span>
          </div>
          ${tripName ? `<div style="font-size: 0.75rem; font-weight: 600; color: var(--text-main); margin-bottom: 0.25rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(tripName)}">🏷 ${escapeHtml(tripName)}</div>` : ''}
          ${datesText ? `<div style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.25rem;"><span>📅</span> <span>${datesText}</span></div>` : ''}
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.72rem; color: var(--text-muted); padding-top: 0.3rem; border-top: 1px dashed rgba(37,99,235,0.2);">
            <span>👥 ${travellersText}</span>
            <strong style="color: var(--primary-dark); font-weight: 700;">${budgetText ? `💰 ${budgetText}` : ''}</strong>
          </div>
        </div>
      `;
    }
  });
}

// Global click interceptor for trip sub-module links: guarantees active trip continuity
document.addEventListener("click", (e) => {
  const link = e.target.closest("a");
  if (!link) return;
  const href = link.getAttribute("href");
  if (!href || href.startsWith("#") || href.startsWith("javascript:") || href.startsWith("http")) return;

  const targetPages = ["trip.html", "itinerary.html", "expenses.html", "recommendations.html"];
  for (const page of targetPages) {
    const isTarget = href === page || href.startsWith(`${page}?`) || href.includes(`/${page}`);
    if (isTarget) {
      // Check if this link specifically specifies a real user trip id (e.g. from dashboard card)
      let linkTripId = null;
      try {
        const u = new URL(href, window.location.origin);
        linkTripId = u.searchParams.get("id");
      } catch (err) {}

      let targetId = null;
      if (linkTripId && !isNaN(parseInt(linkTripId, 10)) && parseInt(linkTripId, 10) !== 101) {
        targetId = parseInt(linkTripId, 10);
        localStorage.setItem("active_trip_id", String(targetId));
      } else {
        const activeId = getActiveTripId();
        if (activeId && activeId !== 101) {
          targetId = activeId;
        }
      }

      if (targetId) {
        e.preventDefault();
        window.location.href = `${page}?id=${targetId}`;
        return;
      }
    }
  }
});

async function initActiveTripNavigation() {
  const urlParams = new URLSearchParams(window.location.search);
  const urlId = urlParams.get("id");
  if (urlId && !isNaN(parseInt(urlId, 10)) && parseInt(urlId, 10) !== 101) {
    localStorage.setItem("active_trip_id", urlId);
  }

  // Purge any residual dummy 101 / Goa in localStorage
  if (localStorage.getItem("active_trip_id") === "101") {
    localStorage.removeItem("active_trip_id");
  }
  if (localStorage.getItem("active_trip_destination") === "Goa") {
    localStorage.removeItem("active_trip_destination");
  }

  // Initial rewiring with currently known or stored active trip
  updateActiveTripNavigation();

  // If user is logged in, optionally verify active trip or fetch the latest trip
  if (typeof ApiService !== "undefined" && ApiService.trips && ApiService.auth && ApiService.auth.isLoggedIn()) {
    try {
      const storedId = localStorage.getItem("active_trip_id");
      const targetId = (urlId && urlId !== "101") ? urlId : (storedId && storedId !== "101" ? storedId : null);
      let activeObj = null;

      // 1. Try to fetch the target trip directly first for fast metadata access
      if (targetId) {
        try {
          activeObj = await ApiService.trips.get(targetId);
        } catch (eGet) {}
      }

      // 2. If not found or targetId is null, get trips list
      if (!activeObj) {
        const trips = await ApiService.trips.list();
        if (trips && trips.length > 0) {
          if (targetId) {
            activeObj = trips.find(t => String(t.trip_id) === String(targetId));
          }
          if (!activeObj) {
            // Prefer Mysuru or user's latest trip
            const mysuruTrip = trips.find(t => (t.destination || '').toLowerCase().includes("mysur"));
            activeObj = mysuruTrip || trips[trips.length - 1];
          }
        }
      }

      if (activeObj) {
        setActiveTrip(activeObj.trip_id, activeObj.destination, activeObj);
      }
    } catch (e) {
      // Non-blocking fallback
    }
  }
}

