import { useMemo } from "react";
import { createApiClient } from "../api/client";

export function useApiClient(apiBase, token, oauthSession) {
  return useMemo(() => createApiClient({ baseUrl: apiBase, token, oauthSession }), [apiBase, token, oauthSession]);
}
