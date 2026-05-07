import { Navigate, Route, Routes, Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth, useToast } from "./store";
import { useDirection } from "./hooks/useDirection";
import LanguageSwitcher from "./components/LanguageSwitcher";
import LoginPage from "./pages/LoginPage";
import ProductsPage from "./pages/ProductsPage";
import DashboardPage from "./pages/DashboardPage";
import ReceivingPage from "./pages/ReceivingPage";
import ReturnsPage from "./pages/ReturnsPage";
import ReservationsPage from "./pages/ReservationsPage";
import SuppliersPage from "./pages/SuppliersPage";
import PurchaseOrdersPage from "./pages/PurchaseOrdersPage";
import ReportsPage from "./pages/ReportsPage";
import AdminPage from "./pages/AdminPage";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { user, clear } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation(["nav", "common", "enums"]);
  if (!user) return <Navigate to="/login" replace />;
  const isAdmin = user.role === "admin";
  return (
    <>
      <nav className="nav">
        <strong>{t("appName", { ns: "common" })}</strong>
        <Link to="/dashboard">{t("dashboard", { ns: "nav" })}</Link>
        <Link to="/products">{t("products", { ns: "nav" })}</Link>
        <Link to="/receiving">{t("receiving", { ns: "nav" })}</Link>
        <Link to="/returns">{t("returns", { ns: "nav" })}</Link>
        <Link to="/reservations">{t("reservations", { ns: "nav" })}</Link>
        <Link to="/suppliers">{t("suppliers", { ns: "nav" })}</Link>
        <Link to="/purchase-orders">{t("purchaseOrders", { ns: "nav" })}</Link>
        <Link to="/reports">{t("reports", { ns: "nav" })}</Link>
        {isAdmin && <Link to="/admin">{t("admin", { ns: "nav" })}</Link>}
        <span className="spacer" />
        <span>
          {user.name} · <span style={{ color: "var(--c-text-faint)" }}>{t(`role.${user.role}`, { ns: "enums" })}</span>
        </span>
        <LanguageSwitcher />
        <button
          className="btn secondary"
          onClick={() => { clear(); navigate("/login"); }}
        >
          {t("actions.logout", { ns: "common" })}
        </button>
      </nav>
      <div className="container">{children}</div>
    </>
  );
}

function Toast() {
  const { message, kind } = useToast();
  if (!message) return null;
  return <div className={`toast ${kind}`}>{message}</div>;
}

function P({ el }: { el: React.ReactNode }) {
  return <ProtectedLayout>{el}</ProtectedLayout>;
}

export default function App() {
  useDirection();
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<P el={<DashboardPage />} />} />
        <Route path="/products" element={<P el={<ProductsPage />} />} />
        <Route path="/receiving" element={<P el={<ReceivingPage />} />} />
        <Route path="/returns" element={<P el={<ReturnsPage />} />} />
        <Route path="/reservations" element={<P el={<ReservationsPage />} />} />
        <Route path="/suppliers" element={<P el={<SuppliersPage />} />} />
        <Route path="/purchase-orders" element={<P el={<PurchaseOrdersPage />} />} />
        <Route path="/reports" element={<P el={<ReportsPage />} />} />
        <Route path="/admin" element={<P el={<AdminPage />} />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      <Toast />
    </>
  );
}
