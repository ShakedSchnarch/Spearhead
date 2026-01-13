import { useCallback, useMemo, useState } from "react";
import { anomalyLabels, defaultDashboardState, knownPlatoons, STORAGE_KEY } from "../types/state";
import { usePersistentState } from "./usePersistentState";

const coerceTopN = (value) => {
  const num = Number(value);
  if (Number.isNaN(num) || num <= 0) return defaultDashboardState.topN;
  return num;
};

export function useDashboardState() {
  // Split state: Persistence for preferences, Memory for Auth
  const [preferences, setPreferences] = usePersistentState(STORAGE_KEY, {
    apiBase: defaultDashboardState.apiBase,
    section: defaultDashboardState.section,
    topN: defaultDashboardState.topN,
    week: defaultDashboardState.week,
    // viewMode and platoon are persistent
    viewMode: defaultDashboardState.viewMode,
    platoon: "", // Persist last selected platoon
  });

  const [auth, setAuth] = useState({
    user: null,
    token: "",
    oauthSession: "",
    activeTab: "dashboard",
  });

  const state = { ...preferences, ...auth };

  const update = useCallback(
    (patch) => {
      // Determine what to update
      const incoming = typeof patch === "function" ? patch(state) : patch;
      
      // Separate keys
      const nextPrefs = { ...preferences };
      const nextAuth = { ...auth };
      let prefsChanged = false;
      let authChanged = false;

      Object.keys(incoming).forEach(k => {
        if (["user", "token", "oauthSession", "activeTab"].includes(k)) {
          nextAuth[k] = incoming[k];
          authChanged = true;
        } else {
          nextPrefs[k] = incoming[k];
          prefsChanged = true;
        }
      });

      if (prefsChanged) {
        nextPrefs.topN = coerceTopN(nextPrefs.topN); // logic moved here
        setPreferences(nextPrefs);
      }
      if (authChanged) setAuth(nextAuth);
    },
    [preferences, auth, setPreferences, setAuth, state]
  );

  const clear = useCallback(() => {
    setPreferences({
        apiBase: defaultDashboardState.apiBase,
        section: defaultDashboardState.section,
        topN: defaultDashboardState.topN,
        week: defaultDashboardState.week,
        viewMode: defaultDashboardState.viewMode,
        platoon: ""
    });
    setAuth({
        user: null,
        token: "",
        oauthSession: "",
        activeTab: "dashboard",
    });
  }, [setPreferences, setAuth]);

  const helpers = useMemo(
    () => ({
      knownPlatoons,
      anomalyLabels,
    }),
    [],
  );

  return { state, update, clear, helpers };
}
