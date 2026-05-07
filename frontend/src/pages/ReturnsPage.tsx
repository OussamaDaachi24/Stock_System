import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { createReturn, fetchProducts, fetchReturns, setReturnDisposition } from "../api";
import { useToast } from "../store";

const REASONS = ["defective", "wrong_item", "customer_request", "expired", "other"] as const;
const DISPOSITIONS = ["restock", "scrap", "repair"] as const;

export default function ReturnsPage() {
  const { t } = useTranslation(["returns", "common", "enums"]);
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
      toast.show(t("toast.lookupFirst"), "error");
      return;
    }
    setProductId(data.items[0].product_id);
    setProductSku(data.items[0].sku);
  }

  async function submit() {
    if (!productId) {
      toast.show(t("toast.lookupFirst"), "error");
      return;
    }
    await createReturn({
      product_id: productId,
      quantity,
      reason,
      reference: reference || undefined,
      receiving_notes: notes || undefined,
    });
    toast.show(t("toast.created"));
    setProductId(null); setProductSku(""); setQuantity(1); setReason("defective");
    setReference(""); setNotes(""); setSearch("");
    refresh();
  }

  return (
    <div>
      <h2>{t("title")}</h2>
      <div className="card" style={{ marginBottom: 12 }}>
        <h3>{t("createTitle")}</h3>
        <div className="row">
          <div>
            <label>{t("fields.product")}</label>
            <div style={{ display: "flex", gap: 8 }}>
              <input className="input" value={search} onChange={(e) => setSearch(e.target.value)} />
              <button className="btn secondary" onClick={lookup}>{t("actions.find", { ns: "common" })}</button>
            </div>
            {productSku && <div style={{ fontSize: 12, color: "var(--c-success)", marginTop: 4 }}>{t("selected", { sku: productSku })}</div>}
          </div>
          <div>
            <label>{t("fields.quantity")}</label>
            <input className="input" type="number" min={1} value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))} />
          </div>
        </div>
        <div className="row">
          <div>
            <label>{t("fields.reason")}</label>
            <select className="input" value={reason} onChange={(e) => setReason(e.target.value)}>
              {REASONS.map((r) => <option key={r} value={r}>{t(`returnReason.${r}`, { ns: "enums" })}</option>)}
            </select>
          </div>
          <div>
            <label>{t("fields.reference")}</label>
            <input className="input" value={reference} onChange={(e) => setReference(e.target.value)} />
          </div>
        </div>
        <label>{t("fields.notes")}</label>
        <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <div style={{ marginTop: 12 }}>
          <button className="btn" onClick={submit}>{t("submit")}</button>
        </div>
      </div>

      <div className="card">
        <h3>{t("queueTitle")}</h3>
        <table>
          <thead><tr>
            <th>{t("table.id")}</th>
            <th>{t("table.product")}</th>
            <th>{t("table.qty")}</th>
            <th>{t("table.reason")}</th>
            <th>{t("table.status")}</th>
            <th>{t("table.disposition")}</th>
            <th></th>
          </tr></thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.return_id}>
                <td>{r.return_id}</td>
                <td>#{r.product_id}</td>
                <td>{r.quantity}</td>
                <td>{t(`returnReason.${r.reason}`, { ns: "enums", defaultValue: r.reason })}</td>
                <td>{t(`status.${r.status}`, { ns: "enums", defaultValue: r.status })}</td>
                <td>{r.disposition ? t(`disposition.${r.disposition}`, { ns: "enums", defaultValue: r.disposition }) : "—"}</td>
                <td>
                  {r.status !== "closed" && (
                    <button className="btn secondary" onClick={() => setDisposing(r)}>{t("actions.inspect", { ns: "common" })}</button>
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
  const { t } = useTranslation(["returns", "common", "enums"]);
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
    toast.show(t("toast.dispositionSaved"));
    onSaved();
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{t("modal.title", { id: ret.return_id })}</h3>
        <label>{t("modal.disposition")}</label>
        <select className="input" value={disposition} onChange={(e) => setDisposition(e.target.value)}>
          {DISPOSITIONS.map((d) => <option key={d} value={d}>{t(`disposition.${d}`, { ns: "enums" })}</option>)}
        </select>
        <label>{t("modal.notes")}</label>
        <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <label>{t("modal.credit")}</label>
        <input className="input" value={credit} onChange={(e) => setCredit(e.target.value)} placeholder={t("modal.creditPlaceholder")} />
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>{t("actions.save", { ns: "common" })}</button>
          <button className="btn secondary" onClick={onClose}>{t("actions.cancel", { ns: "common" })}</button>
        </div>
      </div>
    </div>
  );
}
