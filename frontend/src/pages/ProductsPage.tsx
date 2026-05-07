import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { ProductDTO, fetchProducts } from "../api";
import { useAuth } from "../store";
import ProductForm from "../components/ProductForm";

const PAGE_SIZE = 20;

export default function ProductsPage() {
  const { t } = useTranslation(["products", "common", "enums"]);
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
      <h2>{t("title")}</h2>
      <div className="card">
        <div className="toolbar">
          <form onSubmit={onSearchSubmit} style={{ display: "flex", gap: 8, flex: 1 }}>
            <input
              className="input"
              placeholder={t("searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="btn" type="submit">{t("actions.search", { ns: "common" })}</button>
          </form>
          {canMutate && (
            <button className="btn" onClick={() => setCreating(true)} style={{ marginInlineStart: 8 }}>
              {t("newProduct")}
            </button>
          )}
        </div>

        <table>
          <thead>
            <tr>
              <th>{t("table.sku")}</th>
              <th>{t("table.name")}</th>
              <th>{t("table.barcode")}</th>
              <th>{t("table.uom")}</th>
              <th>{t("table.category")}</th>
              <th>{t("table.reorder")}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.product_id}>
                <td>{p.sku}</td>
                <td>{p.name}</td>
                <td>{p.barcode || "—"}</td>
                <td>{t(`uom.${p.unit_of_measure}`, { ns: "enums", defaultValue: p.unit_of_measure })}</td>
                <td>{p.category || "—"}</td>
                <td>{p.reorder_threshold ?? "—"}</td>
                <td>
                  {canMutate && (
                    <button className="btn secondary" onClick={() => setEditing(p)}>
                      {t("actions.edit", { ns: "common" })}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">
                  {t("empty")}
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="toolbar" style={{ marginTop: 16 }}>
          <span style={{ color: "var(--c-text-muted)", fontSize: 13 }}>
            {t("pagination", { total, from: offset + 1, to: Math.min(offset + items.length, total) })}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              className="btn secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              {t("actions.prev", { ns: "common" })}
            </button>
            <button
              className="btn secondary"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              {t("actions.next", { ns: "common" })}
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
