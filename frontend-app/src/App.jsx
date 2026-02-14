import { Alert, Container, Stack } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";

import { createApiClient } from "./api/client";
import { DashboardContent } from "./components/DashboardContent";
import { SimpleLogin } from "./components/SimpleLogin";

const SESSION_STORAGE_KEY = "spearhead.session.v1";

const BATTALION_ALIASES = new Set(["battalion", "גדוד", "גדוד75", "romach", "romach75"]);
const AUTH_ERROR_MESSAGES = {
  palsam_disabled: "מצב פלס״ם עדיין חסום להתחברות (ייפתח בהמשך).",
  missing_oauth_code: "לא התקבל קוד OAuth בתהליך ההתחברות. נסה שוב.",
};

const readStoredSession = () => {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const persistSession = (session) => {
  if (typeof window === "undefined") return;
  if (!session) {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
};

const normalizePlatoon = (value) => {
  const platoon = (value || "").trim();
  if (!platoon) return "";
  const key = platoon.toLowerCase().replace(/[\s_-]/g, "");
  if (BATTALION_ALIASES.has(key)) return "";
  return platoon;
};

const normalizeViewMode = (value, normalizedPlatoon) => {
  const raw = `${value || ""}`.trim();
  if (!raw) return normalizedPlatoon ? "platoon" : "battalion";
  const key = raw.toLowerCase().replace(/[\s_-]/g, "");
  if (key === "battalion" || key === "גדוד") return "battalion";
  if (key === "platoon" || key === "company" || key === "פלוגה") return "platoon";
  return normalizedPlatoon ? "platoon" : "battalion";
};

const buildSession = ({
  token = "",
  session = "",
  email = "",
  platoon = "",
  viewMode = "",
}) => {
  const normalizedPlatoon = normalizePlatoon(platoon);
  const normalizedViewMode = normalizeViewMode(viewMode, normalizedPlatoon);
  return {
    token,
    session: session || token,
    user: {
      email: email || "guest@spearhead.local",
      platoon: normalizedPlatoon,
      role: normalizedPlatoon ? "platoon" : "battalion",
      viewMode: normalizedViewMode,
    },
  };
};

const extractSessionFromUrl = () => {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token") || "";
  const session = params.get("session") || "";
  const email = params.get("email") || "";
  const platoon = params.get("platoon") || params.get("platoon_override") || "";
  const viewMode = params.get("viewMode") || "";
  if (!token && !session && !email && !platoon) return null;
  return buildSession({ token, session, email, platoon, viewMode });
};

const readBootstrapFromUrl = () => {
  if (typeof window === "undefined") {
    return { session: null, authError: "", shouldCleanUrl: false };
  }
  const params = new URLSearchParams(window.location.search);
  const authErrorCode = params.get("authError") || "";
  const authError = authErrorCode ? (AUTH_ERROR_MESSAGES[authErrorCode] || "שגיאת התחברות") : "";
  const session = authError ? null : extractSessionFromUrl();
  return {
    session,
    authError,
    shouldCleanUrl: Boolean(authErrorCode || session),
  };
};

function App() {
  const bootstrap = useMemo(() => readBootstrapFromUrl(), []);
  const [session, setSession] = useState(() => bootstrap.session || readStoredSession());
  const [authError, setAuthError] = useState(() => bootstrap.authError);

  useEffect(() => {
    if (bootstrap.authError) {
      persistSession(null);
    } else if (bootstrap.session) {
      persistSession(bootstrap.session);
    }
    if (bootstrap.shouldCleanUrl && typeof window !== "undefined") {
      const cleanUrl = `${window.location.origin}${window.location.pathname}`;
      window.history.replaceState({}, document.title, cleanUrl);
    }
  }, [bootstrap]);

  const handleLogout = useCallback(() => {
    setSession(null);
    setAuthError("");
    persistSession(null);
  }, []);

  const handleLogin = useCallback((payload) => {
    const next = buildSession(payload);
    setSession(next);
    setAuthError("");
    persistSession(next);
  }, []);

  const apiClient = useMemo(
    () =>
      createApiClient({
        baseUrl:
          typeof window !== "undefined"
            ? window.location.origin.replace(/\/$/, "")
            : "http://127.0.0.1:8000",
        token: session?.token || "",
        oauthSession: session?.session || "",
        onUnauthorized: () => {
          setAuthError("פג תוקף ההתחברות. יש להתחבר מחדש.");
          handleLogout();
        },
      }),
    [session?.token, session?.session, handleLogout],
  );

  return (
    <Container fluid px="md" py="md">
      <Stack gap="md">
        {authError ? (
          <Alert color="red" variant="light" title="שגיאת הזדהות">
            {authError}
          </Alert>
        ) : null}

        {session ? (
          <DashboardContent client={apiClient} user={session.user} onLogout={handleLogout} />
        ) : (
          <SimpleLogin onLogin={handleLogin} />
        )}
      </Stack>
    </Container>
  );
}

export default App;
