import pandas as pd
from datetime import datetime

# Define headers exactly as seen in the "good" empty file
data = {
    "חותמת זמן": [datetime.now(), datetime.now()],
    "בחר פלוגה": ["פלוגה א", "פלוגה ב"],
    "מספר צלימו": ["200100", "200101"],
    "סטטוס לרק\"ם": ["תקין", "תקול"],
    "מיקום": ["שטח כינוס", "גבול הצפון"],
    "תאר את תקלת הטנ\"א": ["NaN", "מנוע מתחמם"],
    "מאג 1: מה הצ', מיקום, תקין\\תקול ומה התקלה": ["תקין", "תקול"],
    "05: מה הצ', מיקום, תקין\\תקול ומה התקלה": ["חסר", "תקין"]
}

df = pd.DataFrame(data)
df.to_excel("../mvp/files/mock_kfir.xlsx", index=False)
print("Generated ../mvp/files/mock_kfir.xlsx")
