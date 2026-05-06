import { useEffect, useState } from "react";
import { fetchLowStock, fetchMetrics, fetchReceipts, fetchReturns, fetchReservations } from "../api";
import { Link } from "react-router-dom";

export default function DashboardPage() {
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
      <h2>Dashboard</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12, marginBottom: 16 }}>
        <Stat label="Products" value={metrics?.products ?? "—"} />
        <Stat label="Ledger entries" value={metrics?.ledger_entries ?? "—"} />
        <Stat label="Active reservations" value={metrics?.active_reservations ?? reservations.length} />
        <Stat label="Open receipts" value={metrics?.open_receipts ?? receipts.length} />
        <Stat label="Pending returns" value={metrics?.pending_returns ?? returns.length} />
        <Stat label="Low-stock items" value={metrics?.low_stock ?? low.length} />
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>Quick links</h3>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <Link to="/receiving" className="btn">Receiving</Link>
          <Link to="/returns" className="btn">Returns</Link>
          <Link to="/reservations" className="btn">Reservations</Link>
          <Link to="/reports" className="btn secondary">Reports</Link>
        </div>
      </div>

      <div className="card">
        <h3>Low-stock products</h3>
        {low.length === 0 ? (
          <p style={{ color: "#6b7280" }}>All products above reorder threshold.</p>
        ) : (
          <table>
            <thead><tr><th>SKU</th><th>Name</th><th>On hand</th><th>Threshold</th></tr></thead>
            <tbody>
              {low.slice(0, 10).map((p) => (
                <tr key={p.product_id}>
                  <td>{p.sku}</td>
                  <td>{p.name}</td>
                  <td>{p.on_hand}</td>
                  <td>{p.reorder_threshold}</td>
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
      <div style={{ color: "#6b7280", fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 600 }}>{value}</div>
    </div>
  );
}
