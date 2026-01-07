from pathlib import Path

from iron_view.data.adapters import (
    PlatoonLoadoutAdapter,
    BattalionSummaryAdapter,
    FormResponsesAdapter,
)


BASE = Path(__file__).resolve().parents[1]


def test_platoon_loadout_zivud_and_ammo():
    path = BASE / "docs/Files/דוחות פלוגת כפיר (1).xlsx"
    records = PlatoonLoadoutAdapter.load(path)
    assert records, "No records parsed from platoon loadout file"

    zivud_match = [
        r for r in records
        if r.section == "zivud" and r.item == "חבל פריסה" and r.column == "צ'636"
    ]
    assert zivud_match, "Expected zivud record for צ'636 חבל פריסה"
    assert zivud_match[0].value == 1.0

    ammo_match = [
        r for r in records
        if r.section == "ammo" and r.item == "חלול"
    ]
    assert ammo_match, "Expected ammo record for חלול"
    # Values should be numeric; accept float/int
    assert any(float(m.value) > 0 for m in ammo_match)


def test_battalion_summary_parses_gaps():
    path = BASE / "docs/Files/מסמך דוחות גדודי (1).xlsx"
    records = BattalionSummaryAdapter.load(path)
    assert records, "No records parsed from battalion summary"

    gap = [
        r for r in records
        if r.section == "summary_zivud" and r.item == "חבל פריסה" and "סופה" in r.column
    ]
    assert gap, "Expected summary gap for חבל פריסה (סופה)"
    assert "בלאי" in str(gap[0].value)


def test_form_responses_status_present():
    path = BASE / "docs/Files/טופס דוחות סמפ כפיר. (תגובות) (1).xlsx"
    responses = FormResponsesAdapter.load(path)
    assert responses, "No responses parsed from form export"
    first = responses[0]
    assert first.fields.get("דוח זיווד [חבל פריסה]") == "קיים"
