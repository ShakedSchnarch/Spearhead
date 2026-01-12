import { useState } from "react";
import { Badge, Button, Group, Paper, Text, Title, Collapse, SegmentedControl, Center } from "@mantine/core";
import { notifications } from "@mantine/notifications";

export function LoginOverlay({ onLogin, defaultPlatoon = "battalion", oauthReady, oauthUrl, logos }) {
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(defaultPlatoon || "battalion");
  const [showDev, setShowDev] = useState(false);

  // Dynamic logo based on selection
  const logoSrc = selected === "battalion" ? logos?.romach : (logos?.[selected] || logos?.romach);

  const handleGoogle = () => {
    setLoading(true);
    const platoon = selected === "battalion" ? "" : selected;
    const viewMode = selected === "battalion" ? "battalion" : "platoon";

    if (oauthUrl) {
      try {
        const url = new URL(oauthUrl);
        const statePayload = {
          platoon, 
          viewMode,
          ts: Date.now(),
        };
        url.searchParams.set("state", encodeURIComponent(JSON.stringify(statePayload)));
        window.location.href = url.toString();
        return;
      } catch {
        notifications.show({
          title: "שגיאת OAuth",
          message: "כתובת ה-OAuth אינה תקינה.",
          color: "red",
        });
        setLoading(false);
      }
    } else {
      // Dev Fallback
      onLogin({ platoon, email: "guest@spearhead.local", token: "", viewMode });
    }
  };

  return (
    <div className="login-overlay">
      <Paper shadow="xl" radius="lg" className="login-card" withBorder style={{ maxWidth: 420, margin: "auto", padding: "2rem" }}>
        
        {/* Header Badge */}
        <Group justify="center" align="center" mb="lg">
          <Badge size="lg" color="teal" radius="xl" variant="gradient" gradient={{ from: "green", to: "teal" }}>
            קצה הרומח · Spearhead
          </Badge>
        </Group>
        
        {/* Dynamic Logo */}
        <div className="login-logo" style={{ textAlign: "center", marginBottom: "1.5rem", height: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
          {logoSrc && (
            <img 
              src={logoSrc} 
              alt={selected} 
              style={{ 
                maxHeight: "100%", 
                maxWidth: "100%", 
                objectFit: "contain",
                filter: "drop-shadow(0px 4px 6px rgba(0,0,0,0.3))"
              }} 
            />
          )}
        </div>

        <Title order={2} ta="center" mb="xs" style={{ fontFamily: "kumbh sans, sans-serif" }}>
          ברוכים הבאים
        </Title>
        <Text ta="center" c="dimmed" size="sm" mb="xl">
          בחר יחידה והתחבר למערכת
        </Text>

        {/* Unit Selection */}
        <SegmentedControl
          fullWidth
          radius="md"
          size="md"
          mb="xl"
          value={selected}
          onChange={setSelected}
          data={[
            { label: "גדוד (רומח)", value: "battalion" },
            { label: "כפיר", value: "כפיר" },
            { label: "סופה", value: "סופה" },
            { label: "מחץ", value: "מחץ" },
          ]}
          styles={{
            root: { backgroundColor: "rgba(0, 0, 0, 0.2)" }
          }}
        />

        {/* Main Action */}
        <Button 
          size="lg" 
          color="cyan" 
          radius="md" 
          fullWidth 
          onClick={handleGoogle} 
          loading={loading}
          leftSection={<span style={{ fontSize: "1.2em", fontWeight: "bold" }}>G</span>}
        >
          {selected === "battalion" ? "התחבר כגדוד" : `התחבר כ${selected}`}
        </Button>

        {/* Dev Footer */}
        <Center mt="xl">
            <Text size="xs" c="dimmed" style={{ cursor: "pointer", opacity: 0.5 }} onClick={() => setShowDev(!showDev)}>
            v1.0.0
            </Text>
        </Center>
        
        <Collapse in={showDev}>
            <Text size="xs" c="dimmed" ta="center" mt="xs">
                Dev Mode: No OAuth? Click above to bypass.
            </Text>
        </Collapse>
      </Paper>
    </div>
  );
}
