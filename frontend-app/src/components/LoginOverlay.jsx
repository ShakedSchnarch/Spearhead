import { useState } from "react";
import { Badge, Button, Collapse, Group, Paper, Select, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";

export function LoginOverlay({ onLogin, defaultPlatoon = "battalion", oauthReady, oauthUrl, logos }) {
  const [target, setTarget] = useState(defaultPlatoon || "battalion");
  const [email, setEmail] = useState("");
  const [tokenInput, setTokenInput] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const logoSrc =
    target === "battalion"
      ? logos?.romach
      : logos?.[target] || logos?.romach;

  const handleSubmit = (e) => {
    e.preventDefault();
    const viewMode = target === "battalion" ? "battalion" : "platoon";
    const platoon = target === "battalion" ? "" : target;
    onLogin({ platoon, email, token: tokenInput, viewMode });
  };

  const handleGoogle = () => {
    const viewMode = target === "battalion" ? "battalion" : "platoon";
    const platoon = target === "battalion" ? "" : target;
    if (oauthUrl) {
      try {
        const url = new URL(oauthUrl);
        const statePayload = {
          platoon,
          viewMode,
          email,
          ts: Date.now(),
        };
        url.searchParams.set("state", encodeURIComponent(JSON.stringify(statePayload)));
        window.location.href = url.toString();
      } catch {
        notifications.show({
          title: "OAuth לא מוגדר",
          message: "לא ניתן לנתח את כתובת ה-OAuth שסופקה.",
          color: "red",
        });
      }
      return;
    }
    notifications.show({
      title: "OAuth לא מוגדר",
      message: "לא הוגדר VITE_GOOGLE_OAUTH_URL. משתמש בפלואו הידני.",
      color: "yellow",
    });
    onLogin({ platoon, email: email || "guest@spearhead.local", token: tokenInput, viewMode });
  };

  return (
    <div className="login-overlay">
      <Paper shadow="xl" radius="lg" className="login-card" withBorder>
        <Group justify="center" align="center">
          <Badge color="teal" radius="xl" variant="gradient" gradient={{ from: "green", to: "teal" }}>
            קצה הרומח · Spearhead
          </Badge>
        </Group>
        <div className="login-logo">
          {logoSrc && <img src={logoSrc} alt={target === "battalion" ? "רומח" : target} />}
        </div>
        <Title order={2} ta="center">
          כניסה
        </Title>
        <Text ta="center" c="dimmed" size="sm">
          בחר מצב (גדוד/פלוגה), הזדהה עם חשבון Google, והמשך לסנכרון אוטומטי.
        </Text>
        <Stack gap="xs" mt="sm" component="form" onSubmit={handleSubmit}>
          <Select
            label="מצב"
            value={target}
            onChange={(value) => setTarget(value || "battalion")}
            data={[
              { value: "battalion", label: "גדוד (רומח)" },
              { value: "כפיר", label: "כפיר" },
              { value: "סופה", label: "סופה" },
              { value: "מחץ", label: "מחץ" },
            ]}
            required
          />
          <TextInput
            label="מייל Google"
            placeholder="name@domain"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Collapse in={showAdvanced}>
            <TextInput
              label="טוקן (מתקדם/דב)"
              placeholder="Bearer/Basic"
              type="password"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
            />
          </Collapse>
          <Button type="submit" color="cyan" radius="md" fullWidth>
            המשך וסנכרן
          </Button>
          <Button type="button" variant="light" radius="md" fullWidth onClick={handleGoogle}>
            כניסה עם Google
          </Button>
          <Button type="button" variant="subtle" radius="md" fullWidth onClick={() => setShowAdvanced((v) => !v)}>
            {showAdvanced ? "הסתר מתקדם" : "שדות מתקדמים (דב)"}
          </Button>
          {!oauthReady && (
            <Text size="xs" c="yellow" ta="center">
              OAuth לא הוגדר (VITE_GOOGLE_OAUTH_URL). השתמש בלוגין הידני או הוסף כתובת OAuth.
            </Text>
          )}
        </Stack>
        <Text size="xs" c="dimmed" ta="center" mt="xs">
          סנכרון ינסה לרוץ אוטומטית לאחר הכניסה. ניתן להעלות קובץ טפסים ידנית במקרה של כשל.
        </Text>
      </Paper>
    </div>
  );
}
