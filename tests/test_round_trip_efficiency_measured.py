"""Round-trip efficiency: "use measured" instead of a hidden 0.85.

A stored 0.85 (the default) used to mean "use the measured value": the slider
showed 0.85 while about 0.82 was used, and a fixed 0.85 could not be set. Now
no stored value means measured (its "use measured" switch on), any stored
value is used as given, and the v16 -> v17 migration drops a stored 0.85 so
existing installs keep behaving as before.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.omnibattery import async_migrate_entry
from custom_components.omnibattery.const import CONF_ROUND_TRIP_EFFICIENCY
from custom_components.omnibattery.energy import effective_round_trip_efficiency
from custom_components.omnibattery.number import MarstekArbitrageNumber
from custom_components.omnibattery.switch import RoundTripEfficiencyMeasuredSwitch

DOMAIN = "omnibattery"
PANEL = Path("custom_components/omnibattery/frontend/marstek-panel.js")


def _battery(charged, discharged, capacity):
    return SimpleNamespace(
        data={
            "total_charging_energy": charged,
            "total_discharging_energy": discharged,
            "battery_total_energy": capacity,
        },
        capabilities=SimpleNamespace(independent_power_planes=False),
    )


# A Marstek with enough cycles (81.6 %), a Zendure without (excluded).
FLEET = [_battery(3442.8, 2808.0, 5.12), _battery(326.9, 283.6, 8.16)]


def _controller(stored=None):
    return SimpleNamespace(round_trip_efficiency=stored, coordinators=FLEET)


def test_no_stored_value_means_measured():
    value, source = effective_round_trip_efficiency(_controller())

    assert source == "measured"
    assert round(value, 4) == round(2808.0 / 3442.8, 4)


def test_a_stored_0_85_is_used_as_given():
    assert effective_round_trip_efficiency(_controller(0.85)) == (0.85, "configured")


class _Entries:
    def async_update_entry(self, entry, *, data, version=None, title=None):
        entry.data = data
        if version is not None:
            entry.version = version


def _entities(data):
    controller = SimpleNamespace(
        round_trip_efficiency=data.get(CONF_ROUND_TRIP_EFFICIENCY),
        coordinators=FLEET,
        reloads=0,
    )

    def reload():
        controller.round_trip_efficiency = entry.data.get(CONF_ROUND_TRIP_EFFICIENCY)
        controller.reloads += 1

    controller.update_pd_parameters = reload
    entry = SimpleNamespace(data=dict(data), entry_id="entry")
    hass = SimpleNamespace(data={DOMAIN: {"entry": {"controller": controller}}}, config_entries=_Entries())
    slider = MarstekArbitrageNumber(hass, entry, "efficiency")
    switch = RoundTripEfficiencyMeasuredSwitch(hass, entry, controller)
    switch.async_write_ha_state = lambda: None
    return entry, slider, switch


def test_the_slider_shows_the_measured_value_in_use():
    _entry, slider, switch = _entities({})

    assert switch.is_on
    assert slider.native_value == round(2808.0 / 3442.8, 4)
    assert slider.extra_state_attributes == {"uses_default": True, "default_kind": "measured"}


async def test_turning_it_off_fixes_the_value_in_use():
    entry, slider, switch = _entities({})

    await switch.async_turn_off()

    assert entry.data[CONF_ROUND_TRIP_EFFICIENCY] == 0.82
    assert not switch.is_on
    assert slider.native_value == 0.82
    assert slider.extra_state_attributes["uses_default"] is False


async def test_turning_it_on_drops_a_fixed_value():
    entry, slider, switch = _entities({CONF_ROUND_TRIP_EFFICIENCY: 0.85})

    await switch.async_turn_on()

    assert CONF_ROUND_TRIP_EFFICIENCY not in entry.data
    assert slider.extra_state_attributes["default_kind"] == "measured"


def _no_registry():
    return patch.multiple(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: SimpleNamespace(
            async_get_entity_id=lambda *args: None,
            async_remove=lambda *args: None,
        ),
        async_entries_for_config_entry=lambda reg, entry_id: [],
    )


async def _migrate(data):
    hass = SimpleNamespace(config_entries=_Entries())
    entry = SimpleNamespace(version=16, entry_id="entry", data=dict(data))
    with _no_registry():
        assert await async_migrate_entry(hass, entry) is True
    assert entry.version == 17
    return entry.data


async def test_the_migration_turns_the_hidden_0_85_into_measured():
    assert CONF_ROUND_TRIP_EFFICIENCY not in await _migrate({CONF_ROUND_TRIP_EFFICIENCY: 0.85})


async def test_the_migration_keeps_any_other_value():
    assert (await _migrate({CONF_ROUND_TRIP_EFFICIENCY: 0.9}))[CONF_ROUND_TRIP_EFFICIENCY] == 0.9


def test_the_panel_shows_the_switch_and_a_measured_tag():
    panel = PANEL.read_text(encoding="utf-8")

    switch_row = panel.index('key: "round_trip_efficiency_use_measured", domain: "switch"')
    slider_row = panel.index('key: "round_trip_efficiency", lk: "itemRoundTripEfficiency"')
    # The value first, its default switch below it as a modifier: a switch
    # above the slider reads as the feature's on/off.
    assert slider_row < switch_row
    assert 'a.default_kind === "measured" ? "tagMeasured" : "tagDefault"' in panel
    assert panel.count("itemRoundTripMeasured:") == 6
    assert panel.count("tagMeasured:") == 6
    assert panel.count("round_trip_efficiency_use_measured:") == 6


def test_an_unset_arbitrage_margin_reads_as_0_so_the_panel_shows_it():
    # unknown would be dropped by the panel; 0 and unset both mean off
    entry = SimpleNamespace(data={}, entry_id="entry")
    assert MarstekArbitrageNumber(SimpleNamespace(data={}), entry, "margin").native_value == 0.0
    entry.data = {"min_arbitrage_margin": 0.05}
    assert MarstekArbitrageNumber(SimpleNamespace(data={}), entry, "margin").native_value == 0.05
