/**
 * ============================================================================
 * SMART TRAVEL PLANNER - REST API SERVICE CLIENT
 * Real FastAPI Backend Integration with JWT Authentication
 * ============================================================================
 */

const API_BASE = (typeof window !== "undefined" && window.location.protocol === "file:") 
  ? "http://127.0.0.1:8000" 
  : "";

const ApiService = {
  TOKEN_KEY: "stp_access_token",

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY) || "";
  },

  setToken(token) {
    if (token) {
      localStorage.setItem(this.TOKEN_KEY, token);
    } else {
      localStorage.removeItem(this.TOKEN_KEY);
    }
  },

  getHeaders(includeAuth = true) {
    const headers = {
      "Content-Type": "application/json",
      "Accept": "application/json"
    };
    if (includeAuth) {
      const token = this.getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }
    return headers;
  },

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    options.headers = {
      ...this.getHeaders(!options.skipAuth),
      ...(options.headers || {})
    };

    try {
      const response = await fetch(url, options);

      // If token expired/unauthorized and not already trying to log in, attempt auto-login as demo user
      if (response.status === 401 && !endpoint.includes("/api/users/login") && !endpoint.includes("/api/users/register")) {
        console.warn("[API] Received 401 Unauthorized. Attempting demo login...");
        const autoLoggedIn = await this.auth.autoLoginDemoUser();
        if (autoLoggedIn) {
          // Retry request with fresh token
          options.headers["Authorization"] = `Bearer ${this.getToken()}`;
          const retryResponse = await fetch(url, options);
          if (!retryResponse.ok) {
            const errData = await retryResponse.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${retryResponse.status}`);
          }
          return await retryResponse.json();
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.detail || `Request failed with status ${response.status}`;
        throw new Error(message);
      }

      return await response.json();
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  /**
   * AUTHENTICATION APIS
   */
  auth: {
    async register(userData) {
      const data = await ApiService.request("/api/users/register", {
        method: "POST",
        body: JSON.stringify(userData),
        skipAuth: true
      });
      if (data.access_token) {
        ApiService.setToken(data.access_token);
        sessionStorage.removeItem("stp_user_logged_out");
      }
      return data;
    },

    async login(credentials) {
      const data = await ApiService.request("/api/users/login", {
        method: "POST",
        body: JSON.stringify(credentials),
        skipAuth: true
      });
      if (data.access_token) {
        ApiService.setToken(data.access_token);
        sessionStorage.removeItem("stp_user_logged_out");
      }
      return data;
    },

    async getMe() {
      return await ApiService.request("/api/users/me");
    },

    async updateProfile(profileData) {
      return await ApiService.request("/api/users/me", {
        method: "PUT",
        body: JSON.stringify(profileData)
      });
    },

    isLoggedIn() {
      const token = ApiService.getToken();
      const hasLoggedOut = sessionStorage.getItem("stp_user_logged_out") === "true";
      return Boolean(token && !hasLoggedOut);
    },

    requireAuth() {
      if (!this.isLoggedIn()) {
        const current = window.location.pathname.split("/").pop() || "dashboard.html";
        window.location.href = `login.html?next=${encodeURIComponent(current)}`;
        return false;
      }
      return true;
    },

    async logout() {
      try {
        await ApiService.request("/api/users/logout", { method: "POST" });
      } catch (e) {
        // Ignore network errors on logout
      }
      ApiService.setToken("");
      sessionStorage.setItem("stp_user_logged_out", "true");
      window.location.href = "login.html";
    },

    async autoLoginDemoUser() {
      if (sessionStorage.getItem("stp_user_logged_out") === "true") {
        return false;
      }
      try {
        const res = await fetch(`${API_BASE}/api/users/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: "arun.kumar@example.com",
            password: "password123"
          })
        });
        if (res.ok) {
          const data = await res.json();
          if (data.access_token) {
            ApiService.setToken(data.access_token);
            sessionStorage.removeItem("stp_user_logged_out");
            return true;
          }
        }
      } catch (e) {
        console.warn("Auto demo login failed:", e);
      }
      return false;
    }
  },


  /**
   * TRIPS APIS
   */
  trips: {
    async list() {
      return await ApiService.request("/api/trips");
    },

    async get(tripId) {
      return await ApiService.request(`/api/trips/${tripId}`);
    },

    async create(tripData) {
      return await ApiService.request("/api/trips", {
        method: "POST",
        body: JSON.stringify(tripData)
      });
    },

    async update(tripId, tripData) {
      return await ApiService.request(`/api/trips/${tripId}`, {
        method: "PUT",
        body: JSON.stringify(tripData)
      });
    },

    async delete(tripId) {
      return await ApiService.request(`/api/trips/${tripId}`, {
        method: "DELETE"
      });
    },

    async summary(tripId) {
      return await ApiService.request(`/api/trips/${tripId}/summary`);
    }
  },

  /**
   * ITINERARY APIS
   */
  itinerary: {
    async list(tripId) {
      return await ApiService.request(`/api/trips/${tripId}/itinerary`);
    },

    async add(tripId, itemData) {
      return await ApiService.request(`/api/trips/${tripId}/itinerary`, {
        method: "POST",
        body: JSON.stringify(itemData)
      });
    },

    async update(itemId, itemData) {
      return await ApiService.request(`/api/itinerary/${itemId}`, {
        method: "PUT",
        body: JSON.stringify(itemData)
      });
    },

    async delete(itemId) {
      return await ApiService.request(`/api/itinerary/${itemId}`, {
        method: "DELETE"
      });
    }
  },

  /**
   * EXPENSES APIS
   */
  expenses: {
    async list(tripId) {
      return await ApiService.request(`/api/trips/${tripId}/expenses`);
    },

    async add(tripId, expenseData) {
      return await ApiService.request(`/api/trips/${tripId}/expenses`, {
        method: "POST",
        body: JSON.stringify(expenseData)
      });
    },

    async update(expenseId, expenseData) {
      return await ApiService.request(`/api/expenses/${expenseId}`, {
        method: "PUT",
        body: JSON.stringify(expenseData)
      });
    },

    async delete(expenseId) {
      return await ApiService.request(`/api/expenses/${expenseId}`, {
        method: "DELETE"
      });
    }
  },

  /**
   * RECOMMENDATIONS & SAVED EXPERIENCES APIS
   */
  recommendations: {
    async get(tripId, category = "", useDevAdapter = false, search = "", destination = "") {
      let url = `/api/trips/${tripId}/recommendations`;
      const params = [];
      if (category && category !== "All") {
        params.push(`category=${encodeURIComponent(category)}`);
      }
      if (search && search.trim()) {
        params.push(`search=${encodeURIComponent(search.trim())}`);
      }
      if (destination && destination.trim()) {
        params.push(`destination=${encodeURIComponent(destination.trim())}`);
      }
      if (useDevAdapter) {
        params.push("use_dev_adapter=true");
      }
      if (params.length > 0) {
        url += `?${params.join("&")}`;
      }
      return await ApiService.request(url);
    },

    async getByDestination(destination = "", category = "", useDevAdapter = false, search = "") {
      let url = `/api/experiences/recommendations`;
      const params = [];
      if (destination && destination.trim() && destination.trim() !== "All") {
        params.push(`destination=${encodeURIComponent(destination.trim())}`);
      }
      if (category && category !== "All") {
        params.push(`category=${encodeURIComponent(category)}`);
      }
      if (search && search.trim()) {
        params.push(`search=${encodeURIComponent(search.trim())}`);
      }
      if (useDevAdapter) {
        params.push("use_dev_adapter=true");
      }
      if (params.length > 0) {
        url += `?${params.join("&")}`;
      }
      return await ApiService.request(url);
    },

    async getHistory() {
      return await ApiService.request("/api/recommendations/history");
    },

    async save(tripId, expData) {
      return await ApiService.request(`/api/trips/${tripId}/experiences`, {
        method: "POST",
        body: JSON.stringify(expData)
      });
    },

    async getSaved(tripId) {
      return await ApiService.request(`/api/trips/${tripId}/experiences`);
    },

    async deleteSaved(savedId) {
      return await ApiService.request(`/api/experiences/${savedId}`, {
        method: "DELETE"
      });
    }
  }
};

// Seamless demo auto-login initialization
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    if (!ApiService.getToken()) {
      ApiService.auth.autoLoginDemoUser();
    }
  });
}
