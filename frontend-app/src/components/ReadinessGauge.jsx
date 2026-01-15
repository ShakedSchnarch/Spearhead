import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  ResponsiveContainer,
} from "recharts";
import { Box, Text, useMantineTheme } from "@mantine/core";

export function ReadinessGauge({ score, size = 200 }) {
  const theme = useMantineTheme();
  const hasValue = typeof score === "number" && !Number.isNaN(score);
  const safeScore = hasValue ? score : 0;

  const getColor = (val) => {
    if (val >= 90) return theme.colors.green[6];
    if (val >= 60) return theme.colors.yellow[6];
    return theme.colors.red[6];
  };

  const data = [
    {
      name: "Score",
      value: safeScore,
      fill: getColor(safeScore),
    },
  ];

  return (
    <Box w={size} h={size / 1.5} pos="relative" mx="auto">
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart
          cx="50%"
          cy="70%" // Move down to make it a half-circle arc
          innerRadius="70%"
          outerRadius="100%"
          barSize={20}
          data={data}
          startAngle={180}
          endAngle={0}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, 100]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            background
            clockWise
            dataKey="value"
            cornerRadius={10}
            label={false}
          />
        </RadialBarChart>
      </ResponsiveContainer>
      <Box
        pos="absolute"
        top="60%"
        left="50%"
        style={{ transform: "translate(-50%, -50%)", textAlign: "center" }}
      >
        <Text fz={40} fw={900} lh={1} c={hasValue ? getColor(safeScore) : theme.colors.gray[5]}>
          {hasValue ? `${safeScore}%` : "—"}
        </Text>
        <Text size="sm" c="dimmed" fw={500}>
          כשירות
        </Text>
      </Box>
    </Box>
  );
}
