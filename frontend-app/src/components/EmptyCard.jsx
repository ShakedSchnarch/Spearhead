import { Card, Text } from "@mantine/core";

export function EmptyCard({ title, message }) {
  return (
    <Card withBorder shadow="sm" padding="md" radius="md" className="card">
      <div className="card-title">{title}</div>
      <div className="empty-card">
        <Text size="sm" c="dimmed">
          {message}
        </Text>
      </div>
    </Card>
  );
}
