import { createContext, useContext, useMemo, useCallback } from "react";
import { useDashboardState } from "../hooks/useDashboardState";
import { useDashboardData } from "../hooks/useDashboardData";
import { useDashboardActions } from "../hooks/useDashboardActions";
import { useApiClient } from "../hooks/useApiClient";
import { anomalyLabels, knownPlatoons } from "../types/state";

const DashboardContext = createContext(null);

export function DashboardProvider({ children }) {
  const { state, update, clear, helpers } = useDashboardState();
  const {
    apiBase,
    section,
    topN,
    platoon,
    week,
    viewMode,
    activeTab,
    token, // From state, managed by useDashboardState
    user,
    oauthSession,
  } = state;

  // Derive API client
  const apiClient = useApiClient(apiBase, token, oauthSession);

  // Derive Data
  const enabled = Boolean(user);
  const { health, syncStatus, summary, coverage, tabular } = useDashboardData(
    apiClient,
    { section, topN, platoon, week, viewMode },
    enabled
  );

  // Derive Actions
  const { syncMutation, uploadMutation, exportMutation } = useDashboardActions(apiClient);

  // Auth Helpers
  const logout = useCallback(
    () =>
      update((prev) => ({
        ...prev,
        user: null,
        token: "",
        oauthSession: "",
        platoon: "",
        viewMode: "battalion",
      })),
    [update]
  );
  
  // 401 Handling Interceptor Setup (Ideally in useApiClient, but we need logout access)
  // Since useApiClient is a hook returning an instance, we can't easily inject logout callback *into* it 
  // unless we pass it or use an effect.
  // Better pattern: useApiClient takes a `onUnauthorized` callback.
  
  // Let's defer strict interceptor to useApiClient modification, 
  // but here we simply need to ensure we pass the right args.

  const login = useCallback(
    (payload) =>
      update((prev) => ({
        ...prev,
        user: {
          platoon: payload.platoon,
          email: payload.email,
          token: payload.token || "", 
        },
        token: payload.token || "",
        oauthSession: payload.oauthSession || "", // Explicit separation
        platoon: payload.platoon || prev.platoon,
        viewMode: payload.viewMode || (payload.platoon ? "platoon" : "battalion"),
        activeTab: "dashboard",
      })),
    [update]
  );
  
  const setBanner = useCallback((banner) => {
    // Ideally this should be in state or a separate UI context
    // For now we can expose a setter if we lift banner state here?
    // Let's keep banner local to App or Layout?
    // Actually, widespread use suggests it should be here.
    // Adding to ref via state update or new state? 
    // Let's defer banner to a UIContext or keep it simple in App.jsx initially.
  }, []);

  const value = useMemo(
    () => ({
      state,
      update,
      clear,
      data: { health, syncStatus, summary, coverage, tabular },
      actions: { syncMutation, uploadMutation, exportMutation, login, logout },
      helpers: { ...helpers, knownPlatoons, friendlyImportName: (k) => k }, // Add more helpers
    }),
    [state, update, clear, helpers, health, syncStatus, summary, coverage, tabular, syncMutation, uploadMutation, exportMutation, login, logout]
  );

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}

export const useDashboard = () => {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
};
