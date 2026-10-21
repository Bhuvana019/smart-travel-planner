/**
 * ============================================================================
 * SMART TRAVEL PLANNER - RECOMMENDATIONS CONTROLLER (PHASE 5)
 * Real FastAPI Backend integration with External Experience Finder Service
 * ============================================================================
 */

let currentTripId = 130;
let currentTrip = null;
let currentCategory = "All";
let searchQuery = "";
let selectedDestinationFilter = "current";
let cachedExperiences = [];
let addedItineraryTitles = new Set();
let userTripsList = [];
let searchDebounceTimer = null;

function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
  initRecommendationsPage();
});

async function initRecommendationsPage() {
  const urlParams = new URLSearchParams(window.location.search);
  const tripParam = urlParams.get("id");
  if (tripParam && !isNaN(parseInt(tripParam, 10)) && parseInt(tripParam, 10) !== 101) {
    currentTripId = parseInt(tripParam, 10);
  } else if (typeof getActiveTripId === "function" && getActiveTripId()) {
    currentTripId = getActiveTripId();
  }

  setupRecsFilters();
  setupRecsSearch();
  setupUseTripInterestsButton();
  
  await loadUserTrips();
  showReadyState();
}

function showReadyState() {
  const readyCard = document.getElementById("recs-ready-card");
  const commConsole = document.getElementById("recs-comm-console");
  const gridContainer = document.getElementById("experiences-grid-container");
  const countBadge = document.getElementById("recs-results-count-badge");
  const emptyState = document.getElementById("experiences-empty-state");

  if (readyCard) readyCard.style.display = "block";
  if (commConsole) commConsole.style.display = "none";
  if (gridContainer) gridContainer.innerHTML = "";
  if (emptyState) emptyState.style.display = "none";
  if (countBadge) {
    countBadge.textContent = "Click '⚡ Get Recommendations' or search to query Experience Finder (:8001)";
  }
}

function triggerLiveRecommendations() {
  loadRecommendationsData(false);
}

async function loadUserTrips() {
  try {
    userTripsList = await ApiService.trips.list();
    populateTripSelector(userTripsList);

    // If currentTripId not in trips list, default to first trip
    if (userTripsList.length > 0) {
      const activeStoredId = localStorage.getItem("active_trip_id");
      let match = null;
      if (currentTripId && currentTripId !== 101) {
        match = userTripsList.find(t => t.trip_id === currentTripId);
      }
      if (!match && activeStoredId && activeStoredId !== "101") {
        match = userTripsList.find(t => String(t.trip_id) === String(activeStoredId));
      }
      if (!match) {
        match = userTripsList.find(t => (t.destination || '').toLowerCase().includes("mysur")) || userTripsList[userTripsList.length - 1];
      }
      currentTripId = match.trip_id;
      currentTrip = match;
      if (typeof setActiveTrip === "function") {
        setActiveTrip(currentTrip.trip_id, currentTrip.destination, currentTrip);
      }
      loadRecsTripMeta(currentTrip);
    }
  } catch (err) {
    console.warn("Failed to load user trips:", err);
  }
}

function populateTripSelector(trips) {
  const select = document.getElementById("recs-trip-select");
  if (!select) return;

  if (!trips || trips.length === 0) {
    select.innerHTML = `<option value="130" selected>Mysuru (friends)</option>`;
    return;
  }

  select.innerHTML = trips.map(t => `
    <option value="${t.trip_id}" ${t.trip_id === currentTripId ? "selected" : ""}>
      ${t.destination} (${t.trip_name || 'Vacation'})
    </option>
  `).join("");

  select.addEventListener("change", async (e) => {
    currentTripId = parseInt(e.target.value, 10);
    const newTrip = userTripsList.find(t => t.trip_id === currentTripId);
    if (newTrip) {
      currentTrip = newTrip;
      if (typeof setActiveTrip === "function") {
        setActiveTrip(currentTrip.trip_id, currentTrip.destination, currentTrip);
      }
      loadRecsTripMeta(currentTrip);
    }
    // Update browser URL query param without full reload
    const url = new URL(window.location);
    url.searchParams.set("id", currentTripId);
    window.history.replaceState({}, "", url);

    showReadyState();
  });
}

