import {
  Badge,
  Button,
  Card,
  Group,
  Image,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useState } from "react";
import { battalionMeta, COMPANY_KEYS, getUnitMeta } from "../config/unitMeta";

const buildOAuthState = (selected) => {
  const platoon = selected === "battalion" ? "" : selected;
  const viewMode = selected === "battalion" ? "battalion" : "platoon";
  return JSON.stringify({ platoon, viewMode, ts: Date.now() });
};

export function SimpleLogin({ onLogin }) {
  const [selected, setSelected] = useState("כפיר");
  const oauthUrl = import.meta.env.VITE_GOOGLE_OAUTH_URL || "";
  const allowGuest = (import.meta.env.VITE_ALLOW_GUEST_LOGIN || "").toLowerCase() === "true";
  const selectedMeta = getUnitMeta(selected);
  const companyCards = COMPANY_KEYS.map((key) => getUnitMeta(key));

  const handleGoogleLogin = () => {
    if (!oauthUrl) {
      const isLocal = typeof window !== "undefined"
        && ["127.0.0.1", "localhost"].includes(window.location.hostname);

      if (allowGuest || isLocal) {
        const platoon = selected === "battalion" ? "" : selected;
        onLogin({
          email: "guest@spearhead.local",
          platoon,
          viewMode: platoon ? "platoon" : "battalion",
        });
        return;
      }

      const url = new URL("/auth/google/start", window.location.origin);
      url.searchParams.set("state", buildOAuthState(selected));
      window.location.href = url.toString();
      return;
    }

    const url = new URL(oauthUrl);
    url.searchParams.set("state", buildOAuthState(selected));
    window.location.href = url.toString();
  };

  return (
    <Card withBorder shadow="lg" maw={880} mx="auto" mt="xl" p="lg" className="auth-shell">
      <Stack gap="lg">
        <Group justify="space-between" wrap="wrap">
          <div>
            <Title order={2}>קצה הרומח · גדוד 75</Title>
          </div>
          <Badge variant="light" color="cyan" size="lg">
            גרסה 2
          </Badge>
        </Group>

        <Card withBorder radius="md" p="sm" className="auth-mode-card">
          <Stack gap="sm">
            <Text fw={700}>כניסה במצב פלוגה</Text>
            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
              {companyCards.map((meta) => (
                <Card
                  key={meta.key}
                  withBorder
                  radius="md"
                  p="sm"
                  className="unit-logo-card"
                  data-active={selected === meta.key ? "true" : "false"}
                  onClick={() => setSelected(meta.key)}
                >
                  <Stack align="center" gap={6}>
                    <Image src={meta.logo} alt={meta.shortLabel} radius="sm" h={58} w={58} fit="cover" />
                    <Text size="sm" fw={700}>
                      {meta.shortLabel}
                    </Text>
                  </Stack>
                </Card>
              ))}
            </SimpleGrid>
          </Stack>
        </Card>

        <Card
          withBorder
          radius="md"
          p="md"
          className="battalion-login-card"
          data-active={selected === "battalion" ? "true" : "false"}
          onClick={() => setSelected("battalion")}
        >
          <Group justify="space-between" wrap="wrap" gap="md">
            <Group gap="md" wrap="nowrap">
              <Image
                src={battalionMeta.logo}
                alt={battalionMeta.label}
                radius="md"
                w={58}
                h={58}
                fit="cover"
              />
              <div>
                <Text fw={700}>כניסה במצב גדודי</Text>
                <Text size="sm" c="dimmed">
                  תצוגת השוואה רוחבית בין כלל הפלוגות
                </Text>
              </div>
            </Group>
            <Badge variant="light" color="cyan">
              גדוד 75
            </Badge>
          </Group>
        </Card>

        <Card withBorder radius="md" p="md" className="auth-controls-card">
          <Stack gap="md">
            <Group justify="space-between">
              <Text fw={700}>בחירת מצב כניסה</Text>
              <Badge variant="filled" style={{ backgroundColor: selectedMeta.color }}>
                {selectedMeta.shortLabel}
              </Badge>
            </Group>

            <Button onClick={handleGoogleLogin} color="cyan" size="md">
              התחברות עם Google
            </Button>
          </Stack>
        </Card>

      </Stack>
    </Card>
  );
}
