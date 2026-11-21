"""ha-install only: an entry at this fork's earlier v17 still gets upstream's v17 (#506)."""
from types import SimpleNamespace
from unittest.mock import patch

from custom_components.omnibattery import async_migrate_entry
from custom_components.omnibattery.const import (
    CONF_CAPACITY_PROTECTION_ENABLED,
    CONF_MAX_CONTRACTED_POWER,
)


class _Entries:
    def async_update_entry(self, entry, **changes):
        for key, value in changes.items():
            setattr(entry, key, value)


async def _migrate(version, data):
    removed = []
    registry = SimpleNamespace(
        async_get_entity_id=lambda domain, platform, uid: "number.limit" if uid.endswith("capacity_protection_limit") else None,
        async_remove=removed.append,
    )
    hass = SimpleNamespace(config_entries=_Entries())
    entry = SimpleNamespace(version=version, entry_id="entry", data=dict(data), options={})
    with patch.multiple(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: registry,
        async_entries_for_config_entry=lambda reg, entry_id: [],
    ):
        assert await async_migrate_entry(hass, entry) is True
    return entry, removed


async def test_a_fork_v17_entry_folds_the_peak_limit_and_drops_its_entity():
    # Our install: peak shaving off, contracted power 20000 W, limit 2500 W.
    entry, removed = await _migrate(17, {
        CONF_MAX_CONTRACTED_POWER: 20000,
        CONF_CAPACITY_PROTECTION_ENABLED: False,
        "capacity_protection_limit": 2500,
    })
    assert entry.version == 21
    assert "capacity_protection_limit" not in entry.data
    assert entry.data[CONF_MAX_CONTRACTED_POWER] == 20000
    assert removed == ["number.limit"]


async def test_a_fork_v17_entry_with_peak_shaving_on_takes_the_lower_cap():
    entry, _ = await _migrate(17, {
        CONF_MAX_CONTRACTED_POWER: 7000,
        CONF_CAPACITY_PROTECTION_ENABLED: True,
        "capacity_protection_limit": 4500,
    })
    assert entry.data[CONF_MAX_CONTRACTED_POWER] == 4500


async def test_an_upstream_v17_entry_keeps_its_cap():
    entry, removed = await _migrate(17, {CONF_MAX_CONTRACTED_POWER: 6000})
    assert entry.version == 21
    assert entry.data[CONF_MAX_CONTRACTED_POWER] == 6000
    assert removed == []
