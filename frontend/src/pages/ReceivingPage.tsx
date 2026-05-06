import { useEffect, useState } from "react";
import {
  ProductDTO,
  completeReceipt,
  createReceipt,
  fetchProducts,
  fetchReceipts,
} from "../api";
import { useToast } from "../store";

interface Line {
  product_id: number;
  sku: string;
  name: string;
  quantity: number;
  lot_batch?: string;
  location?: string;
}

export default function ReceivingPage() {
  const toast = useToast();
  const [poId, setPoId] = useState("");
  const [scan, setScan] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [recent, setRecent] = useState<any[]>([]);
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    try {
      setRecent(await fetchReceipts({}));
    } catch {}
  }
  useEffect(() => { refresh(); }, []);

  async function onScan(e: React.FormEvent) {
    e.preventDefault();
    if (!scan.trim()) return;
    const data = await fetchProducts({ search: scan.trim(), limit: 1, offset: 0 });
    if (!data.items.length) {
      toast.show(`Product not found: ${scan}`, "error");
      return;
    }
    const p: ProductDTO = data.items[0];
    setLines((prev) => {
      const existing = prev.find((l) => l.product_id === p.product_id);
      if (existing) {
        return prev.map((l) =>
          l.product_id === p.product_id ? { ...l, quantity: l.quantity + 1 } : l
        );
      }
      return [...prev, { product_id: p.product_id, sku: p.sku, name: p.name, quantity: 1 }];
    });
    setScan("");
  }

  function updateLine(idx: number, patch: Partial<Line>) {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, ...patch } : l)));
  }
  function removeLine(idx: number) {
    setLines((prev) => prev.filter((_, i) => i !== idx));
  }

  async function submit(thenComplete: boolean) {
    if (lines.length === 0) {
      toast.show("Add at least one line", "error");
      return;
    }
    setSubmitting(true);
    try {
      const payload: any = {
        lines: lines.map((l) => ({
          product_id: l.product_id,
          quantity: l.quantity,
          lot_batch: l.lot_batch || undefined,
          location: l.location || undefined,
        })),
      };
      if (poId.trim()) payload.po_id = Number(poId.trim());
      const r = await createReceipt(payload);
      if (thenComplete) {
        await completeReceipt(r.receipt_id);
      }
      toast.show(`Receipt #${r.receipt_id} created${thenComplete ? " & completed" : ""}`);
      if (r.discrepancies?.length) {
        toast.show(`${r.discrepancies.length} discrepancies flagged`, "error");
      }
      setLines([]);
      setPoId("");
      refresh();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h2>Receiving</h2>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="row">
          <div>
            <label>PO ID (optional)</label>
            <input className="input" value={poId} onChange={(e) => setPoId(e.target.value)} placeholder="123" />
          </div>
          <div>
            <label>Scan / SKU lookup</label>
            <form onSubmit={onScan} style={{ display: "flex", gap: 8 }}>
              <input
                className="input"
                value={scan}
                onChange={(e) => setScan(e.target.value)}
                placeholder="Scan barcode or type SKU"
                autoFocus
              />
              <button className="btn" type="submit">Add</button>
            </form>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>Lines</h3>
        <table>
          <thead>
            <tr><th>SKU</th><th>Name</th><th>Qty</th><th>Lot/Batch</th><th>Location</th><th></th></tr>
          </thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i}>
                <td>{l.sku}</td>
                <td>{l.name}</td>
                <td>
                  <input className="input" type="number" min={1} value={l.quantity}
                    onChange={(e) => updateLine(i, { quantity: Math.max(1, Number(e.target.value)) })}
                    style={{ width: 80 }} />
                </td>
                <td>
                  <input className="input" value={l.lot_batch || ""}
                    onChange={(e) => updateLine(i, { lot_batch: e.target.value })} />
                </td>
                <td>
                  <input className="input" value={l.location || ""}
                    onChange={(e) => updateLine(i, { location: e.target.value })} />
                </td>
                <td><button className="btn danger" onClick={() => removeLine(i)}>Remove</button></td>
              </tr>
            ))}
            {lines.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: "center", padding: 24, color: "#6b7280" }}>
                Scan a barcode or type a SKU to add lines.
              </td></tr>
            )}
          </tbody>
        </table>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn secondary" disabled={submitting} onClick={() => submit(false)}>
            Save receipt
          </button>
          <button className="btn" disabled={submitting} onClick={() => submit(true)}>
            Save & complete
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Recent receipts</h3>
        <table>
          <thead><tr><th>ID</th><th>PO</th><th>Status</th><th>Discrepancies</th><th>Created</th></tr></thead>
          <tbody>
            {recent.slice(0, 10).map((r: any) => (
              <tr key={r.receipt_id}>
                <td>{r.receipt_id}</td>
                <td>{r.po_id ?? "—"}</td>
                <td>{r.status}</td>
                <td>{r.discrepancies?.length || 0}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
