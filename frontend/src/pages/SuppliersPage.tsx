import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { SupplierDTO, createSupplier, fetchSuppliers } from "../api";
import { useAuth, useToast } from "../store";

export default function SuppliersPage() {
  const { t } = useTranslation(["suppliers", "common"]);
  const role = useAuth((s) => s.user?.role);
  const canMutate = role === "admin" || role === "manager";
  const toast = useToast();
  const [items, setItems] = useState<SupplierDTO[]>([]);
  const [creating, setCreating] = useState(false);

  async function load() { setItems(await fetchSuppliers()); }
  useEffect(() => { load(); }, []);

  return (
    <div>
      <h2>{t("title")}</h2>
      <div className="card">
        <div className="toolbar">
          <span>{t("count", { count: items.length })}</span>
          {canMutate && <button className="btn" onClick={() => setCreating(true)}>{t("newSupplier")}</button>}
        </div>
        <table>
          <thead><tr>
            <th>{t("table.name")}</th>
            <th>{t("table.email")}</th>
            <th>{t("table.phone")}</th>
            <th>{t("table.city")}</th>
            <th>{t("table.country")}</th>
            <th>{t("table.active")}</th>
          </tr></thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.supplier_id}>
                <td>{s.name}</td>
                <td>{s.contact_email || "—"}</td>
                <td>{s.contact_phone || "—"}</td>
                <td>{s.city || "—"}</td>
                <td>{s.country || "—"}</td>
                <td>{s.active ? t("labels.yes", { ns: "common" }) : t("labels.no", { ns: "common" })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {creating && (
        <SupplierModal
          onClose={() => setCreating(false)}
          onSaved={() => { setCreating(false); toast.show(t("toast.created")); load(); }}
        />
      )}
    </div>
  );
}

function SupplierModal({ onClose, onSaved }: any) {
  const { t } = useTranslation(["suppliers", "common"]);
  const [form, setForm] = useState<Partial<SupplierDTO>>({ name: "", contact_email: "", contact_phone: "" });
  function update(k: string, v: any) { setForm((f) => ({ ...f, [k]: v })); }
  async function save() {
    await createSupplier(form);
    onSaved();
  }
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{t("modal.title")}</h3>
        <label>{t("modal.name")}</label>
        <input className="input" value={form.name || ""} onChange={(e) => update("name", e.target.value)} />
        <label>{t("modal.email")}</label>
        <input className="input" value={form.contact_email || ""} onChange={(e) => update("contact_email", e.target.value)} />
        <label>{t("modal.phone")}</label>
        <input className="input" value={form.contact_phone || ""} onChange={(e) => update("contact_phone", e.target.value)} />
        <label>{t("modal.city")}</label>
        <input className="input" value={form.city || ""} onChange={(e) => update("city", e.target.value)} />
        <label>{t("modal.country")}</label>
        <input className="input" value={form.country || ""} onChange={(e) => update("country", e.target.value)} />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>{t("actions.create", { ns: "common" })}</button>
          <button className="btn secondary" onClick={onClose}>{t("actions.cancel", { ns: "common" })}</button>
        </div>
      </div>
    </div>
  );
}
