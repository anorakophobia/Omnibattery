"""ha-install only: an entry at this fork's earlier v18 still gets upstream's v18 (offgrid threshold)."""
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.omnibattery import async_migrate_entry
from custom_components.omnibattery.const import CONF_ROUND_TRIP_EFFICIENCY


class _Entries:
    def async_update_entry(self, entry, **changes):
        for key, value in changes.items():
            setattr(entry, key, value)


async def _migrate(version, data):
    removed = []
    registered = [
        SimpleNamespace(domain="number", unique_id="x_backup_offgrid_threshold", entity_id="number.offgrid"),
        SimpleNamespace(domain="number", unique_id="x_max_soc", entity_id="number.max_soc"),
    ]
    registry = SimpleNamespace(async_get_entity_id=lambda *a: None, async_remove=removed.append)
    hass = SimpleNamespace(config_entries=_Entries())
    entry = SimpleNamespace(version=version, entry_id="entry", data=dict(data))
    with patch.multiple(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: registry,
        async_entries_for_config_entry=lambda reg, entry_id: registered,
    ):
        assert await async_migrate_entry(hass, entry) is True
    return entry, removed


async def test_a_fork_v18_entry_drops_the_offgrid_threshold_and_its_entity():
    entry, removed = await _migrate(18, {
        "batteries": [{"name": "a", "backup_offgrid_threshold": 50}, {"name": "b"}],
    })
    assert entry.version == 19
    assert entry.data["batteries"] == [{"name": "a"}, {"name": "b"}]
    assert removed == ["number.offgrid"]


async def test_a_fork_v18_entry_keeps_a_fixed_round_trip_efficiency_of_085():
    # The round-trip step ran as v18 on ha.41: a 0.85 stored since is a fixed value.
    entry, _ = await _migrate(18, {CONF_ROUND_TRIP_EFFICIENCY: 0.85, "batteries": []})
    assert entry.version == 19
    assert entry.data[CONF_ROUND_TRIP_EFFICIENCY] == 0.85


async def test_an_entry_below_v18_still_drops_the_sentinel_085():
    entry, _ = await _migrate(17, {CONF_ROUND_TRIP_EFFICIENCY: 0.85, "batteries": []})
    assert entry.version == 19
    assert CONF_ROUND_TRIP_EFFICIENCY not in entry.data
