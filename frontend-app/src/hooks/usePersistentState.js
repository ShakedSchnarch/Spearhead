import { useEffect, useState } from "react";

const canUseStorage = () => typeof window !== "undefined" && typeof window.localStorage !== "undefined";

export function usePersistentState(key, initialValue) {
  const [state, setState] = useState(() => {
    if (!canUseStorage()) return initialValue;
    try {
      const raw = window.localStorage.getItem(key);
      if (raw) return JSON.parse(raw);
    } catch {
      // ignore malformed cache and fall back to defaults
    }
    return typeof initialValue === "function" ? initialValue() : initialValue;
  });

  useEffect(() => {
    if (!canUseStorage()) return;
    try {
      window.localStorage.setItem(key, JSON.stringify(state));
    } catch {
      // ignore quota/storage issues silently
    }
  }, [key, state]);

  return [state, setState];
}
