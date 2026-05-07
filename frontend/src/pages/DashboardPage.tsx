import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetchLowStock, fetchMetrics, fetchReceipts, fetchReturns, fetchReservations } from "../api";
import { Link } from "react-router-dom";
import { formatNumber } from "../i18n/format";

export default function DashboardPage() {
  const { t } = useTranslation(["dashboard", "nav"]);
  const [metrics, setMetrics] = useState<any>(null);
  const [low, setLow] = useState<any[]>([]);
  const [receipts, setReceipts] = useState<any[]>([]);
  const [returns, setReturns] = useState<any[]>([]);
  const [reservations, setReservations] = useState<any[]>([]);

  async function load() {
    try {
      const [m, lo, rec, ret, res] = await Promise.all([
        fetchMetrics().catch(() => null),
        fetchLowStock(),
        fetchReceipts({ status: "open" }).catch(() => []),
        fetchReturns({ status: "intake" }).catch(() => []),
        fetchReservations({ status: "active" }).catch(() => []),
      ]);
      setMetrics(m);
      setLow(lo);
      setReceipts(rec || []);
      setReturns(ret || []);
      setReservations(res || []);
    } catch {}
  }

  useEffect(() => { load(); }, []);

  return (
    <div>
      <h2>{t("title")}</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 16 }}>
        <Stat label={t("stats.products")} value={metrics?.products} />
        <Stat label={t("stats.ledgerEntries")} value={metrics?.ledger_entries} />
        <Stat label={t("stats.activeReservations")} value={metrics?.active_reservations ?? reservations.length} />
        <Stat label={t("stats.openReceipts")} value={metrics?.open_receipts ?? receipts.length} />
        <Stat label={t("stats.pendingReturns")} value={metrics?.pending_returns ?? returns.length} />
        <Stat label={t("stats.lowStock")} value={metrics?.low_stock ?? low.length} />
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>{t("quickLinks")}</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/receiving" className="btn">{t("receiving", { ns: "nav" })}</Link>
          <Link to="/returns" className="btn">{t("returns", { ns: "nav" })}</Link>
          <Link to="/reservations" className="btn">{t("reservations", { ns: "nav" })}</Link>
          <Link to="/reports" className="btn secondary">{t("reports", { ns: "nav" })}</Link>
        </div>
      </div>

      <div className="card">
        <h3>{t("lowStockTitle")}</h3>
        {low.length === 0 ? (
          <p className="empty" style={{ padding: 0, textAlign: "start" }}>{t("lowStockEmpty")}</p>
        ) : (
          <table>
            <thead><tr>
              <th>{t("table.sku")}</th>
              <th>{t("table.name")}</th>
              <th>{t("table.onHand")}</th>
              <th>{t("table.threshold")}</th>
            </tr></thead>
            <tbody>
              {low.slice(0, 10).map((p) => (
                <tr key={p.product_id}>
                  <td>{p.sku}</td>
                  <td>{p.name}</td>
                  <td>{formatNumber(p.on_hand)}</td>
                  <td>{formatNumber(p.reorder_threshold)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value === null || value === undefined ? "—" : formatNumber(value, { maximumFractionDigits: 0 })}</div>
    </div>
  );
}
