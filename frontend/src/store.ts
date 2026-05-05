import { create } from "zustand";

export interface User {
  user_id: number;
  email: string;
  name: string;
  role: "operator" | "manager" | "admin" | "viewer";
  status: string;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setSession: (s: { accessToken: string; refreshToken: string; user: User }) => void;
  clear: () => void;
}

const STORAGE_KEY = "stock_session_v1";

function loadInitial() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

const initial = loadInitial();

export const useAuth = create<AuthState>((set) => ({
  accessToken: initial?.accessToken ?? null,
  refreshToken: initial?.refreshToken ?? null,
  user: initial?.user ?? null,
  setSession: ({ accessToken, refreshToken, user }) => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ accessToken, refreshToken, user }));
    set({ accessToken, refreshToken, user });
  },
  clear: () => {
    sessionStorage.removeItem(STORAGE_KEY);
    set({ accessToken: null, refreshToken: null, user: null });
  },
}));

interface ToastState {
  message: string | null;
  kind: "info" | "error";
  show: (m: string, k?: "info" | "error") => void;
  hide: () => void;
}

export const useToast = create<ToastState>((set) => ({
  message: null,
  kind: "info",
  show: (message, kind = "info") => {
    set({ message, kind });
    setTimeout(() => set({ message: null }), 3500);
  },
  hide: () => set({ message: null }),
}));
