import { useEffect, useState } from "react";
import { createReturn, fetchProducts, fetchReturns, setReturnDisposition } from "../api";
import { useToast } from "../store";

const REASONS = ["defective", "wrong_item", "customer_request", "expired", "other"] as const;
const DISPOSITIONS = ["restock", "scrap", "repair"] as const;

export default function ReturnsPage() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [productId, setProductId] = useState<number | null>(null);
  const [productSku, setProductSku] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [reason, setReason] = useState<string>("defective");
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  const [items, setItems] = useState<any[]>([]);
  const [disposing, setDisposing] = useState<any | null>(null);

  async function refresh() {
    setItems(await fetchReturns({}));
  }
  useEffect(() => { refresh(); }, []);

  async function lookup() {
    if (!search.trim()) return;
    const data = await fetchProducts({ search, limit: 1, offset: 0 });
    if (!data.items.length) {
      toast.show("Product not found", "error");
      return;
    }
    setProductId(data.items[0].product_id);
    setProductSku(data.items[0].sku);
  }

  async function submit() {
    if (!productId) {
      toast.show("Look up a product first", "error");
      return;
    }
    await createReturn({
      product_id: productId,
      quantity,
      reason,
      reference: reference || undefined,
      receiving_notes: notes || undefined,
    });
    toast.show("Return created");
    setProductId(null); setProductSku(""); setQuantity(1); setReason("defective");
    setReference(""); setNotes(""); setSearch("");
    refresh();
  }

  return (
    <div>
      <h2>Returns</h2>
      <div className="card" style={{ marginBottom: 12 }}>
        <h3>Create return</h3>
        <div className="row">
          <div>
            <label>Product (SKU/name/barcode)</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="input" value={search} onChange={(e) => setSearch(e.target.value)} />
              <button className="btn secondary" onClick={lookup}>Find</button>
            </div>
            {productSku && <div style={{ fontSize: 12, color: "#059669", marginTop: 4 }}>Selected: {productSku}</div>}
          </div>
          <div>
            <label>Quantity</label>
            <input className="input" type="number" min={1} value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))} />
          </div>
        </div>
        <div className="row">
          <div>
            <label>Reason</label>
            <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
              {REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label>Order reference (optional)</label>
            <input className="input" value={reference} onChange={(e) => setReference(e.target.value)} />
          </div>
        </div>
        <label>Notes</label>
        <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={submit}>Create return</button>
        </div>
      </div>

      <div className="card">
        <h3>Return queue</h3>
        <table>
          <thead><tr><th>ID</th><th>Product</th><th>Qty</th><th>Reason</th><th>Status</th><th>Disposition</th><th></th></tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.return_id}>
                <td>{r.return_id}</td>
                <td>#{r.product_id}</td>
                <td>{r.quantity}</td>
                <td>{r.reason}</td>
                <td>{r.status}</td>
                <td>{r.disposition || "—"}</td>
                <td>
                  {r.status !== "closed" && (
                    <button className="btn secondary" onClick={() => setDisposing(r)}>Inspect</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {disposing && (
        <DispositionModal
          ret={disposing}
          onClose={() => setDisposing(null)}
          onSaved={() => { setDisposing(null); refresh(); }}
        />
      )}
    </div>
  );
}

function DispositionModal({ ret, onClose, onSaved }: any) {
  const [disposition, setDisposition] = useState<string>("restock");
  const [notes, setNotes] = useState("");
  const [credit, setCredit] = useState("");
  const toast = useToast();

  async function save() {
    await setReturnDisposition(ret.return_id, {
      disposition,
      disposition_notes: notes || undefined,
      credit_amount: credit || undefined,
    });
    toast.show("Disposition saved");
    onSaved();
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Return #{ret.return_id} — Inspect</h3>
        <label>Disposition</label>
        <select className="input" value={disposition} onChange={(e) => setDisposition(e.target.value)}>
          {DISPOSITIONS.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <label>Notes</label>
        <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <label>Credit amount (optional)</label>
        <input className="input" value={credit} onChange={(e) => setCredit(e.target.value)} placeholder="0.00" />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>Save</button>
          <button className="btn secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
