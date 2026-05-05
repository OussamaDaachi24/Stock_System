import { Navigate, Route, Routes, Link, useNavigate } from "react-router-dom";
import { useAuth, useToast } from "./store";
import LoginPage from "./pages/LoginPage";
import ProductsPage from "./pages/ProductsPage";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { user, clear } = useAuth();
  const navigate = useNavigate();
  if (!user) return <Navigate to="/login" replace />;
  return (
    <>
      <nav className="nav">
        <strong>Stock System</strong>
        <Link to="/products">Products</Link>
        <span className="spacer" />
        <span>{user.name} ({user.role})</span>
        <button
          className="btn secondary"
          onClick={() => {
            clear();
            navigate("/login");
          }}
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

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/products"
          element={
            <ProtectedLayout>
              <ProductsPage />
            </ProtectedLayout>
          }
        />
        <Route path="*" element={<Navigate to="/products" replace />} />
      </Routes>
      <Toast />
    </>
  );
}
