import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MantineProvider, createTheme } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "./index.css";
import App from "./App.jsx";

const theme = createTheme({
  fontFamily: '"Space Grotesk", "Inter", system-ui, -apple-system, sans-serif',
  defaultRadius: "md",
  primaryColor: "cyan",
  dir: "rtl",
});

const queryClient = new QueryClient();

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="dark" withGlobalStyles withNormalizeCSS>
      <Notifications position="top-center" />
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </MantineProvider>
  </StrictMode>,
);
