import { useQuery } from "@tanstack/react-query";
import { useDashboard } from "../context/DashboardContext";

export function useIntelligence(platoonOverride = null) {
  const { client, state } = useDashboard();
  const { viewMode, platoon: userPlatoon, week } = state;
  const logPayload = (label, payload) => {
    // Trace the raw API payload to debug shape mismatches
    console.log(`[intel] ${label}`, payload);
  };

  // Determine target scope
  // If viewMode is 'platoon', we fetch for the active platoon (userPlatoon)
  // If viewMode is 'battalion', we might fetch overview OR a specific platoon if selected?
  // Current requirement:
  // - Platoon View -> getIntelligence(platoon)
  // - Battalion View -> getBattalionIntelligence()

  const targetPlatoon = platoonOverride || userPlatoon;

  const platoonQuery = useQuery({
    queryKey: ["intelligence", "platoon", targetPlatoon, week],
    queryFn: ({ signal }) =>
      client.getIntelligence(targetPlatoon, { week }, signal),
    enabled: !!client && !!targetPlatoon,
    staleTime: 30000,
    onSuccess: (data) => logPayload(`platoon:${targetPlatoon}`, data),
  });

  const battalionQuery = useQuery({
    queryKey: ["intelligence", "battalion", week],
    queryFn: ({ signal }) => client.getBattalionIntelligence({ week }, signal),
    enabled: !!client && viewMode === "battalion" && !platoonOverride,
    staleTime: 30000,
    retry: (failureCount, error) => {
      if (error?.status === 403) return false;
      return failureCount < 3;
    },
    onSuccess: (data) => logPayload("battalion", data),
  });

  return {
    platoonData: platoonQuery.data,
    platoonLoading: platoonQuery.isLoading,
    platoonError: platoonQuery.error,
    battalionData: battalionQuery.data,
    battalionLoading: battalionQuery.isLoading,
    battalionError: battalionQuery.error,
    refetchPlatoon: platoonQuery.refetch,
    refetchBattalion: battalionQuery.refetch,
  };
}
