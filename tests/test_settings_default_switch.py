"""A "use default" switch beside a setting slider.

A number entity cannot be cleared from the UI, so once the slider was moved
a setting kept its stored value for good. A setting whose definition has
``default_switch`` gets a switch: ON means no stored value, so the setting is
its default and follows it (the solar safety margin, 5 % of the fleet, through
battery changes). OFF stores the value in use. Moving the slider stores a
value, which reads as OFF. The panel shows a "default" tag on the slider.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

from custom_components.omnibattery.const import (
    CONFIG_NUMBER_DEFINITIONS,
    CONF_PREDICTIVE_SAFETY_MARGIN_KWH,
)
from custom_components.omnibattery.number import MarstekConfigNumberEntity
from custom_components.omnibattery.switch import ConfigNumberDefaultSwitch

DOMAIN = "omnibattery"
PANEL = Path("custom_components/omnibattery/frontend/marstek-panel.js")
MARGIN_DEF = next(
    d for d in CONFIG_NUMBER_DEFINITIONS if d["key"] == CONF_PREDICTIVE_SAFETY_MARGIN_KWH
)
# A Marstek reads its capacity, a Zendure at 0 detects it: 13.28 kWh -> 0.66.
FLEET = {"batteries": [{"name": "Venus"}, {"name": "SolarFlow", "battery_capacity_kwh": 0}]}


class _Entries:
    def __init__(self):
        self.updates = 0

    def async_update_entry(self, entry, *, data):
        entry.data = data
        self.updates += 1


def _setup(data):
    controller = SimpleNamespace(
        _reported_battery_capacity_kwh=lambda: {"Venus": 5.12, "SolarFlow": 8.16},
        reloads=0,
    )
    controller.update_pd_parameters = lambda: setattr(controller, "reloads", controller.reloads + 1)
    entry = SimpleNamespace(data=dict(data), entry_id="entry")
    hass = SimpleNamespace(
        data={DOMAIN: {"entry": {"controller": controller}}},
        config_entries=_Entries(),
    )
    switch = ConfigNumberDefaultSwitch(hass, entry, controller, MARGIN_DEF)
    switch.async_write_ha_state = lambda: None
    slider = MarstekConfigNumberEntity(hass, entry, MARGIN_DEF)
    return hass, entry, controller, switch, slider


def test_the_margin_has_a_default_switch():
    assert MARGIN_DEF.get("default_switch") is True


def test_without_a_stored_value_the_setting_follows_its_default():
    _hass, _entry, _controller, switch, slider = _setup(FLEET)

    assert switch.is_on
    assert slider.native_value == 0.66
    assert slider.extra_state_attributes == {"uses_default": True}


def test_a_stored_value_reads_as_off():
    _hass, _entry, _controller, switch, slider = _setup(
        {**FLEET, CONF_PREDICTIVE_SAFETY_MARGIN_KWH: 2.0}
    )

    assert not switch.is_on
    assert slider.native_value == 2.0
    assert slider.extra_state_attributes == {"uses_default": False}


def test_turning_it_on_drops_the_stored_value():
    hass, entry, controller, switch, slider = _setup(
        {**FLEET, CONF_PREDICTIVE_SAFETY_MARGIN_KWH: 2.0}
    )

    asyncio.run(switch.async_turn_on())

    assert CONF_PREDICTIVE_SAFETY_MARGIN_KWH not in entry.data
    assert switch.is_on
    assert slider.native_value == 0.66
    assert controller.reloads == 1


def test_turning_it_off_fixes_the_value_in_use():
    _hass, entry, controller, switch, slider = _setup(FLEET)

    asyncio.run(switch.async_turn_off())

    assert entry.data[CONF_PREDICTIVE_SAFETY_MARGIN_KWH] == 0.66
    assert not switch.is_on
    assert slider.native_value == 0.66
    assert controller.reloads == 1


def test_a_setting_without_the_flag_has_no_attribute():
    other = next(d for d in CONFIG_NUMBER_DEFINITIONS if not d.get("default_switch"))
    slider = MarstekConfigNumberEntity(None, SimpleNamespace(data={}, entry_id="e"), other)

    assert slider.extra_state_attributes is None


def test_the_panel_shows_the_switch_and_a_default_tag():
    panel = PANEL.read_text(encoding="utf-8")

    switch_row = panel.index('key: "predictive_safety_margin_kwh_use_default", domain: "switch"')
    slider_row = panel.index('key: "predictive_safety_margin_kwh", lk: "itemSolarSafety"')
    assert switch_row < slider_row
    assert "a.uses_default === true" in panel
    assert 'this._t("tagDefault")' in panel
    # label, tag and help in every panel language
    assert panel.count("itemSolarSafetyDefault:") == 6
    assert panel.count("tagDefault:") == 6
    assert panel.count("predictive_safety_margin_kwh_use_default:") == 6