function loadRecsTripMeta(trip) {
  if (!trip) return;

  const destTitleElem = document.getElementById("recs-dest-title");
  const destBadgeElem = document.getElementById("recs-dest-badge");
  const datesSubElem = document.getElementById("recs-dates-sub");
  const backBtn = document.getElementById("recs-back-to-trip");

  if (destTitleElem) destTitleElem.textContent = `Recommended Experiences in ${trip.destination}`;
  if (destBadgeElem) destBadgeElem.textContent = trip.destination;
  if (datesSubElem) datesSubElem.textContent = `Curated activities tailored for ${trip.travellers} travelers • Target Budget: ${formatINR(trip.budget)}`;
  if (backBtn) backBtn.setAttribute("href", `trip.html?id=${trip.trip_id}`);

  // Update Ready State metadata fields
  const readyDest = document.getElementById("ready-dest-text");
  const readyTrav = document.getElementById("ready-travellers-text");
  const readyBud = document.getElementById("ready-budget-text");
  if (readyDest) readyDest.textContent = trip.destination;
  if (readyTrav) readyTrav.textContent = `${trip.travellers} Members`;
  if (readyBud) readyBud.textContent = `${formatINR(trip.budget)} Budget`;

  // Update trip subnavigation links to include current trip id
  document.querySelectorAll(".trip-subnav-link").forEach(link => {
    const href = link.getAttribute("href");
    if (href) {
      const base = href.split("?")[0];
      link.setAttribute("href", `${base}?id=${trip.trip_id}`);
    }
  });

  // Render Trip Interests Chips
  renderTripInterestsChips(trip.interests);
}

function renderTripInterestsChips(interestsStr) {
  const container = document.getElementById("trip-interests-container");
  if (!container) return;

  if (!interestsStr || !interestsStr.trim()) {
    container.innerHTML = `<span style="font-size: 0.85rem; color: var(--text-muted); font-style: italic;">No specific interests set</span>`;
    return;
  }

  const interests = interestsStr.split(",").map(i => i.trim()).filter(Boolean);
  container.innerHTML = interests.map(interest => `
    <button 
      class="badge badge-primary interest-chip-btn" 
      style="cursor: pointer; border: none; font-size: 0.85rem; padding: 0.35rem 0.75rem;" 
      title="Filter by ${interest}"
      onclick="selectInterestCategory('${escapeHtml(interest)}')">
      🏷 ${escapeHtml(interest)}
    </button>
  `).join("");
}

function selectInterestCategory(category) {
  currentCategory = category;
  // Update active pill
  document.querySelectorAll(".category-filter-pills .filter-pill").forEach(p => {
    const pillCat = p.getAttribute("data-category");
    if (pillCat && pillCat.toLowerCase() === category.toLowerCase()) {
      p.classList.add("active");
    } else {
      p.classList.remove("active");
    }
  });
  loadRecommendationsData(false);
}

function setupUseTripInterestsButton() {
  const btn = document.getElementById("btn-use-interests");
  if (!btn) return;

  btn.addEventListener("click", () => {
    if (!currentTrip || !currentTrip.interests) {
      showToast("No interests saved for this trip. Using 'All'.", "info");
      return;
    }
    const firstInterest = currentTrip.interests.split(",")[0].trim();
    if (firstInterest) {
      selectInterestCategory(firstInterest);
      showToast(`Filtering recommendations by trip interest: ${firstInterest}`, "info");
    }
  });
}

function setupRecsFilters() {
  const pills = document.querySelectorAll(".category-filter-pills .filter-pill");
  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      currentCategory = pill.getAttribute("data-category") || "All";
      loadRecommendationsData(false);
    });
  });
}

function resetRecsFilter() {
  currentCategory = "All";
  searchQuery = "";
  selectedDestinationFilter = "current";
  const searchInput = document.getElementById("recs-search-input");
  if (searchInput) searchInput.value = "";
  const destSelect = document.getElementById("recs-dest-filter-select");
  if (destSelect) destSelect.value = "current";
  document.querySelectorAll(".category-filter-pills .filter-pill").forEach(p => {
    if (p.getAttribute("data-category") === "All") p.classList.add("active");
    else p.classList.remove("active");
  });
  loadRecommendationsData(false);
}

function setupRecsSearch() {
  const input = document.getElementById("recs-search-input");
  if (input) {
    input.addEventListener("input", (e) => {
      searchQuery = e.target.value;
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        loadRecommendationsData(false);
      }, 400);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        clearTimeout(searchDebounceTimer);
        searchQuery = input.value;
        loadRecommendationsData(false);
      }
    });
  }

  const destSelect = document.getElementById("recs-dest-filter-select");
  if (destSelect) {
    destSelect.addEventListener("change", (e) => {
      selectedDestinationFilter = e.target.value;
      loadRecommendationsData(false);
    });
  }
}

