import { useMemo } from "react";
import { createApiClient } from "../api/client";

export function useApiClient(apiBase, token, oauthSession, onUnauthorized) {
  return useMemo(
    () => createApiClient({ baseUrl: apiBase, token, oauthSession, onUnauthorized }),
    [apiBase, token, oauthSession, onUnauthorized]
  );
}
