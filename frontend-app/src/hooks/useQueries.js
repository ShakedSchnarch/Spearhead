import { useQuery } from "@tanstack/react-query";
import { useDashboard } from "../context/DashboardContext";

export function useQueries() {
  const { client, state } = useDashboard();
  const { section, platoon, week } = state;

  const byFamily = useQuery({
    queryKey: ["queries", "by-family", client?.baseUrl, section, platoon, week],
    queryFn: ({ signal }) =>
      client.tabularByFamily({ section, platoon, week }, signal),
    enabled: !!client,
    staleTime: 10_000,
  });

  const gapsByPlatoon = useQuery({
    queryKey: ["queries", "gaps-by-platoon", client?.baseUrl, section, week],
    queryFn: ({ signal }) =>
      client.tabularGapsByPlatoon({ section, week }, signal),
    enabled: !!client,
    staleTime: 10_000,
  });

  return { byFamily, gapsByPlatoon };
}