function triggerPlacesSearch() {
  const input = document.getElementById("recs-search-input");
  if (input) {
    searchQuery = input.value;
  }
  const destSelect = document.getElementById("recs-dest-filter-select");
  if (destSelect) {
    selectedDestinationFilter = destSelect.value;
  }
  clearTimeout(searchDebounceTimer);
  loadRecommendationsData(false);
}

/**
 * Loads recommendations from the FastAPI backend which communicates with Experience Finder REST API.
 * Parameters:
 *  - useDevAdapter: if true, requests the clearly labelled local development mock adapter.
 */
async function loadRecommendationsData(useDevAdapter = false) {
  const getBtn = document.getElementById("btn-get-recommendations");
  const searchBtn = document.getElementById("btn-search-places");
  const errorCard = document.getElementById("recs-error-card");
  const countBadge = document.getElementById("recs-results-count-badge");
  const readyCard = document.getElementById("recs-ready-card");

  if (readyCard) readyCard.style.display = "none";

  if (getBtn) {
    getBtn.disabled = true;
    getBtn.innerHTML = `<span class="spinner"></span> Calling API...`;
  }
  if (searchBtn) {
    searchBtn.disabled = true;
    searchBtn.innerHTML = `<span class="spinner"></span> Searching API...`;
  }
  if (countBadge) {
    countBadge.textContent = "Connecting to Experience Finder API (:8001)...";
  }

  if (errorCard) errorCard.style.display = "none";
  const startTime = performance.now();

  try {
    // 1. Fetch current trip itinerary to detect already-scheduled items
    if (currentTripId) {
      try {
        const existingItinerary = await ApiService.itinerary.list(currentTripId);
        addedItineraryTitles = new Set(existingItinerary.map(item => item.activity.trim().toLowerCase()));
      } catch (itinErr) {
        console.warn("Could not fetch trip itinerary:", itinErr);
        addedItineraryTitles = new Set();
      }
    }

    // Determine target destination
    let destToQuery = "";
    if (selectedDestinationFilter === "current" && currentTrip) {
      destToQuery = currentTrip.destination;
    } else if (selectedDestinationFilter && selectedDestinationFilter !== "current") {
      destToQuery = selectedDestinationFilter;
    } else if (currentTrip) {
      destToQuery = currentTrip.destination;
    } else {
      destToQuery = "All";
    }

    // 2. Call backend recommendations endpoint (communicates via HTTPX with Experience Finder)
    let res;
    if (currentTripId && selectedDestinationFilter === "current") {
      res = await ApiService.recommendations.get(
        currentTripId,
        currentCategory,
        useDevAdapter,
        searchQuery,
        destToQuery
      );
    } else {
      res = await ApiService.recommendations.getByDestination(
        destToQuery,
        currentCategory,
        useDevAdapter,
        searchQuery
      );
    }

    const latencyMs = Math.round(performance.now() - startTime);

    // 3. Handle service failure / error state
    if (res.status === "ERROR") {
      cachedExperiences = [];
      renderErrorState(res);
      renderExperiencesList([]);
      if (countBadge) countBadge.textContent = "Experience Finder service unreachable";
      return;
    }

    // 4. Handle successful or mock response
    cachedExperiences = res.experiences || [];
    renderCommunicationConsole(res, latencyMs, destToQuery);
    renderSourceBanner(res);
    renderExperiencesList(cachedExperiences);

    if (countBadge) {
      const qDesc = searchQuery.trim() ? ` matching "${escapeHtml(searchQuery)}"` : "";
      const catDesc = currentCategory !== "All" ? ` in ${escapeHtml(currentCategory)}` : "";
      const destDesc = destToQuery && destToQuery !== "All" ? ` in ${escapeHtml(destToQuery)}` : " across India";
      countBadge.innerHTML = `Found <strong>${cachedExperiences.length}</strong> places${qDesc}${catDesc}${destDesc}`;
    }

  } catch (err) {
    console.error("Recommendations API error:", err);
    renderErrorState({
      target_url: "http://localhost:8001/api/experiences",
      status_message: "Network Error: Could not communicate with Experience Finder API",
      error_detail: err.message || "Failed to fetch recommendations. Ensure the service is online or use the dev adapter."
    });
    renderExperiencesList([]);
    if (countBadge) countBadge.textContent = "Network error connecting to API";
  } finally {
    if (getBtn) {
      getBtn.disabled = false;
      getBtn.innerHTML = `<span id="btn-recs-icon">⚡</span> Get Recommendations`;
    }
    if (searchBtn) {
      searchBtn.disabled = false;
      searchBtn.innerHTML = `<span>⚡</span> Search Places`;
    }
  }
}

