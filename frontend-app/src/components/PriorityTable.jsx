import { Table, Card, Text, Badge, ScrollArea } from "@mantine/core";

export function PriorityTable({ title, rows, height = 300 }) {
  // rows expected: Array of { tank_id, score, grade, critical_gaps, top_missing_items }

  const getScoreColor = (score) => {
    if (score >= 90) return "green";
    if (score >= 60) return "yellow";
    return "red";
  };

  const tableRows = rows.map((row) => (
    <Table.Tr key={row.tank_id}>
      <Table.Td>
        <Text fw={700}>{row.tank_id}</Text>
      </Table.Td>
      <Table.Td>
        <Badge color={getScoreColor(row.score)} variant="light">
          {row.score}% ({row.grade})
        </Badge>
      </Table.Td>
      <Table.Td>
        {row.critical_gaps && row.critical_gaps.length > 0 ? (
          <Badge color="red" variant="filled">
            STOP: {row.critical_gaps[0]}
          </Badge>
        ) : (
          <Text size="sm" c="dimmed">
            {row.top_missing_items?.join(", ") || "No specific gaps"}
          </Text>
        )}
      </Table.Td>
    </Table.Tr>
  ));

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text size="lg" fw={700} mb="md">
        {title}
      </Text>
      <ScrollArea h={height}>
        <Table stickyHeader verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>טנק</Table.Th>
              <Table.Th>כשירות</Table.Th>
              <Table.Th>חריגים / פערים עיקריים</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>{tableRows}</Table.Tbody>
        </Table>
      </ScrollArea>
    </Card>
  );
}
