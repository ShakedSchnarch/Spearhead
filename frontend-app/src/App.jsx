import { Alert, Container, Stack } from "@mantine/core";
import { useCallback, useEffect, useMemo, useState } from "react";

import { createApiClient } from "./api/client";
import { DashboardContent } from "./components/DashboardContent";
import { SimpleLogin } from "./components/SimpleLogin";

const SESSION_STORAGE_KEY = "spearhead.session.v1";

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
  if (!platoon || platoon.toLowerCase() === "battalion") return "";
  return platoon;
};

const buildSession = ({
  token = "",
  session = "",
  email = "",
  platoon = "",
  viewMode = "",
}) => {
  const normalizedPlatoon = normalizePlatoon(platoon);
  return {
    token,
    session: session || token,
    user: {
      email: email || "guest@spearhead.local",
      platoon: normalizedPlatoon,
      role: normalizedPlatoon ? "platoon" : "battalion",
      viewMode: viewMode || (normalizedPlatoon ? "platoon" : "battalion"),
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

function App() {
  const [session, setSession] = useState(() => readStoredSession());
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    const fromUrl = extractSessionFromUrl();
    if (!fromUrl) return;
    setSession(fromUrl);
    persistSession(fromUrl);
    const cleanUrl = `${window.location.origin}${window.location.pathname}`;
    window.history.replaceState({}, document.title, cleanUrl);
  }, []);

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
          setAuthError("Your session expired. Please sign in again.");
          handleLogout();
        },
      }),
    [session?.token, session?.session, handleLogout],
  );

  return (
    <Container fluid px="md" py="md">
      <Stack gap="md">
        {authError ? (
          <Alert color="red" variant="light" title="Authentication error">
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
