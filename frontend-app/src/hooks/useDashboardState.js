import { useCallback, useMemo } from "react";
import { anomalyLabels, defaultDashboardState, knownPlatoons, STORAGE_KEY } from "../types/state";
import { usePersistentState } from "./usePersistentState";

const coerceTopN = (value) => {
  const num = Number(value);
  if (Number.isNaN(num) || num <= 0) return defaultDashboardState.topN;
  return num;
};

export function useDashboardState() {
  const [state, setState] = usePersistentState(STORAGE_KEY, () => ({ ...defaultDashboardState }));

  const update = useCallback(
    (patch) =>
      setState((prev) => {
        const incoming = typeof patch === "function" ? patch(prev) : patch;
        const next = { ...prev, ...incoming };
        next.topN = coerceTopN(next.topN);
        return next;
      }),
    [setState],
  );

  const clear = useCallback(() => setState({ ...defaultDashboardState }), [setState]);

  const helpers = useMemo(
    () => ({
      knownPlatoons,
      anomalyLabels,
    }),
    [],
  );

  return { state, update, clear, helpers };
}
