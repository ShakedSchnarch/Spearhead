import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  Group,
  Loader,
  Select,
  Table,
  Text,
  TextInput,
} from "@mantine/core";

import { useDashboard } from "../context/DashboardContext";
import { EmptyCard } from "./EmptyCard";

const sectionOptions = [
  { value: "zivud", label: "זיווד" },
  { value: "ammo", label: "תחמושת" },
  { value: "summary_zivud", label: "סיכום זיווד" },
  { value: "summary_ammo", label: "סיכום תחמושת" },
  { value: "all", label: "הכל" },
];

export function QueryPanel() {
  const { state, client } = useDashboard();
  const { section: defaultSection, platoon, week } = state;
  const [text, setText] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [section, setSection] = useState(defaultSection || "zivud");

  const targetPlatoon = platoon || undefined;
  const resolvedSection = section === "all" ? undefined : section;

  const searchQuery = useQuery({
    queryKey: [
      "tabular-search",
      client?.baseUrl,
      submitted,
      resolvedSection,
      targetPlatoon,
      week,
    ],
    queryFn: ({ signal }) =>
      client.tabularSearch(
        {
          q: submitted,
          section: resolvedSection,
          platoon: targetPlatoon,
          week,
        },
        signal
      ),
    enabled: !!client && submitted.length >= 2,
    staleTime: 5_000,
  });

  const rows = useMemo(
    () =>
      (searchQuery.data || []).map((row, idx) => (
        <Table.Tr key={`${row.item}-${row.column}-${idx}`}>
          <Table.Td>{row.item || "?"}</Table.Td>
          <Table.Td>
            <Badge variant="light" color="gray">
              {row.column || "-"}
            </Badge>
          </Table.Td>
          <Table.Td>
            {row.is_gap ? (
              <Badge color="red" variant="filled">
                {row.value ?? "חסר"}
              </Badge>
            ) : (
              <Text size="sm" fw={600}>
                {row.value ?? "-"}
              </Text>
            )}
          </Table.Td>
          <Table.Td>{row.platoon || targetPlatoon || "גדוד"}</Table.Td>
          <Table.Td>{row.week || "לא ידוע"}</Table.Td>
          <Table.Td>
            <Badge variant="outline" color="cyan">
              {row.section}
            </Badge>
          </Table.Td>
        </Table.Tr>
      )),
    [searchQuery.data, targetPlatoon]
  );

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (trimmed.length < 2) return;
    setSubmitted(trimmed);
  };

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Group justify="space-between" align="flex-end" mb="md">
        <div>
          <Text fw={800} size="lg">
            ממשק חיפוש (Legacy)
          </Text>
          <Text size="sm" c="dimmed">
            חפש פריט/תחמושת מתוך קבצי האקסל שהועלו (Query Service)
          </Text>
        </div>
        <Group>
          <Select
            data={sectionOptions}
            value={section}
            onChange={setSection}
            label="מקור"
            size="sm"
            allowDeselect={false}
            withinPortal
          />
          <TextInput
            label="חיפוש לפי פריט / טנק / ערך"
            placeholder="לדוגמה: מג\"מ / שרשרת גרירה / 653"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSubmit();
            }}
            size="sm"
            style={{ minWidth: 280 }}
          />
          <Button onClick={handleSubmit} disabled={!text.trim()} color="cyan">
            חפש
          </Button>
        </Group>
      </Group>

      {searchQuery.isFetching && (
        <Group justify="center" mb="sm">
          <Loader size="sm" color="cyan" />
          <Text size="sm" c="dimmed">
            טוען תוצאות...
          </Text>
        </Group>
      )}

      {searchQuery.error && (
        <EmptyCard
          title="שגיאת חיפוש"
          message={searchQuery.error.message || "לא ניתן לאחזר נתוני חיפוש"}
        />
      )}

      {!searchQuery.isFetching && submitted && rows.length === 0 && (
        <EmptyCard
          title="לא נמצאו תוצאות"
          message="נסה מונח אחר או בחר מקור נתונים אחר"
        />
      )}

      {rows.length > 0 && (
        <Table stickyHeader verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>פריט</Table.Th>
              <Table.Th>טנק / עמודה</Table.Th>
              <Table.Th>ערך</Table.Th>
              <Table.Th>פלוגה</Table.Th>
              <Table.Th>שבוע</Table.Th>
              <Table.Th>מקור</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>{rows}</Table.Tbody>
        </Table>
      )}
    </Card>
  );
}
