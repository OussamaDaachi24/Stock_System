import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { createInventoryExport, exportDownloadUrl, getExportJob } from "../api";
import { useAuth, useToast } from "../store";
import { formatDateTime } from "../i18n/format";

export default function ReportsPage() {
  const { t } = useTranslation(["reports", "common", "enums"]);
  const toast = useToast();
  const token = useAuth((s) => s.accessToken);
  const [format, setFormat] = useState<"csv" | "json">("csv");
  const [category, setCategory] = useState("");
  const [supplierId, setSupplierId] = useState("");
  const [job, setJob] = useState<any | null>(null);
  const [polling, setPolling] = useState(false);
  const pollRef = useRef<number | null>(null);

  useEffect(() => () => { if (pollRef.current) window.clearTimeout(pollRef.current); }, []);

  async function start() {
    setJob(null); setPolling(true);
    const j = await createInventoryExport({
      format,
      category: category || undefined,
      supplier_id: supplierId ? Number(supplierId) : undefined,
    });
    setJob(j);
    if (j.status !== "completed" && j.status !== "failed") {
      poll(j.job_id);
    } else {
      setPolling(false);
    }
  }

  function poll(jobId: string) {
    pollRef.current = window.setTimeout(async () => {
      try {
        const j = await getExportJob(jobId);
        setJob(j);
        if (j.status === "completed" || j.status === "failed") {
          setPolling(false);
        } else {
          poll(jobId);
        }
      } catch {
        setPolling(false);
      }
    }, 1500);
  }

  async function download() {
    if (!job) return;
    const r = await fetch(exportDownloadUrl(job.job_id), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) { toast.show(t("toast.downloadFailed"), "error"); return; }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `inventory_${job.job_id}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <h2>{t("title")}</h2>
      <div className="card">
        <h3>{t("exportTitle")}</h3>
        <div className="row">
          <div>
            <label>{t("fields.format")}</label>
            <select className="input" value={format} onChange={(e) => setFormat(e.target.value as any)}>
              <option value="csv">{t("format.csv", { ns: "enums" })}</option>
              <option value="json">{t("format.json", { ns: "enums" })}</option>
            </select>
          </div>
          <div>
            <label>{t("fields.category")}</label>
            <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
        </div>
        <label>{t("fields.supplierId")}</label>
        <input className="input" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} />
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button className="btn" disabled={polling} onClick={start}>{t("generate")}</button>
          {job && job.status === "completed" && (
            <button className="btn secondary" onClick={download}>{t("download")}</button>
          )}
        </div>
        {job && (
          <div style={{ marginTop: 12, fontSize: 13 }}>
            {t("jobInfo")} <code>{job.job_id}</code> — {t("status")}:{" "}
            <strong>{t(`status.${job.status}`, { ns: "enums", defaultValue: job.status })}</strong>
            {job.expires_at && <span> · {t("expires", { date: formatDateTime(job.expires_at) })}</span>}
            {job.error && <div className="error-text">{job.error}</div>}
          </div>
        )}
      </div>
    </div>
  );
}
