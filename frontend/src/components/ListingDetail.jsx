import { useEffect, useState } from "react";
import { api } from "../api";

export default function ListingDetail({ productId, onClose }) {
  const [product, setProduct] = useState(null);
  const [priceHistory, setPriceHistory] = useState([]);
  const [dealScore, setDealScore] = useState(null);
  const [reviewSignals, setReviewSignals] = useState([]);
  const [watchlistItem, setWatchlistItem] = useState(null);
  const [threshold, setThreshold] = useState(70);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const listingId = product?.listings?.[0]?.listing_id;

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const p = await api.getProduct(productId);
      setProduct(p);
      const lid = p.listings?.[0]?.listing_id;
      if (lid) {
        const [history, score, signals, watchlist] = await Promise.all([
          api.getPriceHistory(lid),
          api.getDealScore(lid).catch(() => null),
          api.getReviewSignals(lid),
          api.getWatchlist(),
        ]);
        setPriceHistory(history);
        setDealScore(score);
        setReviewSignals(signals);
        setWatchlistItem(watchlist.find((w) => w.listing_id === lid) || null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]);

  async function handleRefreshNow() {
    setError("");
    try {
      await api.refreshNow();
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleWatchlistToggle() {
    setError("");
    try {
      if (watchlistItem) {
        await api.removeFromWatchlist(watchlistItem.watchlist_id);
      } else {
        await api.addToWatchlist(listingId, Number(threshold));
      }
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <div className="card">Loading...</div>;
  if (!product) return null;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <div>
          <h3 style={{ marginBottom: 4 }}>{product.name}</h3>
          <div className="muted">{product.brand} · {product.category.name}</div>
        </div>
        <button onClick={onClose} style={{ marginTop: 0, background: "#e2e2e5", color: "#333" }}>Close</button>
      </div>

      {error && <div className="error">{error}</div>}

      <div style={{ marginTop: 16 }}>
        <button onClick={handleRefreshNow}>Refresh price &amp; deal data now</button>
      </div>

      <h4 style={{ marginTop: 20 }}>Deal score</h4>
      {dealScore ? (
        <div>
          <strong style={{ fontSize: 22 }}>{dealScore.composite_score?.toFixed(1)}</strong> / 100
          <div className="muted">
            price score {dealScore.price_score?.toFixed(1)} · review score {dealScore.review_score?.toFixed(1)}
          </div>
        </div>
      ) : (
        <p className="muted">No deal score yet — click "Refresh" above.</p>
      )}

      <h4 style={{ marginTop: 20 }}>Price history ({priceHistory.length} snapshot{priceHistory.length === 1 ? "" : "s"})</h4>
      {priceHistory.length === 0 && <p className="muted">No price data yet.</p>}
      {priceHistory.map((snap) => (
        <div className="result-item" key={snap.snapshot_id}>
          ₹{snap.listed_price.toFixed(2)}
          {snap.true_price !== null && snap.true_price !== snap.listed_price && (
            <span className="muted"> (true price ₹{snap.true_price.toFixed(2)})</span>
          )}
          {snap.is_genuine_discount === false && <span className="error"> — not a genuine discount</span>}
          {snap.is_genuine_discount === true && <span className="success"> — genuine drop</span>}
          <div className="muted">{new Date(snap.recorded_at).toLocaleString()}</div>
        </div>
      ))}

      <h4 style={{ marginTop: 20 }}>Review signals</h4>
      {reviewSignals.length === 0 && <p className="muted">No review signals extracted yet.</p>}
      {reviewSignals.map((sig) => (
        <div key={sig.keyword_tag} className="result-item">
          <strong>{sig.keyword_tag}</strong> — mentioned {sig.mention_count}x
        </div>
      ))}

      <h4 style={{ marginTop: 20 }}>Watchlist</h4>
      {watchlistItem ? (
        <div>
          <p className="muted">
            On watchlist — alert threshold {watchlistItem.threshold_score}.
            {watchlistItem.last_alerted_at && (
              <> Last alerted {new Date(watchlistItem.last_alerted_at).toLocaleString()}.</>
            )}
          </p>
          <button onClick={handleWatchlistToggle}>Remove from watchlist</button>
        </div>
      ) : (
        <div>
          <label>Alert threshold (deal score)</label>
          <input type="number" min="0" max="100" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
          <button onClick={handleWatchlistToggle}>Add to watchlist</button>
        </div>
      )}
    </div>
  );
}
