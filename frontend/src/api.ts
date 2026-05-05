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
