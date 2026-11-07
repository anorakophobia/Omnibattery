"""Every setting tooltip ends with its default, in all six panel languages.

The rule (AGENTS.md, "A setting is more than its entity"): a setting's tooltip
in SYS_HELP ends with one sentence stating its default, "Default: …" with the
label of each language. The value is checked against the code's DEFAULT_*
constant where there is one, so a changed default cannot drift from its
tooltip. Status rows and buttons get no such sentence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from custom_components.omnibattery.const import (
    DEFAULT_DISCHARGE_RESERVE_MIN_SAVING,
    DEFAULT_NEGATIVE_INJECTION_THRESHOLD,
    DEFAULT_PREDICTIVE_MIN_SOC_FLOOR,
    DEFAULT_PREDISCHARGE_RESERVE_SOC,
    DEFAULT_SURPLUS_HOLD_MIN_SAVING,
)

PANEL = Path("custom_components/omnibattery/frontend/marstek-panel.js")
LANGS = ["en", "es", "ca", "de", "fr", "nl"]
LABEL = {
    "en": "Default:",
    "es": "Por defecto:",
    "ca": "Per defecte:",
    "de": "Standard:",
    "fr": "Par défaut :",
    "nl": "Standaard:",
}


def _per_kwh(value):
    return f"{value:.2f} per kWh"


def _pct(value):
    return f"{value:g} %"


# key -> the English default sentence's value. Numbers come from the code.
DEFAULTS = {
    # predictive charging card
    "predictive_charging": "off",
    "predictive_charging_notifications": "on",
    "predictive_safety_margin_kwh_use_default": "on",
    "predictive_safety_margin_kwh": "5 % of the total battery capacity",
    "min_soc_floor_enabled": "off",
    "predictive_min_soc_floor": _pct(DEFAULT_PREDICTIVE_MIN_SOC_FLOOR),
    "max_price_threshold_enabled": "off (automatic)",
    "max_price_threshold": "not set (automatic)",
    "min_arbitrage_margin": "not set (off)",
    "round_trip_efficiency_use_measured": "on",
    "round_trip_efficiency": "measured (0.85 until a battery has 50 cycles)",
    "negative_price_charging": "off",
    "price_discharge_control": "off",
    "discharge_price_threshold_enabled": "off (automatic)",
    "discharge_price_threshold": "not set (automatic)",
    "discharge_reserve": "off",
    "discharge_reserve_min_saving": _per_kwh(DEFAULT_DISCHARGE_RESERVE_MIN_SAVING),
    "high_price_sale": "off",
    "surplus_price_hold": "off",
    "surplus_hold_min_saving": _per_kwh(DEFAULT_SURPLUS_HOLD_MIN_SAVING),
    "smart_predischarge": "off",
    "negative_injection_threshold": _per_kwh(DEFAULT_NEGATIVE_INJECTION_THRESHOLD),
    "predischarge_reserve_soc": _pct(DEFAULT_PREDISCHARGE_RESERVE_SOC),
}

NO_DEFAULT = (
    "curtailment_status",
    "surplus_price_hold_status",
    "high_price_discharge_status",
    "discharge_reserve_status",
    "reevaluate_dynamic_pricing",
)


def _help(lang):
    panel = PANEL.read_text(encoding="utf-8")
    start = panel.index("const SYS_HELP = {")
    end = panel.index("\n};", start)
    blocks = [panel.index(f"\n  {code}: {{", start, end) for code in LANGS]
    i = LANGS.index(lang)
    block = panel[blocks[i] : blocks[i + 1] if i + 1 < len(LANGS) else end]
    entries = {}
    for m in re.finditer(r'\n\s+(\w+): ("(?:[^"\\]|\\.)*")', block):
        entries[m.group(1)] = json.loads(m.group(2))
    return entries


@pytest.mark.parametrize("key", sorted(DEFAULTS))
def test_the_english_tooltip_states_the_code_s_default(key):
    assert _help("en")[key].endswith(f"Default: {DEFAULTS[key]}.")


@pytest.mark.parametrize("lang", LANGS)
def test_every_language_ends_with_one_default_sentence(lang):
    entries = _help(lang)
    for key in DEFAULTS:
        text = entries[key]
        tail = text.rsplit(". ", 1)[-1]
        assert tail.startswith(LABEL[lang]), (lang, key, tail)
        assert text.count(LABEL[lang]) == 1, (lang, key)


@pytest.mark.parametrize("lang", LANGS)
def test_status_rows_and_buttons_state_no_default(lang):
    entries = _help(lang)
    for key in NO_DEFAULT:
        assert LABEL[lang] not in entries[key], (lang, key)
