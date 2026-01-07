from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ConfigDict


class AliasConfig(BaseModel):
    aliases: List[str] = Field(default_factory=list)


class FamilyConfig(BaseModel):
    aliases: List[str] = Field(default_factory=list)
    extras: List[str] = Field(default_factory=list)


class PlatoonInferenceConfig(BaseModel):
    file_names: List[Dict[str, str]] = Field(default_factory=list)
    sheet_ids: Dict[str, str] = Field(default_factory=dict)


class FormFieldConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tank_id: AliasConfig = Field(
        default_factory=lambda: AliasConfig(
            aliases=["צ טנק", "צ' טנק", "מספר צלימו", "מספר צלי"]
        )
    )
    timestamp: AliasConfig = Field(default_factory=lambda: AliasConfig(aliases=["חותמת זמן", "תאריך"]))
    commander: AliasConfig = Field(
        default_factory=lambda: AliasConfig(aliases=["שם המטק", 'שם המט\"ק', "שם מפקד"])
    )
    platoon_inference: PlatoonInferenceConfig = Field(default_factory=PlatoonInferenceConfig)
    families: Dict[str, FamilyConfig] = Field(default_factory=dict)


class FieldConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    gap_tokens: List[str] = Field(default_factory=lambda: ["חוסר", "בלאי", "אין"])
    ok_tokens: List[str] = Field(default_factory=lambda: ["קיים", "יש", "תקין"])
    form: FormFieldConfig = Field(default_factory=FormFieldConfig)


def _default_families() -> Dict[str, FamilyConfig]:
    """
    Provide a baseline set of family alias rules so the system remains tolerant
    even when config/fields.yaml is missing or partial.
    """
    return {
        "zivud": FamilyConfig(
            aliases=["דוח זיווד [*]"],
            extras=[
                "שרשרת גרירה",
                "שאקל 25 טון",
                "שאקל 5 טון",
                "שאקל קרנף",
                'שיני חזיר\\נג"ח',
                "מעיל רוח",
                "מטען ניתוק זחל",
                "נונל",
            ],
        ),
        "ammo": FamilyConfig(
            aliases=[
                "ברוסי מאג",
                "ברוסי 05",
                "חלול",
                "חצב",
                "כלנית",
                "חץ",
                "רימוני רסס",
                "רימוני עשן",
                "מרגמה נפיץ",
                "מרגמה תאורה",
            ]
        ),
        "means": FamilyConfig(aliases=["סטטוס ציוד קשר [*]"]),
        "issues": FamilyConfig(
            aliases=[
                "מאג * מה הצ",
                "05 * מה הצ",
                'אמר"ל * מה הצ',
                "משקפת * מה הצ",
                "מצפן * מה הצ",
                "מדיה* מה הצ",
                "NFC * מה הצ",
                "אולר * מה הצ",
                "בורוסייט * מה הצ",
                "מבן * מה הצ",
                "CF * מה הצ",
                "מ.ק* מה הצ",
                "תקלות*",
            ]
        ),
        "parsim": FamilyConfig(aliases=["פערי צלמים*"]),
    }


def load_field_config(path: Optional[Path] = None) -> FieldConfig:
    """
    Load header/alias mapping configuration from YAML with safe defaults.
    """
    file_path = path or Path("config/fields.yaml")
    if not file_path.exists():
        cfg = FieldConfig()
        cfg.form.families = _default_families()
        return cfg

    with open(file_path, "r") as f:
        data = yaml.safe_load(f) or {}

    loaded = FieldConfig.model_validate(data)
    merged_families = _default_families()
    merged_families.update(loaded.form.families)
    loaded.form.families = merged_families
    return loaded


# Singleton-style loaded config for convenience
field_config = load_field_config()
