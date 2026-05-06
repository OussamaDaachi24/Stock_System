import { Navigate, Route, Routes, Link, useNavigate } from "react-router-dom";
import { useAuth, useToast } from "./store";
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
  if (!user) return <Navigate to="/login" replace />;
  const isAdmin = user.role === "admin";
  return (
    <>
      <nav className="nav">
        <strong>Stock System</strong>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/products">Products</Link>
        <Link to="/receiving">Receiving</Link>
        <Link to="/returns">Returns</Link>
        <Link to="/reservations">Reservations</Link>
        <Link to="/suppliers">Suppliers</Link>
        <Link to="/purchase-orders">POs</Link>
        <Link to="/reports">Reports</Link>
        {isAdmin && <Link to="/admin">Admin</Link>}
        <span className="spacer" />
        <span>{user.name} ({user.role})</span>
        <button
          className="btn secondary"
          onClick={() => { clear(); navigate("/login"); }}
        >
          Logout
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
