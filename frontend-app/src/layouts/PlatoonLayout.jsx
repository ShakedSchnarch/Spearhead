import { Outlet, Navigate } from "react-router-dom";
import { HeroHeader } from "../components/HeroHeader";
import { useDashboard } from "../context/DashboardContext";
import { useMemo } from "react";

// Logos (Duplicated from MainLayout for now, should extract to constant)
const assetBase = "/spearhead";
const logoPath = (file) => `${assetBase}/logos/${file}`;
const platoonLogos = {
  כפיר: logoPath("Kfir_logo.JPG"),
  סופה: logoPath("Sufa_logo.JPG"),
  מחץ: logoPath("Machatz_logo.JPG"),
  פלסם: logoPath("Palsam_logo.JPG"),
  romach: logoPath("Romach_75_logo.JPG"),
};

export function PlatoonLayout() {
  const { state, actions, data } = useDashboard();
  const { user } = state;
  const { health } = data;

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const logo = useMemo(() => {
    return platoonLogos[user.platoon] || platoonLogos.romach;
  }, [user.platoon]);

  return (
    <div className="layout-platoon page">
      <HeroHeader
        user={user}
        viewMode="platoon"
        platoon={user.platoon}
        health={health?.isError ? "Offline" : "Online"}
        syncEnabled={true}
        onLogout={actions.logout}
        logoSrc={logo}
      />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
