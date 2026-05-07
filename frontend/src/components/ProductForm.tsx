import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ProductDTO, createProduct, updateProduct } from "../api";
import { useToast } from "../store";

const UOM_OPTIONS = ["piece", "kg", "liter", "meter", "box", "pack", "unit"];

interface Props {
  mode: "create" | "edit";
  product?: ProductDTO;
  onClose: () => void;
  onSaved: () => void;
}

export default function ProductForm({ mode, product, onClose, onSaved }: Props) {
  const { t } = useTranslation(["products", "common", "enums"]);
  const showToast = useToast((s) => s.show);
  const [form, setForm] = useState<Partial<ProductDTO>>(
    product ?? { unit_of_measure: "piece" }
  );
  const [saving, setSaving] = useState(false);

  function set<K extends keyof ProductDTO>(key: K, value: ProductDTO[K] | string) {
    setForm((f) => ({ ...f, [key]: value === "" ? null : value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      if (mode === "create") {
        await createProduct({
          sku: form.sku?.trim(),
          name: form.name?.trim(),
          barcode: form.barcode || null,
          unit_of_measure: form.unit_of_measure,
          category: form.category || null,
          cost_price: form.cost_price || null,
          sell_price: form.sell_price || null,
          reorder_threshold: form.reorder_threshold ?? null,
          location: form.location || null,
        });
        showToast(t("form.createdToast"));
      } else if (product) {
        await updateProduct(product.product_id, {
          name: form.name,
          category: form.category || null,
          cost_price: form.cost_price || null,
          sell_price: form.sell_price || null,
          reorder_threshold: form.reorder_threshold ?? null,
          location: form.location || null,
        });
        showToast(t("form.updatedToast"));
      }
      onSaved();
    } catch {
      // toast shown by interceptor
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{mode === "create" ? t("form.newTitle") : t("form.editTitle", { sku: product?.sku })}</h3>
        <form onSubmit={onSubmit}>
          <div className="row">
            <div>
              <label>{t("form.sku")}</label>
              <input
                className="input"
                value={form.sku ?? ""}
                disabled={mode === "edit"}
                onChange={(e) => set("sku", e.target.value)}
                required
              />
            </div>
            <div>
              <label>{t("form.barcode")}</label>
              <input
                className="input"
                value={form.barcode ?? ""}
                disabled={mode === "edit"}
                onChange={(e) => set("barcode", e.target.value)}
                autoFocus={mode === "create"}
              />
            </div>
          </div>
          <label>{t("form.name")}</label>
          <input
            className="input"
            value={form.name ?? ""}
            onChange={(e) => set("name", e.target.value)}
            required
          />
          <div className="row">
            <div>
              <label>{t("form.uom")}</label>
              <select
                className="input"
                value={form.unit_of_measure ?? "piece"}
                disabled={mode === "edit"}
                onChange={(e) => set("unit_of_measure", e.target.value)}
              >
                {UOM_OPTIONS.map((u) => (
                  <option key={u} value={u}>{t(`uom.${u}`, { ns: "enums" })}</option>
                ))}
              </select>
            </div>
            <div>
              <label>{t("form.category")}</label>
              <input
                className="input"
                value={form.category ?? ""}
                onChange={(e) => set("category", e.target.value)}
              />
            </div>
          </div>
          <div className="row">
            <div>
              <label>{t("form.costPrice")}</label>
              <input
                className="input"
                type="number"
                step="0.01"
                value={(form.cost_price as any) ?? ""}
                onChange={(e) => set("cost_price", e.target.value)}
              />
            </div>
            <div>
              <label>{t("form.sellPrice")}</label>
              <input
                className="input"
                type="number"
                step="0.01"
                value={(form.sell_price as any) ?? ""}
                onChange={(e) => set("sell_price", e.target.value)}
              />
            </div>
          </div>
          <div className="row">
            <div>
              <label>{t("form.reorderThreshold")}</label>
              <input
                className="input"
                type="number"
                value={form.reorder_threshold ?? ""}
                onChange={(e) =>
                  set("reorder_threshold", e.target.value === "" ? (null as any) : Number(e.target.value))
                }
              />
            </div>
            <div>
              <label>{t("form.location")}</label>
              <input
                className="input"
                value={form.location ?? ""}
                onChange={(e) => set("location", e.target.value)}
              />
            </div>
          </div>
          <div style={{ marginTop: 18, display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button type="button" className="btn secondary" onClick={onClose}>
              {t("actions.cancel", { ns: "common" })}
            </button>
            <button type="submit" className="btn" disabled={saving}>
              {saving
                ? t("actions.saving", { ns: "common" })
                : mode === "create"
                  ? t("actions.create", { ns: "common" })
                  : t("actions.save", { ns: "common" })}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
