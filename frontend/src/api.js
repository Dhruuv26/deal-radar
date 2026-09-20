const BASE_URL = "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  getCategories: () => request("/api/categories"),
  getRetailers: () => request("/api/retailers"),
  searchProducts: (q) => request(`/api/products/search?q=${encodeURIComponent(q)}`),
  addProduct: (payload) =>
    request("/api/products", { method: "POST", body: JSON.stringify(payload) }),
  getProduct: (productId) => request(`/api/products/${productId}`),

  getPriceHistory: (listingId) => request(`/api/listings/${listingId}/price-history`),
  getDealScore: (listingId) => request(`/api/listings/${listingId}/deal-score`),
  getReviewSignals: (listingId) => request(`/api/listings/${listingId}/review-signals`),

  getWatchlist: () => request("/api/watchlist"),
  addToWatchlist: (listingId, thresholdScore) =>
    request("/api/watchlist", {
      method: "POST",
      body: JSON.stringify({ listing_id: listingId, threshold_score: thresholdScore }),
    }),
  removeFromWatchlist: (watchlistId) =>
    request(`/api/watchlist/${watchlistId}`, { method: "DELETE" }),

  refreshNow: () => request("/api/ingestion/refresh-now", { method: "POST" }),
};
