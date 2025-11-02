import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";

import { authStorage } from "./utils/auth";
import LoginForm from "./components/LoginForm";
import RegisterForm from "./components/RegisterForm";
import GamePage from "./components/VoxelGrid";
import TopBar from "./components/TopBar";
import { WebSocketProvider } from "./context/WebSocketProvider";

// ---------------------- AUTH PAGE ----------------------
function AuthPage() {
  const navigate = useNavigate();
  const location = useLocation();

  if (authStorage.isAuthenticated()) return <Navigate to="/" replace />;

  const initialTab: "login" | "register" =
    location.pathname.startsWith("/register") ? "register" : "login";

  const [tab, setTab] = useState<"login" | "register">(initialTab);

  useEffect(() => {
    setTab(initialTab);
  }, [initialTab]);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-6">Welcome</h1>

      <div className="flex gap-2 mb-6">
        <button
          className={`px-3 py-1.5 rounded ${
            tab === "login" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => {
            setTab("login");
            navigate("/login", { replace: true });
          }}
        >
          Sign In
        </button>

        <button
          className={`px-3 py-1.5 rounded ${
            tab === "register" ? "bg-blue-600 text-white" : "bg-gray-200"
          }`}
          onClick={() => {
            setTab("register");
            navigate("/register", { replace: true });
          }}
        >
          Create Account
        </button>
      </div>

      {tab === "login" ? (
        <LoginForm
          onDone={(user, token) => {
            localStorage.setItem("token", token);
            localStorage.setItem("user", user);
            navigate("/"); // ✅ now go to "/" instead of "/game"
          }}
        />
      ) : (
        <RegisterForm
          onDone={(user, token) => {
            localStorage.setItem("token", token);
            localStorage.setItem("user", user);
            navigate("/"); // ✅ now go to "/"
          }}
        />
      )}
    </div>
  );
}

// ---------------------- PRIVATE ROUTE ----------------------
function PrivateRoute({ children }: { children: JSX.Element }) {
  const isAuthed = authStorage.isAuthenticated();
  return isAuthed ? children : <Navigate to="/login" replace />;
}

// ---------------------- MAIN APP ----------------------
export default function App() {
  const isAuthed = authStorage.isAuthenticated();

  return (
    <BrowserRouter>
      <TopBar />
      <Routes>
        {/* ✅ Root "/" is now the game page if logged in */}
        <Route
          path="/"
          element={
            isAuthed ? (
              <PrivateRoute>
                <WebSocketProvider>
                  <GamePage />
                </WebSocketProvider>
              </PrivateRoute>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        <Route path="/login" element={<AuthPage />} />
        <Route path="/register" element={<AuthPage />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
