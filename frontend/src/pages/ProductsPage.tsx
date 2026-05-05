import { useEffect, useState } from "react";
import { ProductDTO, fetchProducts } from "../api";
import { useAuth } from "../store";
import ProductForm from "../components/ProductForm";

const PAGE_SIZE = 20;

export default function ProductsPage() {
  const role = useAuth((s) => s.user?.role);
  const canMutate = role === "admin" || role === "manager";

  const [items, setItems] = useState<ProductDTO[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<ProductDTO | null>(null);
  const [creating, setCreating] = useState(false);

  async function load() {
    const data = await fetchProducts({ search: search || undefined, limit: PAGE_SIZE, offset });
    setItems(data.items);
    setTotal(data.total);
  }

  useEffect(() => {
    load();
  }, [offset]);

  function onSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setOffset(0);
    load();
  }

  return (
    <div>
      <h2>Products</h2>
      <div className="card">
        <div className="toolbar">
          <form onSubmit={onSearchSubmit} style={{ display: "flex", gap: 8, flex: 1 }}>
            <input
              className="input"
              placeholder="Search by SKU, name, or barcode"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="btn" type="submit">Search</button>
          </form>
          {canMutate && (
            <button className="btn" onClick={() => setCreating(true)} style={{ marginLeft: 8 }}>
              + New product
            </button>
          )}
        </div>

        <table>
          <thead>
            <tr>
              <th>SKU</th>
              <th>Name</th>
              <th>Barcode</th>
              <th>UoM</th>
              <th>Category</th>
              <th>Reorder</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.product_id}>
                <td>{p.sku}</td>
                <td>{p.name}</td>
                <td>{p.barcode || "—"}</td>
                <td>{p.unit_of_measure}</td>
                <td>{p.category || "—"}</td>
                <td>{p.reorder_threshold ?? "—"}</td>
                <td>
                  {canMutate && (
                    <button className="btn secondary" onClick={() => setEditing(p)}>
                      Edit
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: 32, color: "#6b7280" }}>
                  No products found.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="toolbar" style={{ marginTop: 16 }}>
          <span style={{ color: "#6b7280", fontSize: 13 }}>
            {total} total · showing {offset + 1}–{Math.min(offset + items.length, total)}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Prev
            </button>
            <button
              className="btn secondary"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {creating && (
        <ProductForm
          mode="create"
          onClose={() => setCreating(false)}
          onSaved={() => {
            setCreating(false);
            load();
          }}
        />
      )}
      {editing && (
        <ProductForm
          mode="edit"
          product={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}
