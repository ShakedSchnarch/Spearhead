import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, Text, useMantineTheme } from "@mantine/core";

export function PlatoonComparison({ data, height = 300 }) {
  // data: [{ platoon: "Kfir", score: 88.5 }, ...]
  const theme = useMantineTheme();

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Text size="lg" fw={700} mb="md">
        כשירות פלוגתית (השוואה)
      </Text>
      <div style={{ width: "100%", height, direction: "ltr" }}>
        <ResponsiveContainer>
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="platoon" />
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              cursor={{ fill: "transparent" }}
              contentStyle={{
                borderRadius: "8px",
                border: "none",
                boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
              }}
            />
            <ReferenceLine y={80} stroke="green" strokeDasharray="3 3" />
            <Bar
              dataKey="score"
              fill={theme.colors.blue[6]}
              radius={[4, 4, 0, 0]}
              barSize={40}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
