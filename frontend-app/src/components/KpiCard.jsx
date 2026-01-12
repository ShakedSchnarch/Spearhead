import { Paper, Text } from "@mantine/core";

export function KpiCard({ label, value, hint, tone = "neutral" }) {
  return (
    <Paper className={`kpi-card ${tone}`} withBorder shadow="sm" padding="md" radius="md">
      <Text size="xs" c="dimmed" className="kpi-card__label">
        {label}
      </Text>
      <div className="kpi-card__value">{value}</div>
      {hint && (
        <Text size="xs" c="dimmed" className="kpi-card__hint">
          {hint}
        </Text>
      )}
    </Paper>
  );
}
