import { Badge, Button, Group, Text, Title } from "@mantine/core";

export function HeroHeader({ user, viewMode, platoon, health, syncEnabled, onLogout, logoSrc }) {
  return (
    <header className="topbar">
      <div className="hero">
        <div className="hero-text">
          <Badge color="teal" size="lg" radius="md" variant="gradient" gradient={{ from: "green", to: "teal" }}>
            קצה הרומח · רומח 75
          </Badge>
          <Title order={2} mt="xs">
            דשבורד מוכנות
          </Title>
          <Text className="muted">סקירה פלוגתית/גדודית, סנכרון מגוגל, כיסוי ואנומליות.</Text>
          <Group gap="xs" mt="sm" wrap="wrap" className="header-actions">
            <Badge variant="light" color="gray">
              משתמש: {user?.email || "לא צוין"}
            </Badge>
            <Badge variant="light" color="cyan">
              מצב: {viewMode === "battalion" ? "גדוד" : "פלוגה"} {platoon ? `· ${platoon}` : ""}
            </Badge>
            <Badge variant="outline" color="green">
              {health}
            </Badge>
            <Badge variant="outline" color={syncEnabled ? "teal" : "gray"}>
              {syncEnabled ? "Google Sync פעיל" : "Google Sync כבוי"}
            </Badge>
            <Button variant="light" size="xs" color="red" onClick={onLogout}>
              התנתק
            </Button>
          </Group>
        </div>
        {logoSrc && <img src={logoSrc} alt={viewMode === "battalion" ? "רומח 75" : platoon} className="hero-logo" />}
      </div>
    </header>
  );
}
