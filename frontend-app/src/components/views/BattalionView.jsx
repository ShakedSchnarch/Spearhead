import { useMemo } from "react";
import { useDashboard } from "../../context/DashboardContext";
import { SummaryTable } from "../SummaryTable";
import { EmptyCard } from "../EmptyCard";

export function BattalionView() {
  const { data } = useDashboard();
  const summaryData = data.summary.data;

  const platoonRows = useMemo(() => {
    if (!summaryData?.platoons) return [];

    // Sort logic can be added here if needed, defaults to whatever order Object.values gives (usually insertion order or alpha)
    // Let's sort by platoon name just in case
    const platoons = Object.values(summaryData.platoons || {}).sort((a, b) =>
      a.platoon.localeCompare(b.platoon)
    );

    return platoons.map((p) => {
      const zivudTotal = Object.values(p.zivud_gaps || {}).reduce(
        (acc, v) => acc + (v || 0),
        0
      );
      const meansTotal = Object.values(p.means || {}).reduce(
        (acc, v) => acc + (v?.count || 0),
        0
      );
      const ammoTotal = Object.values(p.ammo || {}).reduce(
        (acc, v) => acc + (v?.total || 0),
        0
      );

      return {
        key: p.platoon,
        cells: [
          p.platoon,
          p.tank_count,
          zivudTotal,
          meansTotal,
          Math.round(ammoTotal),
        ],
      };
    });
  }, [summaryData]);

  if (!summaryData)
    return <EmptyCard title="אין נתונים" message="ממתין לסנכרון..." />;

  return (
    <div className="battalion-view">
      <SummaryTable
        title="סטטוס גדודי (תמונת מצב)"
        headers={["פלוגה", "טנקים", "פער זיווד", "פער אמצעים", "כמות תחמושת"]}
        rows={platoonRows}
      />
    </div>
  );
}
