import { useState } from "react";
import { Button, Card, FileInput, Text } from "@mantine/core";

export function UploadCard({ title, onUpload, disabled }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState("");

  const handleUpload = async () => {
    if (!file) {
      setResult("בחר/י קובץ");
      return;
    }
    setResult("מעלה...");
    try {
      const inserted = await onUpload(file);
      setResult(`הוכנסו ${inserted}`);
    } catch (err) {
      setResult(`שגיאה: ${err.message || err}`);
    }
  };

  return (
    <Card withBorder shadow="md" padding="md" radius="md">
      <Text fw={700} mb="xs">
        {title}
      </Text>
      <FileInput
        value={file}
        onChange={setFile}
        disabled={disabled}
        accept=".xlsx"
        placeholder="בחר/י קובץ xlsx"
      />
      <Button fullWidth mt="sm" radius="md" onClick={handleUpload} disabled={disabled} loading={disabled}>
        העלה
      </Button>
      {result && (
        <Text size="xs" mt="xs" c="dimmed">
          {result}
        </Text>
      )}
    </Card>
  );
}
