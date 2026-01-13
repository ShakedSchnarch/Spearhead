import { LoginOverlay } from "../components/LoginOverlay";
import { useDashboard } from "../context/DashboardContext";
import { useOAuthLanding } from "../hooks/useOAuthLanding";
import { Navigate } from "react-router-dom";

export function LoginLayout() {
  const { state, actions, helpers } = useDashboard();
  const { user } = state;

  // Handle OAuth Callback
  useOAuthLanding(actions.login);

  if (user) {
    const target =
      user.platoon && user.platoon !== "battalion" ? "/platoon" : "/battalion";
    return <Navigate to={target} replace />;
  }

  // OAuth props
  const oauthUrl = import.meta.env.VITE_GOOGLE_OAUTH_URL || "";
  const oauthReady = Boolean(oauthUrl);
  // Need logos? reusing helper knownPlatoons but logos are inside MainLayout...
  // For now pass empty logos or move logos to a shared file.
  // The LoginOverlay needs logos.

  // Quick fix: Hardcode logos logic or import
  const assetBase = "/spearhead";
  const logoPath = (file) => `${assetBase}/logos/${file}`;
  const platoonLogos = {
    כפיר: logoPath("Kfir_logo.JPG"),
    סופה: logoPath("Sufa_logo.JPG"),
    מחץ: logoPath("Machatz_logo.JPG"),
    פלסם: logoPath("Palsam_logo.JPG"),
    romach: logoPath("Romach_75_logo.JPG"),
  };

  return (
    <div className="layout-login">
      <LoginOverlay
        onLogin={actions.login}
        defaultPlatoon="battalion"
        oauthReady={oauthReady}
        oauthUrl={oauthUrl}
        logos={platoonLogos}
      />
    </div>
  );
}
