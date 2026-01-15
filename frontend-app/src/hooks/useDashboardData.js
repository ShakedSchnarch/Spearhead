import { useQuery } from "@tanstack/react-query";

export function useDashboardData(
  client,
  filters,
  enabled = true,
  isRestricted = false
) {
  const { section, topN, platoon, week, viewMode } = filters;
  const summaryEnabled =
    enabled && (viewMode !== "platoon" || Boolean(platoon));

  const health = useQuery({
    queryKey: ["health", client.baseUrl],
    queryFn: ({ signal }) => client.health(signal),
    enabled,
    staleTime: 60_000,
  });

  const syncStatus = useQuery({
    queryKey: ["sync-status", client.baseUrl],
    queryFn: ({ signal }) => client.syncStatus(signal),
    enabled,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });

  const summary = useQuery({
    queryKey: ["summary", client.baseUrl, viewMode, week, platoon],
    queryFn: ({ signal }) =>
      client.summary({ mode: viewMode, week, platoon }, signal),
    enabled: summaryEnabled,
    staleTime: 10_000,
    keepPreviousData: true,
  });

  // Coverage is primarily a Battalion metric. Platoon users get 403.
  // Update: Backend now supports filtering.
  const coverage = useQuery({
    queryKey: ["coverage", client.baseUrl, week],
    queryFn: ({ signal }) => client.coverage({ week }, signal),
    enabled: enabled,
    staleTime: 10_000,
    keepPreviousData: true,
    retry: (failureCount, error) => {
      // Don't retry 403s
      if (error?.status === 403) return false;
      return failureCount < 3;
    },
  });

  const tabular = useQuery({
    queryKey: ["tabular", client.baseUrl, section, topN, platoon, week],
    queryFn: ({ signal }) =>
      client.tabularBundle({ section, topN, platoon, week }, signal),
    enabled,
    staleTime: 5_000,
    keepPreviousData: true,
  });

  return { health, syncStatus, summary, coverage, tabular };
}
