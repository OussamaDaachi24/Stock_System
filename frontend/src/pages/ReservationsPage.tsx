import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createReservation,
  fetchProducts,
  fetchReservations,
  fetchSnapshot,
  releaseReservation,
} from "../api";
import { useToast } from "../store";
import { formatDate, formatNumber } from "../i18n/format";

export default function ReservationsPage() {
  const { t } = useTranslation(["reservations", "common"]);
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState<number | null>(null);
  const [productSku, setProductSku] = useState("");
  const [available, setAvailable] = useState<number | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [reference, setReference] = useState("");
  const [expiryDays, setExpiryDays] = useState(30);
  const [items, setItems] = useState<any[]>([]);

  async function refresh() {
    setItems(await fetchReservations({ status: "active" }));
  }
  useEffect(() => { refresh(); }, []);

  async function lookup() {
    if (!search.trim()) return;
    const data = await fetchProducts({ search, limit: 1, offset: 0 });
    if (!data.items.length) { toast.show(t("toast.lookupFirst"), "error"); return; }
    const p = data.items[0];
    setProductId(p.product_id);
    setProductSku(p.sku);
    try {
      const snap = await fetchSnapshot(p.product_id);
      setAvailable(snap.available);
    } catch { setAvailable(null); }
  }

  async function submit() {
    if (!productId) { toast.show(t("toast.lookupFirst"), "error"); return; }
    if (available !== null && quantity > available) {
      toast.show(t("toast.insufficient", { available }), "error");
      return;
    }
    try {
      await createReservation({
        product_id: productId,
        quantity,
        reference: reference || undefined,
        expiry_days: expiryDays,
      });
      toast.show(t("toast.created"));
      setProductId(null); setProductSku(""); setAvailable(null);
      setQuantity(1); setReference(""); setSearch("");
      refresh();
    } catch {}
  }

  async function release(id: number) {
    if (!confirm(t("toast.confirmRelease"))) return;
    await releaseReservation(id);
    toast.show(t("toast.released"));
    refresh();
  }

  return (
    <div>
      <h2>{t("title")}</h2>
      <div className="card" style={{ marginBottom: 12 }}>
        <h3>{t("quickReserve")}</h3>
        <div className="row">
          <div>
            <label>{t("fields.product")}</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="input" value={search} onChange={(e) => setSearch(e.target.value)} />
              <button className="btn secondary" onClick={lookup}>{t("actions.find", { ns: "common" })}</button>
            </div>
            {productSku && (
              <div style={{ fontSize: 12, marginTop: 4, color: available === 0 ? "var(--c-danger)" : "var(--c-success)" }}>
                {t("availability", { sku: productSku, available: available ?? "—" })}
              </div>
            )}
          </div>
          <div>
            <label>{t("fields.reference")}</label>
            <input className="input" value={reference} onChange={(e) => setReference(e.target.value)} />
          </div>
        </div>
        <div className="row">
          <div>
            <label>{t("fields.quantity")}</label>
            <input className="input" type="number" min={1} value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))} />
          </div>
          <div>
            <label>{t("fields.expiryDays")}</label>
            <input className="input" type="number" min={1} max={365} value={expiryDays}
              onChange={(e) => setExpiryDays(Math.max(1, Number(e.target.value)))} />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={submit}>{t("submit")}</button>
        </div>
      </div>

      <div className="card">
        <h3>{t("activeTitle")}</h3>
        <table>
          <thead><tr>
            <th>{t("table.id")}</th>
            <th>{t("table.product")}</th>
            <th>{t("table.qty")}</th>
            <th>{t("table.ref")}</th>
            <th>{t("table.expires")}</th>
            <th></th>
          </tr></thead>
          <tbody>
            {items.map((r) => {
              const days = Math.ceil(
                (new Date(r.expiry_timestamp).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
              );
              return (
                <tr key={r.reservation_id}>
                  <td>{r.reservation_id}</td>
                  <td>#{r.product_id}</td>
                  <td>{formatNumber(r.quantity, { maximumFractionDigits: 0 })}</td>
                  <td>{r.reference || "—"}</td>
                  <td>
                    <span style={{ color: days < 7 ? "var(--c-danger)" : "var(--c-text)" }}>
                      {t("expiresIn", { date: formatDate(r.expiry_timestamp), days })}
                    </span>
                  </td>
                  <td><button className="btn danger" onClick={() => release(r.reservation_id)}>{t("actions.release", { ns: "common" })}</button></td>
                </tr>
              );
            })}
            {items.length === 0 && (
              <tr><td colSpan={6} className="empty">{t("empty")}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
