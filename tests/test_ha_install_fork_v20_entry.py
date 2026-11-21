"""ha-install only: an entry at this fork's earlier v20 still gets upstream's v20 (solar safety margin as a %)."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from custom_components.omnibattery import async_migrate_entry
from custom_components.omnibattery.const import (
    CONF_PREDICTIVE_SAFETY_MARGIN_KWH,
    CONF_PREDICTIVE_SAFETY_MARGIN_PCT,
    CONF_ROUND_TRIP_EFFICIENCY,
)

KWH_ENTITY = "number.omnibattery_predictive_safety_margin_kwh"


class _Entries:
    def async_update_entry(self, entry, **changes):
        for key, value in changes.items():
            setattr(entry, key, value)


async def _migrate(version, data, has_entity=True):
    removed = []

    def get_entity_id(domain, _platform, unique_id):
        if has_entity and domain == "number" and unique_id.endswith("_" + CONF_PREDICTIVE_SAFETY_MARGIN_KWH):
            return KWH_ENTITY
        return None

    registry = SimpleNamespace(async_get_entity_id=get_entity_id, async_remove=removed.append)
    hass = SimpleNamespace(config_entries=_Entries())
    entry = SimpleNamespace(version=version, entry_id="entry", data=dict(data), options={})
    with patch.multiple(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: registry,
        async_entries_for_config_entry=lambda reg, entry_id: [],
    ):
        assert await async_migrate_entry(hass, entry) is True
    return entry, removed


@pytest.mark.parametrize(
    "stored, expected",
    [(0.0, 0.0), (2.5, None), (None, None)],
    ids=["zero", "hand_set_value", "never_set"],
)
async def test_a_fork_v20_entry_turns_the_kwh_margin_into_a_pct(stored, expected):
    data = {"batteries": []}
    if stored is not None:
        data[CONF_PREDICTIVE_SAFETY_MARGIN_KWH] = stored

    entry, removed = await _migrate(20, data)

    assert entry.version == 21
    assert CONF_PREDICTIVE_SAFETY_MARGIN_KWH not in entry.data
    assert entry.data.get(CONF_PREDICTIVE_SAFETY_MARGIN_PCT) == expected
    assert removed == [KWH_ENTITY]


async def test_a_fork_v20_entry_keeps_a_pct_already_set():
    # Running the step again for an entry that already has the % leaves it.
    entry, removed = await _migrate(
        20, {"batteries": [], CONF_PREDICTIVE_SAFETY_MARGIN_PCT: 15.0}, has_entity=False
    )
    assert entry.version == 21
    assert entry.data[CONF_PREDICTIVE_SAFETY_MARGIN_PCT] == 15.0 and removed == []


async def test_a_fork_v20_entry_keeps_a_fixed_round_trip_efficiency_of_085():
    # The round-trip step ran as v20 on ha.43: a 0.85 stored since is a fixed value.
    entry, _ = await _migrate(20, {CONF_ROUND_TRIP_EFFICIENCY: 0.85, "batteries": []})
    assert entry.version == 21
    assert entry.data[CONF_ROUND_TRIP_EFFICIENCY] == 0.85


async def test_a_current_entry_is_left_alone():
    entry, removed = await _migrate(21, {CONF_PREDICTIVE_SAFETY_MARGIN_KWH: 2.5, "batteries": []})
    assert entry.version == 21 and entry.data[CONF_PREDICTIVE_SAFETY_MARGIN_KWH] == 2.5 and removed == []
