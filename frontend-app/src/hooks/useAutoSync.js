import { useEffect, useRef } from "react";
import { useDashboard } from "../context/DashboardContext";
import { notifications } from "@mantine/notifications";

/**
 * useAutoSync Hook
 * Automatically triggers a data sync when the user logs in.
 * Prevents infinite loops by using a ref to track sync status per session/user.
 */
export function useAutoSync() {
    const { state, actions } = useDashboard();
    const { user } = state;
    const { syncMutation } = actions;
    
    // Track if we have synced for this specific user/session
    // We use a ref so it doesn't trigger re-renders, but we key it by user.token/email
    // to reset if the user changes.
    const syncedUserRef = useRef(null);

    useEffect(() => {
        // 1. If no user, do nothing.
        if (!user || !user.token) return;

        // 2. If already synced for this user, do nothing.
        if (syncedUserRef.current === user.token) return;

        // 3. Trigger Sync
        console.info("[AutoSync] Triggering initial sync for user:", user.email || "guest");
        syncedUserRef.current = user.token; // Mark as started

        const target = user.platoon && user.platoon !== "battalion" ? user.platoon : "all";

        syncMutation.mutateAsync(target)
            .then(() => {
                notifications.show({ 
                    title: "סנכרון", 
                    message: "הנתונים עודכנו בהצלחה", 
                    color: "teal",
                    autoClose: 2000 
                });
            })
            .catch((err) => {
                console.error("[AutoSync] Failed:", err);
                notifications.show({ 
                    title: "שגיאת סנכרון", 
                    message: "לא ניתן היה למשוך נתונים עדכניים", 
                    color: "red" 
                });
            });

    }, [user, syncMutation]);
    
    return {
        isSyncing: syncMutation.isPending,
        isError: syncMutation.isError
    };
}
