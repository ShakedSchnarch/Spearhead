import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DashboardProvider } from "./context/DashboardContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { LoginLayout } from "./layouts/LoginLayout";
import { BattalionLayout } from "./layouts/BattalionLayout";
import { PlatoonLayout } from "./layouts/PlatoonLayout";
import { DashboardContent } from "./components/DashboardContent";
import "./index.css";

function App() {
  return (
    <ErrorBoundary>
      <DashboardProvider>
        <BrowserRouter basename="/spearhead">
          <Routes>
            {/* Public Route */}
            <Route path="/login" element={<LoginLayout />} />

            {/* Battalion Routes */}
            <Route path="/battalion" element={<BattalionLayout />}>
              <Route index element={<DashboardContent />} />
            </Route>

            {/* Platoon Routes */}
            <Route path="/platoon" element={<PlatoonLayout />}>
              <Route index element={<DashboardContent />} />
            </Route>

            {/* Default Route (Handle OAuth Landing) */}
            <Route path="/" element={<LoginLayout />} />

            {/* Catch all */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </DashboardProvider>
    </ErrorBoundary>
  );
}

export default App;