function renderCommunicationConsole(res, latencyMs, targetDest) {
  const commConsole = document.getElementById("recs-comm-console");
  const readyCard = document.getElementById("recs-ready-card");
  if (readyCard) readyCard.style.display = "none";
  if (!commConsole) return;

  commConsole.style.display = "block";

  const now = new Date();
  const timeElem = document.getElementById("comm-timestamp");
  if (timeElem) timeElem.textContent = `• Transacted at ${now.toLocaleTimeString()}`;

  const reqDest = document.getElementById("comm-req-dest");
  const reqTravellers = document.getElementById("comm-req-travellers");
  const reqBudget = document.getElementById("comm-req-budget");
  const reqCat = document.getElementById("comm-req-cat");
  const reqSearch = document.getElementById("comm-req-search");
  const reqEndpoint = document.getElementById("comm-req-endpoint");

  const travellersCount = currentTrip ? currentTrip.travellers : 1;
  const budgetVal = currentTrip ? currentTrip.budget : 0;

  if (reqDest) reqDest.textContent = targetDest || "All India";
  if (reqTravellers) reqTravellers.textContent = `${travellersCount} Travelers`;
  if (reqBudget) reqBudget.textContent = formatINR(budgetVal);
  if (reqCat) reqCat.textContent = currentCategory || "All";
  if (reqSearch) reqSearch.textContent = searchQuery ? `"${searchQuery}"` : "None (Full Catalog)";
  if (reqEndpoint) {
    reqEndpoint.textContent = `GET /api/experiences?destination=${encodeURIComponent(targetDest || '')}&category=${encodeURIComponent(currentCategory || '')}&travellers=${travellersCount}&budget=${budgetVal}`;
  }

  const resBadge = document.getElementById("comm-res-status-badge");
  const resCount = document.getElementById("comm-res-count");
  const resLatency = document.getElementById("comm-res-latency");

  const isMock = res && res.status === "DEV_MOCK";
  const count = (res && res.experiences) ? res.experiences.length : 0;

  if (resBadge) {
    if (isMock) {
      resBadge.textContent = "DEV MOCK ADAPTER";
      resBadge.style.background = "#fef3c7";
      resBadge.style.color = "#92400e";
      resBadge.style.borderColor = "#fcd34d";
    } else {
      resBadge.textContent = "HTTP 200 OK (LIVE)";
      resBadge.style.background = "#dcfce7";
      resBadge.style.color = "#15803d";
      resBadge.style.borderColor = "#86efac";
    }
  }

  if (resCount) {
    resCount.textContent = `${count} Places Dispatched Live`;
  }

  if (resLatency) {
    resLatency.textContent = `~${latencyMs} ms (Direct HTTPX Microservice)`;
  }
}

function renderErrorState(errData) {
  const errorCard = document.getElementById("recs-error-card");
  const errorUrl = document.getElementById("recs-error-url");
  const errorTitle = document.getElementById("recs-error-title");
  const errorDetail = document.getElementById("recs-error-detail");
  const sourceCard = document.getElementById("recs-source-card");

  if (sourceCard) sourceCard.style.display = "none";

  if (errorCard) {
    errorCard.style.display = "block";
    if (errorUrl) errorUrl.textContent = errData.target_url || "http://localhost:8001";
    if (errorTitle) errorTitle.textContent = errData.status_message || "Experience Finder Service Unreachable";
    if (errorDetail) errorDetail.textContent = errData.error_detail || "Connection timed out or failed. Please retry or test with local dev mock adapter.";
  }
}

