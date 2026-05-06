import { useEffect, useRef, useState } from "react";
import { createInventoryExport, exportDownloadUrl, getExportJob } from "../api";
import { useAuth, useToast } from "../store";

export default function ReportsPage() {
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
    if (!r.ok) { toast.show("Download failed", "error"); return; }
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
      <h2>Reports</h2>
      <div className="card">
        <h3>Inventory export</h3>
        <div className="row">
          <div>
            <label>Format</label>
            <select className="input" value={format} onChange={(e) => setFormat(e.target.value as any)}>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
          </div>
          <div>
            <label>Category (optional)</label>
            <input className="input" value={category} onChange={(e) => setCategory(e.target.value)} />
          </div>
        </div>
        <label>Supplier ID (optional)</label>
        <input className="input" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} />
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button className="btn" disabled={polling} onClick={start}>Generate</button>
          {job && job.status === "completed" && (
            <button className="btn secondary" onClick={download}>Download</button>
          )}
        </div>
        {job && (
          <div style={{ marginTop: 12, fontSize: 13 }}>
            Job <code>{job.job_id}</code> — status: <strong>{job.status}</strong>
            {job.expires_at && <span> · expires {new Date(job.expires_at).toLocaleString()}</span>}
            {job.error && <div className="error-text">{job.error}</div>}
          </div>
        )}
      </div>
    </div>
  );
}
