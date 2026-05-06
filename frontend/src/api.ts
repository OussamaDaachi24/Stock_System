import axios, { AxiosError, AxiosRequestConfig } from "axios";
import { v4 as uuidv4 } from "uuid";
import { useAuth, useToast } from "./store";

export const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = useAuth.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  if ((config.method || "get").toLowerCase() === "post" && !config.headers["Idempotency-Key"]) {
    config.headers["Idempotency-Key"] = uuidv4();
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err: AxiosError<any>) => {
    if (err.response?.status === 401) {
      useAuth.getState().clear();
    }
    const msg =
      err.response?.data?.error?.message ||
      err.response?.data?.detail ||
      err.message ||
      "Request failed";
    useToast.getState().show(String(msg), "error");
    return Promise.reject(err);
  }
);

export interface ProductDTO {
  product_id: number;
  sku: string;
  name: string;
  barcode?: string | null;
  unit_of_measure: string;
  category?: string | null;
  cost_price?: string | null;
  sell_price?: string | null;
  reorder_threshold?: number | null;
  supplier_id?: number | null;
  location?: string | null;
  attributes?: Record<string, unknown> | null;
}

export interface ProductListResponse {
  items: ProductDTO[];
  total: number;
  limit: number;
  offset: number;
}

export async function login(email: string, password: string) {
  const r = await api.post("/api/v1/auth/login", { email, password });
  return r.data.data;
}

