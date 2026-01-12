import { DashboardProvider } from "./context/DashboardContext";
import { MainLayout } from "./components/MainLayout";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./index.css";

function App() {
  return (
    <ErrorBoundary>
      <DashboardProvider>
        <MainLayout />
      </DashboardProvider>
    </ErrorBoundary>
  );
}

export default App;
