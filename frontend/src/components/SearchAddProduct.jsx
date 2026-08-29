import { useEffect, useState } from "react";
import { api } from "../api";

export default function SearchAddProduct() {
  const [categories, setCategories] = useState([]);
  const [retailers, setRetailers] = useState([]);

  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [searchError, setSearchError] = useState("");

  const [form, setForm] = useState({
    name: "",
    brand: "",
    category_id: "",
    retailer_id: "",
    retailer_sku: "",
    product_url: "",
  });
  const [addError, setAddError] = useState("");
  const [addSuccess, setAddSuccess] = useState("");

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
    api.getRetailers().then(setRetailers).catch(() => {});
  }, []);

  async function handleSearch(e) {
    e.preventDefault();
    setSearchError("");
    try {
      const data = await api.searchProducts(query);
      setResults(data);
    } catch (err) {
      setSearchError(err.message);
    }
  }

  async function handleAdd(e) {
    e.preventDefault();
    setAddError("");
    setAddSuccess("");
    try {
      const payload = {
        name: form.name,
        brand: form.brand || null,
        category_id: Number(form.category_id),
        listing: {
          retailer_id: Number(form.retailer_id),
          retailer_sku: form.retailer_sku,
          product_url: form.product_url,
        },
      };
      const product = await api.addProduct(payload);
      setAddSuccess(`Added "${product.name}" and started tracking it.`);
      setForm({ name: "", brand: "", category_id: "", retailer_id: "", retailer_sku: "", product_url: "" });
    } catch (err) {
      setAddError(err.message);
    }
  }

  return (
    <div className="app">
      <h1>Deal Radar</h1>
      <div className="notice">
        This build implements <strong>Product Search &amp; Catalog Management (P1)</strong> only.
        Price history, deal scores, review signals, watchlists, and alerts are not implemented
        yet — see the README for the full status.
      </div>

      <div className="card">
        <h3>Search tracked products</h3>
        <form onSubmit={handleSearch}>
          <label>Product name or brand</label>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. Logitech" />
          <button type="submit">Search</button>
        </form>
        {searchError && <div className="error">{searchError}</div>}
        {results && results.length === 0 && <p className="muted">No matching products tracked yet.</p>}
        {results && results.length > 0 && (
          <div style={{ marginTop: 16 }}>
            {results.map((r) => (
              <div className="result-item" key={r.product_id}>
                <strong>{r.name}</strong> {r.brand ? `— ${r.brand}` : ""}
                <div className="muted">
                  {r.category_name} · {r.listing_count} listing{r.listing_count === 1 ? "" : "s"} tracked
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3>Add a product to track</h3>
        <form onSubmit={handleAdd}>
          <label>Product name</label>
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />

          <label>Brand</label>
          <input value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />

          <label>Category</label>
          <select required value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })}>
            <option value="">Select a category</option>
            {categories.map((c) => (
              <option key={c.category_id} value={c.category_id}>{c.name}</option>
            ))}
          </select>

          <label>Retailer</label>
          <select required value={form.retailer_id} onChange={(e) => setForm({ ...form, retailer_id: e.target.value })}>
            <option value="">Select a retailer</option>
            {retailers.map((r) => (
              <option key={r.retailer_id} value={r.retailer_id}>{r.name}</option>
            ))}
          </select>

          <label>Retailer SKU</label>
          <input required value={form.retailer_sku} onChange={(e) => setForm({ ...form, retailer_sku: e.target.value })} />

          <label>Product URL</label>
          <input required value={form.product_url} onChange={(e) => setForm({ ...form, product_url: e.target.value })} />

          <button type="submit">Add to tracking</button>
        </form>
        {addError && <div className="error">{addError}</div>}
        {addSuccess && <div className="success">{addSuccess}</div>}
      </div>
    </div>
  );
}
