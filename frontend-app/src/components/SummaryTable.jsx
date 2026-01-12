import { Card } from "@mantine/core";

export function SummaryTable({ title, headers, rows }) {
  return (
    <Card withBorder shadow="sm" padding="md" radius="md" className="card">
      <div className="card-title">{title}</div>
      <table className="table">
        <thead>
          <tr>
            {headers.map((h) => (
              <th key={h}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row) => (
              <tr key={row.key || row.cells[0]}>
                {row.cells.map((v, idx) => (
                  <td key={idx}>{v}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={headers.length}>אין נתונים</td>
            </tr>
          )}
        </tbody>
      </table>
    </Card>
  );
}
