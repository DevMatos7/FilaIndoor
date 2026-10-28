import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = String(error?.config?.url || "");
    const isLogin = url.includes("/auth/login");
    if (status === 401 && !isLogin) {
      localStorage.removeItem("token");
      if (!window.location.pathname.startsWith("/login")) {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.assign(`/login?expired=1&next=${next}`);
      }
    }
    return Promise.reject(error);
  },
);

export default api;

export type QueueSummary = {
  id: string;
  department_id: string;
  name: string;
  status: string;
  priority_strategy: string;
  normal_prefix: string;
  priority_prefix: string;
};

export type Ticket = {
  id: string;
  number: string;
  type: string;
  status: string;
  issued_at?: string | null;
  called_at?: string | null;
  service_started_at?: string | null;
  completed_at?: string | null;
  events?: Array<{
    id: string;
    event_type: string;
    event_at: string;
  }>;
};

export type QueueStatus = {
  queue_id: string;
  name: string;
  status: string;
  waiting_count: number;
  priority_waiting: number;
  estimated_wait_seconds: number;
  current: Ticket | null;
  last_called: Ticket[];
  priority_rule: {
    normal_weight: number;
    priority_weight: number;
    priority_max_wait_seconds: number;
  };
};
