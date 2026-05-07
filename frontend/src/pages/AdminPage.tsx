import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  createUser,
  fetchBackups,
  fetchHealth,
  fetchMetrics,
  fetchUsers,
  restoreBackup,
  triggerBackup,
} from "../api";
import { useToast } from "../store";
import { formatBytes, formatDateTime, formatNumber } from "../i18n/format";

export default function AdminPage() {
  const { t } = useTranslation(["admin", "common", "enums"]);
  const toast = useToast();
  const [users, setUsers] = useState<any[]>([]);
  const [backups, setBackups] = useState<any[]>([]);
  const [health, setHealth] = useState<any | null>(null);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [showUser, setShowUser] = useState(false);

  async function load() {
    try {
      const [u, b, h, m] = await Promise.all([
        fetchUsers().catch(() => []),
        fetchBackups().catch(() => []),
        fetchHealth().catch(() => null),
        fetchMetrics().catch(() => null),
      ]);
      setUsers(u); setBackups(b); setHealth(h); setMetrics(m);
    } catch {}
  }
  useEffect(() => { load(); }, []);

  async function doBackup() {
    await triggerBackup("manual");
    toast.show(t("toast.backupCreated"));
    load();
  }

  async function doRestore(id: string) {
    if (!confirm(t("toast.confirmRestore", { id }))) return;
    await restoreBackup(id);
    toast.show(t("toast.restoreComplete"));
    load();
  }

  return (
    <div>
      <h2>{t("title")}</h2>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>{t("systemStatus")}</h3>
        {health && (
          <div style={{ display: "flex", gap: 24, fontSize: 14 }}>
            <span>{t("service")}: <strong>{health.status}</strong></span>
            <span>{t("db")}: <strong>{health.db}</strong></span>
            <span>{t("cache")}: <strong>{health.redis}</strong></span>
          </div>
        )}
        {metrics && (
          <div style={{ marginTop: 8, fontSize: 13, color: "var(--c-text-2)" }}>
            {t("metricsLine", {
              products: formatNumber(metrics.products, { maximumFractionDigits: 0 }),
              ledger: formatNumber(metrics.ledger_entries, { maximumFractionDigits: 0 }),
              reservations: formatNumber(metrics.active_reservations, { maximumFractionDigits: 0 }),
              lowStock: formatNumber(metrics.low_stock, { maximumFractionDigits: 0 }),
            })}
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <div className="toolbar">
          <h3>{t("users")}</h3>
          <button className="btn" onClick={() => setShowUser(true)}>{t("newUser")}</button>
        </div>
        <table>
          <thead><tr>
            <th>{t("table.email")}</th>
            <th>{t("table.name")}</th>
            <th>{t("table.role")}</th>
            <th>{t("table.status")}</th>
          </tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td>{u.email}</td>
                <td>{u.name}</td>
                <td>{t(`role.${u.role}`, { ns: "enums", defaultValue: u.role })}</td>
                <td>{t(`status.${u.status}`, { ns: "enums", defaultValue: u.status })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3>{t("backups")}</h3>
          <button className="btn" onClick={doBackup}>{t("triggerBackup")}</button>
        </div>
        <table>
          <thead><tr>
            <th>{t("table.id")}</th>
            <th>{t("table.status", { defaultValue: t("table.status") })}</th>
            <th>{t("table.size")}</th>
            <th>{t("table.created")}</th>
            <th></th>
          </tr></thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.backup_id}>
                <td><code>{b.backup_id.slice(0, 8)}…</code></td>
                <td>{t(`status.${b.status}`, { ns: "enums", defaultValue: b.status })}</td>
                <td>{formatBytes(b.size_bytes)}</td>
                <td>{formatDateTime(b.created_at)}</td>
                <td>
                  {b.status === "completed" && (
                    <button className="btn danger" onClick={() => doRestore(b.backup_id)}>{t("actions.restore", { ns: "common" })}</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showUser && (
        <UserModal onClose={() => setShowUser(false)} onSaved={() => { setShowUser(false); load(); }} />
      )}
    </div>
  );
}

function UserModal({ onClose, onSaved }: any) {
  const { t } = useTranslation(["admin", "common", "enums"]);
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("operator");

  async function save() {
    if (password.length < 8) { toast.show(t("toast.passwordTooShort"), "error"); return; }
    await createUser({ email, name, password, role });
    toast.show(t("toast.userCreated"));
    onSaved();
  }

  const roles = ["operator", "manager", "admin", "viewer"];

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{t("modal.title")}</h3>
        <label>{t("modal.email")}</label>
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>{t("modal.name")}</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        <label>{t("modal.password")}</label>
        <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <label>{t("modal.role")}</label>
        <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
          {roles.map((r) => <option key={r} value={r}>{t(`role.${r}`, { ns: "enums" })}</option>)}
        </select>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>{t("actions.create", { ns: "common" })}</button>
          <button className="btn secondary" onClick={onClose}>{t("actions.cancel", { ns: "common" })}</button>
        </div>
      </div>
    </div>
  );
}
