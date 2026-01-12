import { EmptyCard } from "./EmptyCard";
import { SummaryTable } from "./SummaryTable";

export function FormStatusTables({ formsOk, formsGaps, topN = 5 }) {
  const okRows = (formsOk || [])
    .slice(0, topN)
    .map((f, idx) => ({ key: idx, cells: [f.platoon || f.item || "?", f.week || "?", f.total || f.count || 0] }));
  const gapRows = (formsGaps || [])
    .slice(0, topN)
    .map((f, idx) => ({ key: idx, cells: [f.platoon || f.item || "?", f.week || "?", f.total || f.count || 0] }));
  return (
    <div className="grid two-col">
      {okRows.length ? (
        <SummaryTable title="טפסים תקינים" headers={["פלוגה", "שבוע", "סה\"כ"]} rows={okRows} />
      ) : (
        <EmptyCard title="אין טפסים תקינים" message="לא נמצאו טפסים תקינים לנתונים שהועלו." />
      )}
      {gapRows.length ? (
        <SummaryTable title="פערי טפסים" headers={["פלוגה", "שבוע", "סה\"כ"]} rows={gapRows} />
      ) : (
        <EmptyCard title="אין פערי טפסים" message="לא נמצאו פערים ברשומות הטפסים." />
      )}
    </div>
  );
}
