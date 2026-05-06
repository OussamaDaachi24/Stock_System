import { useEffect, useState } from "react";
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

export default function AdminPage() {
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
    toast.show("Backup created");
    load();
  }

  async function doRestore(id: string) {
    if (!confirm(`Restore backup ${id}? This will overwrite current data.`)) return;
    await restoreBackup(id);
    toast.show("Restore complete");
    load();
  }

  return (
    <div>
      <h2>Admin</h2>

      <div className="card" style={{ marginBottom: 12 }}>
        <h3>System status</h3>
        {health && (
          <div style={{ display: "flex", gap: 24, fontSize: 14 }}>
            <span>Service: <strong>{health.status}</strong></span>
            <span>DB: <strong>{health.db}</strong></span>
            <span>Cache: <strong>{health.redis}</strong></span>
          </div>
        )}
        {metrics && (
          <div style={{ marginTop: 8, fontSize: 13, color: "#4b5563" }}>
            {metrics.products} products · {metrics.ledger_entries} ledger entries ·{" "}
            {metrics.active_reservations} active reservations · {metrics.low_stock} low-stock
          </div>
        )}
      </div>

      <div className="card" style={{ marginBottom: 12 }}>
        <div className="toolbar">
          <h3>Users</h3>
          <button className="btn" onClick={() => setShowUser(true)}>+ New user</button>
        </div>
        <table>
          <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Status</th></tr></thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.user_id}>
                <td>{u.email}</td><td>{u.name}</td><td>{u.role}</td><td>{u.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3>Backups</h3>
          <button className="btn" onClick={doBackup}>Trigger backup</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>Status</th><th>Size</th><th>Created</th><th></th></tr></thead>
          <tbody>
            {backups.map((b) => (
              <tr key={b.backup_id}>
                <td><code>{b.backup_id.slice(0, 8)}…</code></td>
                <td>{b.status}</td>
                <td>{b.size_bytes ? `${Math.round(b.size_bytes / 1024)} KB` : "—"}</td>
                <td>{new Date(b.created_at).toLocaleString()}</td>
                <td>
                  {b.status === "completed" && (
                    <button className="btn danger" onClick={() => doRestore(b.backup_id)}>Restore</button>
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
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("operator");

  async function save() {
    if (password.length < 8) { toast.show("Password must be at least 8 chars", "error"); return; }
    await createUser({ email, name, password, role });
    toast.show("User created");
    onSaved();
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Create user</h3>
        <label>Email</label>
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>Name</label>
        <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
        <label>Password</label>
        <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <label>Role</label>
        <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="operator">operator</option>
          <option value="manager">manager</option>
          <option value="admin">admin</option>
          <option value="viewer">viewer</option>
        </select>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button className="btn" onClick={save}>Create</button>
          <button className="btn secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
