import { useEffect, useState } from "react";
import {
  createPurchaseOrder,
  fetchProducts,
  fetchPurchaseOrders,
  fetchSuppliers,
} from "../api";
import { useAuth, useToast } from "../store";

interface Line { product_id: number; sku: string; quantity: number; unit_price?: string; }

export default function PurchaseOrdersPage() {
  const role = useAuth((s) => s.user?.role);
  const canMutate = role === "admin" || role === "manager";
  const [items, setItems] = useState<any[]>([]);
  const [creating, setCreating] = useState(false);

  async function load() { setItems((await fetchPurchaseOrders()) || []); }
  useEffect(() => { load(); }, []);

  return (
    <div>
      <h2>Purchase Orders</h2>
      <div className="card">
        <div className="toolbar">
          <span>{items.length} POs</span>
          {canMutate && <button className="btn" onClick={() => setCreating(true)}>+ New PO</button>}
        </div>
        <table>
          <thead><tr><th>PO #</th><th>Supplier</th><th>Status</th><th>Lines</th><th>Created</th></tr></thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.po_id}>
                <td>{p.po_number}</td>
                <td>#{p.supplier_id}</td>
                <td>{p.status}</td>
                <td>{p.lines?.length ?? 0}</td>
                <td>{new Date(p.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {creating && (
        <CreatePOModal onClose={() => setCreating(false)} onSaved={() => { setCreating(false); load(); }} />
      )}
    </div>
  );
}

function CreatePOModal({ onClose, onSaved }: any) {
  const toast = useToast();
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [supplierId, setSupplierId] = useState<number | "">("");
  const [poNumber, setPoNumber] = useState("");
  const [search, setSearch] = useState("");
  const [lines, setLines] = useState<Line[]>([]);

  useEffect(() => { fetchSuppliers().then(setSuppliers); }, []);

  async function addProduct() {
    if (!search.trim()) return;
    const data = await fetchProducts({ search, limit: 1, offset: 0 });
    if (!data.items.length) { toast.show("Product not found", "error"); return; }
    const p = data.items[0];
    setLines((prev) => [...prev, { product_id: p.product_id, sku: p.sku, quantity: 1 }]);
    setSearch("");
  }

  async function save() {
    if (!supplierId || !poNumber.trim() || lines.length === 0) {
      toast.show("Supplier, PO number, and at least one line required", "error");
      return;
    }
    await createPurchaseOrder({
      supplier_id: Number(supplierId),
      po_number: poNumber.trim(),
      lines: lines.map((l) => ({
        product_id: l.product_id,
        quantity: l.quantity,
        unit_price: l.unit_price || undefined,
      })),
    });
    toast.show("PO created");
    onSaved();
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 640 }}>
        <h3>Create purchase order</h3>
        <div className="row">
          <div>
            <label>Supplier</label>
            <select className="input" value={supplierId} onChange={(e) => setSupplierId(Number(e.target.value))}>
              <option value="">— select —</option>
              {suppliers.map((s) => <option key={s.supplier_id} value={s.supplier_id}>{s.name}</option>)}
            </select>
          </div>
          <div>
            <label>PO #</label>
            <input className="input" value={poNumber} onChange={(e) => setPoNumber(e.target.value)} />
          </div>
        </div>

        <label>Add product</label>
        <div style={{ display: "flex", gap: 8 }}>
          <input className="input" placeholder="Search SKU/name" value={search} onChange={(e) => setSearch(e.target.value)} />
          <button className="btn secondary" onClick={addProduct}>Add</button>
        </div>

        <table style={{ marginTop: 12 }}>
          <thead><tr><th>SKU</th><th>Qty</th><th>Unit price</th><th></th></tr></thead>
          <tbody>
            {lines.map((l, i) => (
              <tr key={i}>
                <td>{l.sku}</td>
                <td>
                  <input className="input" type="number" min={1} value={l.quantity} style={{ width: 80 }}
                    onChange={(e) => setLines((p) => p.map((x, j) => j === i ? { ...x, quantity: Math.max(1, Number(e.target.value)) } : x))} />
                </td>
                <td>
                  <input className="input" value={l.unit_price || ""} placeholder="0.00"
                    onChange={(e) => setLines((p) => p.map((x, j) => j === i ? { ...x, unit_price: e.target.value } : x))} />
                </td>
                <td><button className="btn danger" onClick={() => setLines((p) => p.filter((_, j) => j !== i))}>Remove</button></td>
              </tr>
            ))}
          </tbody>
        </table>

        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>Create</button>
          <button className="btn secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