export async function fetchProducts(params: {
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<ProductListResponse> {
  const r = await api.get("/api/v1/products", { params });
  return r.data.data;
}

export async function createProduct(payload: Partial<ProductDTO>): Promise<ProductDTO> {
  const r = await api.post("/api/v1/products", payload);
  return r.data.data;
}

export async function updateProduct(
  id: number,
  payload: Partial<ProductDTO>
): Promise<ProductDTO> {
  const r = await api.put(`/api/v1/products/${id}`, payload);
  return r.data.data;
}

// --- Inventory ---
export interface SnapshotDTO {
  snapshot_id: number;
  product_id: number;
  on_hand: number;
  reserved: number;
  available: number;
}

export async function fetchSnapshots(): Promise<SnapshotDTO[]> {
  const r = await api.get("/api/v1/inventory/snapshot");
  return r.data.data;
}

export async function fetchSnapshot(productId: number): Promise<SnapshotDTO> {
  const r = await api.get(`/api/v1/inventory/snapshot`, { params: { product_id: productId } });
  return r.data.data;
}

export async function createAdjustment(payload: {
  product_id: number;
  quantity_delta: number;
  reason: string;
  allow_negative?: boolean;
}) {
  const r = await api.post("/api/v1/inventory/adjustments", payload);
  return r.data.data;
}

export async function fetchLedger(params: {
  product_id?: number;
  type?: string;
  limit?: number;
  offset?: number;
}) {
  const r = await api.get("/api/v1/inventory/ledger", { params });
  return r.data.data;
}

export async function fetchLowStock() {
  const r = await api.get("/api/v1/inventory/low-stock");
  return r.data.data as Array<{
    product_id: number;
    sku: string;
    name: string;
    on_hand: number;
    reorder_threshold: number;
  }>;
}

// --- Suppliers ---
export interface SupplierDTO {
  supplier_id: number;
  name: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  city?: string | null;
  country?: string | null;
  active: number;
}

export async function fetchSuppliers(): Promise<SupplierDTO[]> {
  const r = await api.get("/api/v1/suppliers");
  return r.data.data?.items ?? r.data.data ?? [];
}

export async function createSupplier(payload: Partial<SupplierDTO>) {
  const r = await api.post("/api/v1/suppliers", payload);
  return r.data.data;
}

// --- Purchase Orders ---
export interface POLineDTO {
  po_line_id?: number;
  product_id: number;
  quantity: number;
  received_quantity?: number;
  unit_price?: string | null;
}

export interface PurchaseOrderDTO {
  po_id: number;
  supplier_id: number;
  po_number: string;
  status: string;
  expected_delivery_date?: string | null;
  notes?: string | null;
  created_at: string;
  lines: POLineDTO[];
}

export async function fetchPurchaseOrders(params: { status?: string } = {}) {
  const r = await api.get("/api/v1/purchase-orders", { params });
  return r.data.data?.items ?? r.data.data;
}

export async function getPurchaseOrder(poId: number): Promise<PurchaseOrderDTO> {
  const r = await api.get(`/api/v1/purchase-orders/${poId}`);
  return r.data.data;
}

export async function createPurchaseOrder(payload: {
  supplier_id: number;
  po_number: string;
  expected_delivery_date?: string;
  notes?: string;
  lines: { product_id: number; quantity: number; unit_price?: string }[];
}) {
  const r = await api.post("/api/v1/purchase-orders", payload);
  return r.data.data;
}

// --- Receipts ---
export interface ReceiptDTO {
  receipt_id: number;
  po_id?: number | null;
  supplier_id?: number | null;
  status: string;
  discrepancies?: any[] | null;
  created_at: string;
  completed_at?: string | null;
  lines: any[];
}

export async function createReceipt(payload: {
  po_id?: number;
  supplier_id?: number;
  lines: { product_id: number; quantity: number; lot_batch?: string; location?: string }[];
}) {
  const r = await api.post("/api/v1/receipts", payload);
  return r.data.data;
}

export async function fetchReceipts(params: { po_id?: number; status?: string } = {}) {
  const r = await api.get("/api/v1/receipts", { params });
  return r.data.data?.items ?? r.data.data;
}

export async function completeReceipt(receiptId: number) {
  const r = await api.post(`/api/v1/receipts/${receiptId}/complete`);
  return r.data.data;
}

// --- Returns ---
export async function fetchReturns(params: { status?: string } = {}) {
  const r = await api.get("/api/v1/returns", { params });
  return r.data.data?.items ?? r.data.data;
}

export async function createReturn(payload: {
  product_id: number;
  quantity: number;
  reason: string;
  reference?: string;
  receiving_notes?: string;
}) {
  const r = await api.post("/api/v1/returns", payload);
  return r.data.data;
}

export async function setReturnDisposition(
  returnId: number,
  payload: { disposition: string; disposition_notes?: string; credit_amount?: string }
) {
  const r = await api.patch(`/api/v1/returns/${returnId}/disposition`, payload);
  return r.data.data;
}

// --- Reservations ---
export async function fetchReservations(params: { status?: string; expiry_soon?: boolean } = {}) {
  const r = await api.get("/api/v1/reservations", { params });
  return r.data.data?.items ?? r.data.data;
}

export async function createReservation(payload: {
  product_id: number;
  quantity: number;
  reference?: string;
  expiry_days?: number;
}) {
  const r = await api.post("/api/v1/reservations", payload);
  return r.data.data;
}

export async function releaseReservation(reservationId: number) {
  const r = await api.delete(`/api/v1/reservations/${reservationId}`);
  return r.data.data;
}

// --- Reports ---
export async function createInventoryExport(payload: {
  format: "csv" | "json";
  category?: string;
  supplier_id?: number;
}) {
  const r = await api.post("/api/v1/reports/inventory-export", payload);
  return r.data.data;
}

export async function getExportJob(jobId: string) {
  const r = await api.get(`/api/v1/reports/inventory-export/${jobId}`);
  return r.data.data;
}

export function exportDownloadUrl(jobId: string) {
  return `${API_BASE}/api/v1/reports/inventory-export/${jobId}/download`;
}

// --- Admin ---
export async function fetchUsers() {
  const r = await api.get("/api/v1/admin/users");
  return r.data.data as Array<{
    user_id: number;
    email: string;
    name: string;
    role: string;
    status: string;
  }>;
}

export async function createUser(payload: {
  email: string;
  name: string;
  password: string;
  role: string;
}) {
  const r = await api.post("/api/v1/admin/users", payload);
  return r.data.data;
}

export async function fetchBackups() {
  const r = await api.get("/api/v1/admin/backups");
  return r.data.data as Array<{
    backup_id: string;
    status: string;
    size_bytes?: number | null;
    created_at: string;
  }>;
}

export async function triggerBackup(notes?: string) {
  const r = await api.post("/api/v1/admin/backups", null, { params: notes ? { notes } : {} });
  return r.data.data;
}

export async function restoreBackup(backupId: string) {
  const r = await api.post("/api/v1/admin/restore", { backup_id: backupId, verify: true });
  return r.data.data;
}

export async function fetchMetrics() {
  const r = await api.get("/api/v1/metrics");
  return r.data.data;
}

export async function fetchHealth() {
  const r = await api.get("/api/v1/health/full");
  return r.data.data;
}

