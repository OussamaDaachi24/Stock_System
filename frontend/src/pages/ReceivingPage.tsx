import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ProductDTO,
  completeReceipt,
  createReceipt,
  fetchProducts,
  fetchReceipts,
} from "../api";
import { useToast } from "../store";
import { formatDateTime, formatNumber } from "../i18n/format";

interface Line {
  product_id: number;
  sku: string;
  name: string;
  quantity: number;
  lot_batch?: string;
  location?: string;
}

export default function ReceivingPage() {
  const { t } = useTranslation(["receiving", "common", "enums"]);
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
      toast.show(t("toast.productNotFound", { value: scan }), "error");
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
      toast.show(t("toast.addAtLeastOneLine"), "error");
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
      toast.show(
        thenComplete
          ? t("toast.createdAndCompleted", { id: r.receipt_id })
          : t("toast.created", { id: r.receipt_id })
      );
      if (r.discrepancies?.length) {
        toast.show(t("toast.discrepanciesFlagged", { count: r.discrepancies.length }), "error");
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
      <h2>{t("title")}</h2>
      <div className="card" style={{ marginBottom: 12 }}>
        <div className="row">
          <div>
            <label>{t("poId")}</label>
            <input className="input" value={poId} onChange={(e) => setPoId(e.target.value)} placeholder={t("poIdPlaceholder")} />
          </div>
          <div>
            <label>{t("scan")}</label>
            <form onSubmit={onScan} style={{ display: "flex", gap: 8 }}>
              <input
                className="input"
                value={scan}
                onChange={(e) => setScan(e.target.value)}
                placeholder={t("scanPlaceholder")}
                autoFocus
              />
              <button className="btn" type="submit">{t("actions.add", { ns: "common" })}</button>
            </form>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>{t("linesTitle")}</h3>
        <table>
          <thead>
            <tr>
              <th>{t("table.sku")}</th>
              <th>{t("table.name")}</th>
              <th>{t("table.qty")}</th>
              <th>{t("table.lotBatch")}</th>
              <th>{t("table.location")}</th>
              <th></th>
            </tr>
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
                <td><button className="btn danger" onClick={() => removeLine(i)}>{t("actions.remove", { ns: "common" })}</button></td>
              </tr>
            ))}
            {lines.length === 0 && (
              <tr><td colSpan={6} className="empty">
                {t("emptyLines")}
              </td></tr>
            )}
          </tbody>
        </table>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn secondary" disabled={submitting} onClick={() => submit(false)}>
            {t("saveReceipt")}
          </button>
          <button className="btn" disabled={submitting} onClick={() => submit(true)}>
            {t("saveAndComplete")}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>{t("recentTitle")}</h3>
        <table>
          <thead><tr>
            <th>{t("table.id")}</th>
            <th>{t("table.po")}</th>
            <th>{t("table.status")}</th>
            <th>{t("table.discrepancies")}</th>
            <th>{t("table.created")}</th>
          </tr></thead>
          <tbody>
            {recent.slice(0, 10).map((r: any) => (
              <tr key={r.receipt_id}>
                <td>{r.receipt_id}</td>
                <td>{r.po_id ?? "—"}</td>
                <td>{t(`status.${r.status}`, { ns: "enums", defaultValue: r.status })}</td>
                <td>{formatNumber(r.discrepancies?.length || 0, { maximumFractionDigits: 0 })}</td>
                <td>{formatDateTime(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
