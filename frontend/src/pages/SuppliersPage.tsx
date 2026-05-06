import { useEffect, useState } from "react";
import { SupplierDTO, createSupplier, fetchSuppliers } from "../api";
import { useAuth, useToast } from "../store";

export default function SuppliersPage() {
  const role = useAuth((s) => s.user?.role);
  const canMutate = role === "admin" || role === "manager";
  const toast = useToast();
  const [items, setItems] = useState<SupplierDTO[]>([]);
  const [creating, setCreating] = useState(false);

  async function load() { setItems(await fetchSuppliers()); }
  useEffect(() => { load(); }, []);

  return (
    <div>
      <h2>Suppliers</h2>
      <div className="card">
        <div className="toolbar">
          <span>{items.length} suppliers</span>
          {canMutate && <button className="btn" onClick={() => setCreating(true)}>+ New supplier</button>}
        </div>
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>City</th><th>Country</th><th>Active</th></tr></thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.supplier_id}>
                <td>{s.name}</td>
                <td>{s.contact_email || "—"}</td>
                <td>{s.contact_phone || "—"}</td>
                <td>{s.city || "—"}</td>
                <td>{s.country || "—"}</td>
                <td>{s.active ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {creating && (
        <SupplierModal
          onClose={() => setCreating(false)}
          onSaved={() => { setCreating(false); toast.show("Supplier created"); load(); }}
        />
      )}
    </div>
  );
}

function SupplierModal({ onClose, onSaved }: any) {
  const [form, setForm] = useState<Partial<SupplierDTO>>({ name: "", contact_email: "", contact_phone: "" });
  function update(k: string, v: any) { setForm((f) => ({ ...f, [k]: v })); }
  async function save() {
    await createSupplier(form);
    onSaved();
  }
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Create supplier</h3>
        <label>Name</label>
        <input className="input" value={form.name || ""} onChange={(e) => update("name", e.target.value)} />
        <label>Email</label>
        <input className="input" value={form.contact_email || ""} onChange={(e) => update("contact_email", e.target.value)} />
        <label>Phone</label>
        <input className="input" value={form.contact_phone || ""} onChange={(e) => update("contact_phone", e.target.value)} />
        <label>City</label>
        <input className="input" value={form.city || ""} onChange={(e) => update("city", e.target.value)} />
        <label>Country</label>
        <input className="input" value={form.country || ""} onChange={(e) => update("country", e.target.value)} />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>Create</button>
          <button className="btn secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
