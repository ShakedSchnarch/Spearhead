import { Outlet, Navigate } from "react-router-dom";
import { HeroHeader } from "../components/HeroHeader";
import { useDashboard } from "../context/DashboardContext";

export function BattalionLayout() {
  const { state, actions, data } = useDashboard();
  const { user } = state;
  const { health } = data; // simplified

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Guard: Battalion only
  if (user.platoon && user.platoon !== "battalion") {
    return <Navigate to="/platoon" replace />;
  }

  return (
    <div className="layout-battalion page">
      <HeroHeader
        user={user}
        viewMode="battalion"
        health={health?.isError ? "Offline" : "Online"}
        syncEnabled={true}
        onLogout={actions.logout}
        logoSrc="/spearhead/logos/Romach_75_logo.JPG"
      />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
