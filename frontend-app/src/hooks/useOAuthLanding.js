import { useEffect } from "react";

/**
 * Reads OAuth callback params from the URL (?token=&email=&platoon=&viewMode=)
 * and passes them to the provided handler once, then cleans the URL.
 */
export function useOAuthLanding(onComplete) {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    const session = params.get("session");
    const email = params.get("email");
    const platoon = params.get("platoon") || params.get("platoon_override") || "";
    const viewMode = params.get("viewMode") || (platoon ? "platoon" : "");
    if (token || email || platoon) {
      onComplete({
        token: token || "",
        session: session || token || "",
        email: email || "",
        platoon,
        viewMode: viewMode || "battalion",
      });
      const cleanUrl = window.location.origin + window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    }
  }, [onComplete]);
}
