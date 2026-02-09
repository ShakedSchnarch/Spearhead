import { Button, Card, SegmentedControl, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";

const DEFAULT_UNITS = [
  { value: "battalion", label: "גדוד" },
  { value: "כפיר", label: "כפיר" },
  { value: "מחץ", label: "מחץ" },
  { value: "סופה", label: "סופה" },
];

const buildOAuthState = (selected) => {
  const platoon = selected === "battalion" ? "" : selected;
  const viewMode = selected === "battalion" ? "battalion" : "platoon";
  return JSON.stringify({ platoon, viewMode, ts: Date.now() });
};

export function SimpleLogin({ onLogin }) {
  const [selected, setSelected] = useState("battalion");
  const oauthUrl = import.meta.env.VITE_GOOGLE_OAUTH_URL || "";

  const handleGoogleLogin = () => {
    if (!oauthUrl) {
      const platoon = selected === "battalion" ? "" : selected;
      onLogin({
        email: "guest@spearhead.local",
        platoon,
        viewMode: platoon ? "platoon" : "battalion",
      });
      return;
    }

    const url = new URL(oauthUrl);
    url.searchParams.set("state", buildOAuthState(selected));
    window.location.href = url.toString();
  };

  return (
    <Card withBorder shadow="sm" maw={520} mx="auto" mt="xl">
      <Stack gap="md">
        <div>
          <Title order={2}>Spearhead</Title>
          <Text c="dimmed" size="sm">
            Responses-only dashboard. Sign in and start working.
          </Text>
        </div>

        <SegmentedControl
          fullWidth
          value={selected}
          onChange={setSelected}
          data={DEFAULT_UNITS}
          radius="md"
        />

        <Button onClick={handleGoogleLogin} color="cyan">
          Sign in with Google
        </Button>

        {!oauthUrl ? (
          <Text size="xs" c="dimmed">
            OAuth URL is not configured. Running in local guest mode.
          </Text>
        ) : null}
      </Stack>
    </Card>
  );
}
