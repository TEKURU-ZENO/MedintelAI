import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      // Clear all V2 auth state on token expiry
      localStorage.removeItem("token");
      localStorage.removeItem("user_profile");
      localStorage.removeItem("ui_config");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);
