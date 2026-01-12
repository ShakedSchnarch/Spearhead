import { useMutation, useQueryClient } from "@tanstack/react-query";

export function useDashboardActions(client) {
  const queryClient = useQueryClient();

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: ["sync-status", client.baseUrl] });
    queryClient.invalidateQueries({ queryKey: ["summary", client.baseUrl] });
    queryClient.invalidateQueries({ queryKey: ["coverage", client.baseUrl] });
    queryClient.invalidateQueries({ queryKey: ["tabular", client.baseUrl] });
  };

  const syncMutation = useMutation({
    mutationFn: (target = "all") => client.syncGoogle(target),
    onSuccess: invalidateData,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ kind, file }) => client.uploadImport(kind, file),
    onSuccess: invalidateData,
  });

  const exportMutation = useMutation({
    mutationFn: ({ mode, params }) => client.exportReport(mode, params),
  });

  return {
    syncMutation,
    uploadMutation,
    exportMutation,
  };
}
