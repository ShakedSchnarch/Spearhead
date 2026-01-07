import os
import random
from typing import Dict, Any, List
from iron_view.domain.models import BattalionData

class LLMClient:
    """
    Client for Generative AI (The 'Creative' Brain).
    CURRENTLY SIMULATED to provide high-quality insights without an API key.
    """
    
    def generate_battalion_insight(self, data: BattalionData) -> Dict[str, Any]:
        """
        Generates a strategic insight for the Intelligence Feed.
        """
        # In a real implementation, this would build a prompt with the BattalionData JSON
        # and send it to OpenAI/Gemini.
        
        # SIMULATION: Return randomized but context-aware insights
        insights = [
            {
                "type": "TREND",
                "title": "מגמת שחיקה מואצת",
                "icon": "fa-arrow-trend-down",
                "color": "amber", # Tailwind color name
                "text": "זוהתה עלייה של 15% בדיווחי 'מנוע מתחמם' בפלוגת להב בהשוואה לשבוע שעבר.",
                "action": "מומלץ לבצע מסדר מנועים יזום ב-48 שעות הקרובות."
            },
            {
                "type": "PREDICTION",
                "title": "תחזית לוגיסטית",
                "icon": "fa-warehouse",
                "color": "blue",
                "text": "צפי למחסור בשמן 10W תוך 3 ימים על בסיס קצב הדיווחים הנוכחי.",
                "action": "יש להקדים אספקה מגדוד הדרכה."
            },
            {
                "type": "ANOMALY",
                "title": "חריגת אמינות",
                "icon": "fa-circle-exclamation",
                "color": "rose",
                "text": "נמצאו 3 דיווחים זהים לחלוטין (Copy-Paste) במחלקת חוד 2.",
                "action": "נדרש בירור מול מפקד המחלקה."
            }
        ]
        
        # Return a random selection for the demo
        return random.sample(insights, 2)