function renderSourceBanner(data) {
  const sourceCard = document.getElementById("recs-source-card");
  const indicator = document.getElementById("recs-source-indicator");
  const urlElem = document.getElementById("recs-source-url");
  const descElem = document.getElementById("recs-source-desc");

  if (!sourceCard) return;
  sourceCard.style.display = "block";

  const isExt = Boolean(data && data.is_external);
  const isMock = data && data.status === "DEV_MOCK";

  if (indicator) {
    if (isExt) {
      indicator.textContent = "🟢 Live External API (Experience Finder)";
      indicator.className = "badge badge-success";
    } else if (isMock) {
      indicator.textContent = "⚠️ LOCAL DEVELOPMENT MOCK ADAPTER (MOCK DATA - NOT REAL API)";
      indicator.className = "badge badge-warning";
    } else {
      indicator.textContent = "ℹ️ " + (data.source || "Experience Catalog");
      indicator.className = "badge badge-primary";
    }
  }

  if (urlElem) {
    urlElem.textContent = isExt 
      ? `Live: ${data.target_url}` 
      : `Target: ${data.target_url || 'http://localhost:8001'} (Mock Adapter)`;
  }

  if (descElem) {
    descElem.textContent = data.status_message || (isExt ? "Live response from external Experience Finder service." : "Local mock adapter data for development testing.");
  }

  sourceCard.style.borderLeftColor = isExt ? "var(--success)" : "var(--warning)";
  sourceCard.style.background = isMock ? "#fffbeb" : "var(--bg-surface)";
}

