import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL;
const TOKEN_KEY = "auth_token";

// login: pide el token al backend y lo guarda en localStorage.
// Usamos axios directamente (no el client con interceptores) para evitar
// bucles si el login devolviese 401.
export async function login(email, password) {
  const { data } = await axios.post(`${API_URL}/auth/login`, {
    email,
    password,
  });
  localStorage.setItem(TOKEN_KEY, data.token);
  return data.token;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function isAuthenticated() {
  return Boolean(getToken());
}
