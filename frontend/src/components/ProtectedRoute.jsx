import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Envuelve rutas privadas: si no hay sesión, redirige a /login.
export function ProtectedRoute({ children }) {
  const { isAuth } = useAuth();
  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
