"""ha-install only: an entry at this fork's earlier v19 still gets upstream's v19 (Discharge Reserve removed)."""
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.omnibattery import async_migrate_entry
from custom_components.omnibattery.const import CONF_ROUND_TRIP_EFFICIENCY

GONE = ("discharge_reserve_enabled", "discharge_reserve_min_saving")


class _Entries:
    def async_update_entry(self, entry, **changes):
        for key, value in changes.items():
            setattr(entry, key, value)


async def _migrate(version, data, options=None):
    removed = []
    ids = {
        ("switch", "discharge_reserve"): "switch.omnibattery_discharge_reserve",
        ("number", "discharge_reserve_min_saving"): "number.omnibattery_discharge_reserve_min_saving",
    }

    def get_entity_id(domain, _platform, unique_id):
        for (dom, key), entity_id in ids.items():
            if dom == domain and unique_id.endswith("_" + key):
                return entity_id
        return None

    registry = SimpleNamespace(async_get_entity_id=get_entity_id, async_remove=removed.append)
    hass = SimpleNamespace(config_entries=_Entries())
    entry = SimpleNamespace(version=version, entry_id="entry", data=dict(data), options=dict(options or {}))
    with patch.multiple(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: registry,
        async_entries_for_config_entry=lambda reg, entry_id: [],
    ):
        assert await async_migrate_entry(hass, entry) is True
    return entry, removed


async def test_a_fork_v19_entry_drops_the_discharge_reserve_keys_and_entities():
    entry, removed = await _migrate(
        19,
        {"batteries": [], GONE[0]: True, GONE[1]: 0.0, "surplus_hold_min_saving": 0.02},
        {GONE[1]: 0.02, "other": 1},
    )
    assert entry.version == 20
    assert not set(GONE) & set(entry.data) and not set(GONE) & set(entry.options)
    assert entry.data["surplus_hold_min_saving"] == 0.02 and entry.options == {"other": 1}
    assert sorted(removed) == [
        "number.omnibattery_discharge_reserve_min_saving",
        "switch.omnibattery_discharge_reserve",
    ]


async def test_a_fork_v19_entry_keeps_a_fixed_round_trip_efficiency_of_085():
    # The round-trip step ran as v19 on ha.42: a 0.85 stored since is a fixed value.
    entry, _ = await _migrate(19, {CONF_ROUND_TRIP_EFFICIENCY: 0.85, "batteries": []})
    assert entry.version == 20
    assert entry.data[CONF_ROUND_TRIP_EFFICIENCY] == 0.85


async def test_a_current_entry_is_left_alone():
    entry, removed = await _migrate(20, {GONE[0]: True, "batteries": []})
    assert entry.version == 20 and entry.data[GONE[0]] is True and removed == []
