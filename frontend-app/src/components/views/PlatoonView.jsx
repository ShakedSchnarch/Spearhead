import { useMemo } from "react";
import { useDashboard } from "../../context/DashboardContext";
import { SummaryTable } from "../SummaryTable";
import { ChartCard } from "../ChartCard";
import { EmptyCard } from "../EmptyCard";

export function PlatoonView() {
  const { state, data } = useDashboard();
  const { platoon } = state;
  const summaryData = data.summary.data;

  // Resolve the specific platoon data
  const platoonSummary = useMemo(() => {
    if (!summaryData) return null;

    // Logic: If mode is Platoon, we trust summaryData.summary
    // If mode is Battalion, we look up platoons[name]
    if (summaryData.mode === "platoon") return summaryData.summary;
    if (
      summaryData.mode === "battalion" &&
      platoon &&
      summaryData.platoons?.[platoon]
    ) {
      return summaryData.platoons[platoon];
    }
    return null;
  }, [summaryData, platoon]);

  const issueRows = useMemo(
    () =>
      (platoonSummary?.issues || []).map((issue, idx) => ({
        key: `${issue.item}-${idx}`,
        cells: [
          issue.item,
          issue.tank_id,
          issue.commander || "-",
          issue.detail,
        ],
      })),
    [platoonSummary]
  );

  const zivudGapRows = useMemo(() => {
    if (!platoonSummary?.zivud_gaps) return [];
    return Object.entries(platoonSummary.zivud_gaps)
      .filter(([_, count]) => count > 0)
      .sort((a, b) => b[1] - a[1]) // Descending
      .map(([item, count]) => ({
        key: item,
        cells: [item, count],
      }));
  }, [platoonSummary]);

  if (!platoon)
    return (
      <EmptyCard title="בחר פלוגה" message="יש לבחור פלוגה כדי לראות נתונים" />
    );
  if (!platoonSummary)
    return (
      <EmptyCard
        title="אין נתונים"
        message={`לא נמצאו נתונים עבור פלוגת ${platoon}`}
      />
    );

  return (
    <div className="platoon-view grid two-col">
      {/* 
         TODO: Hook up real charts to ChartCard. 
         For now, we can show a table of Zivud Gaps on the left, and Issues on the right.
       */}
      <SummaryTable
        title="ריכוז חוסרים (זיווד)"
        headers={["פריט", "כמות חוסר"]}
        rows={zivudGapRows}
      />

      <SummaryTable
        title="פירוט תקלות וחריגות"
        headers={["פריט", "צ' טנק", "מפקד", "דגשים"]}
        rows={issueRows}
      />
    </div>
  );
}