function renderExperiencesList(experiences) {
  const container = document.getElementById("experiences-grid-container");
  const emptyState = document.getElementById("experiences-empty-state");
  const emptyTitle = document.getElementById("empty-state-title");
  const emptyDesc = document.getElementById("empty-state-desc");
  if (!container) return;

  const filtered = experiences || [];

  if (filtered.length === 0) {
    container.innerHTML = "";
    if (emptyState) {
      emptyState.style.display = "flex";
      if (searchQuery.trim()) {
        if (emptyTitle) emptyTitle.textContent = "No search results";
        if (emptyDesc) emptyDesc.textContent = `No experiences matched "${escapeHtml(searchQuery)}". Try searching another place or clearing the search.`;
      } else {
        const dest = (selectedDestinationFilter !== "current" && selectedDestinationFilter) ? selectedDestinationFilter : (currentTrip ? currentTrip.destination : "selected destination");
        if (emptyTitle) emptyTitle.textContent = `No experiences found for ${escapeHtml(dest)}`;
        if (emptyDesc) emptyDesc.textContent = `No activities cataloged for ${escapeHtml(dest)} in category "${escapeHtml(currentCategory)}". Try selecting another category or "All".`;
      }
    }
    return;
  }

  if (emptyState) emptyState.style.display = "none";

  const bgGradients = {
    Adventure: "linear-gradient(135deg, #0284c7, #0369a1)",
    Beach: "linear-gradient(135deg, #06b6d4, #0891b2)",
    Nature: "linear-gradient(135deg, #10b981, #059669)",
    Culture: "linear-gradient(135deg, #f59e0b, #d97706)",
    Food: "linear-gradient(135deg, #ea580c, #c2410c)",
    Leisure: "linear-gradient(135deg, #8b5cf6, #6d28d9)"
  };

  container.innerHTML = filtered.map(rec => {
    const nameLower = (rec.name || "").trim().toLowerCase();
    const isAlreadyAdded = addedItineraryTitles.has(nameLower);
    const cardBg = bgGradients[rec.category] || "linear-gradient(135deg, #0284c7, #0f766e)";

    // Rating display: only display rating if supplied by the API (never invent fake ratings!)
    let ratingHtml = "";
    if (rec.rating !== null && rec.rating !== undefined && !isNaN(rec.rating)) {
      ratingHtml = `<span class="experience-rating-pill">⭐ ${Number(rec.rating).toFixed(1)}</span>`;
    }

    let rawImg = rec.image_url || "";
    if (rawImg.startsWith("/")) {
      const partnerBase = window.location.port === "8000" ? "http://localhost:8001" : "";
      rawImg = partnerBase + rawImg;
    }
    const imgStyle = rawImg 
      ? `background: linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0.65) 100%), url('${escapeHtml(rawImg)}') center/cover no-repeat;`
      : `background: ${cardBg};`;

    let locationHtml = "";
    if (rec.locality || rec.destination) {
      locationHtml = `<div style="font-size: 0.8rem; color: var(--primary); font-weight: 600; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.3rem;">
        <span>📍</span> <span>${escapeHtml(rec.locality || rec.destination)}</span>
      </div>`;
    }

    let durationHtml = "";
    if (rec.duration) {
      durationHtml = `<span style="font-size: 0.75rem; background: rgba(0,0,0,0.55); color: #fff; padding: 0.2rem 0.5rem; border-radius: 999px; backdrop-filter: blur(4px);">⏱ ${escapeHtml(rec.duration)}</span>`;
    }

    return `
      <div class="experience-card" data-rec-id="${rec.id}">
        <div style="background: #f8fafc; border-bottom: 1px solid #e2e8f0; padding: 0.45rem 0.85rem; display: flex; align-items: center; justify-content: space-between;">
          <span class="origin-badge-live">
            <span>🟢</span> Live from Experience Finder (:8001)
          </span>
          <span style="font-size: 0.725rem; color: #64748b; font-weight: 600;">ID #${rec.id}</span>
        </div>
        <div class="experience-card-img" style="${imgStyle}">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
            <span class="experience-category-pill">${escapeHtml(rec.category)}</span>
            <div style="display: flex; gap: 0.35rem; align-items: center;">
              ${durationHtml}
              ${ratingHtml}
            </div>
          </div>
        </div>
        <div class="experience-card-body">
          ${locationHtml}
          <h4 class="experience-title">${escapeHtml(rec.name)}</h4>
          <p class="experience-desc">${escapeHtml(rec.description || 'Curated destination recommendation.')}</p>
        </div>
        <div class="experience-card-footer">
          <div class="experience-price ${rec.price === 0 ? 'free' : ''}">
            ${rec.price === 0 ? 'Free' : formatINR(rec.price)}
          </div>
          <button 
            class="btn btn-sm ${isAlreadyAdded ? 'btn-secondary' : 'btn-primary'} add-to-itinerary-btn"
            ${isAlreadyAdded ? 'disabled' : ''}
            onclick="handleAddToItinerary(${rec.id}, this)">
            ${isAlreadyAdded ? 'Added to Itinerary ✓' : '+ Add to Itinerary'}
          </button>
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Handles adding an experience card to the trip itinerary.
 * Avoids duplicate itinerary entries when a user adds the same experience repeatedly.
 */
async function handleAddToItinerary(expId, btnElem) {
  if (btnElem.disabled) return;

  const rec = cachedExperiences.find(e => e.id == expId);
  if (!rec) return;

  const nameLower = rec.name.trim().toLowerCase();
  if (addedItineraryTitles.has(nameLower)) {
    showToast(`"${rec.name}" is already in your trip itinerary.`, "info");
    btnElem.disabled = true;
    btnElem.innerHTML = "Added to Itinerary ✓";
    btnElem.className = "btn btn-sm btn-secondary add-to-itinerary-btn";
    return;
  }

  btnElem.disabled = true;
  btnElem.innerHTML = `<span class="spinner"></span> Adding...`;

  try {
    const startDate = (currentTrip && currentTrip.start_date) ? currentTrip.start_date : new Date().toISOString().split("T")[0];
    const destination = (currentTrip && currentTrip.destination) ? currentTrip.destination : "Destination";

    // 1. Add to Itinerary in Database
    const itinItem = await ApiService.itinerary.add(currentTripId, {
      date: startDate,
      time: "10:00",
      activity: rec.name,
      location: `${destination} (${rec.category})`,
      category: rec.category || "General",
      estimated_cost: parseFloat(rec.price) || 0.0,
      notes: rec.description || "Added from Experience Finder recommendation"
    });

    // 2. Also record in Saved Experiences
    try {
      await ApiService.recommendations.save(currentTripId, {
        experience_id: typeof rec.id === 'number' ? rec.id : 1,
        name: rec.name,
        category: rec.category,
        price: rec.price,
        rating: rec.rating
      });
    } catch (saveErr) {
      console.warn("Saved experience record notice:", saveErr);
    }

    // 3. Mark as added to prevent duplicate entries
    addedItineraryTitles.add(nameLower);
    btnElem.className = "btn btn-sm btn-secondary add-to-itinerary-btn";
    btnElem.innerHTML = "Added to Itinerary ✓";

    showToast(`"${rec.name}" successfully added to your trip itinerary!`, "success");
  } catch (err) {
    showToast(err.message || "Failed to add experience to itinerary", "error");
    btnElem.disabled = false;
    btnElem.innerHTML = "+ Add to Itinerary";
  }
}
