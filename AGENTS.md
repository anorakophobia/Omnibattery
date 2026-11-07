# Guidance for AI coding agents

Omnibattery is a Home Assistant custom integration (`custom_components/omnibattery`) with its own dashboard panel. These notes are for AI assistants (Claude Code, Codex, Copilot, Cursor and others) working in this repository. They state what a change has to cover beyond the code itself.

## Where things live

- `custom_components/omnibattery/`: the integration. `control/` (charge, discharge and protection logic), `pricing/` (dynamic pricing and the chronological planner), `drivers/` (one per battery brand), `infra/` (coordinator, excluded loads, entity naming), `tracking/` (consumption, solar, daily timeline), `const/integration_const.py` (config keys, `DEFAULT_*` values, `CONFIG_NUMBER_DEFINITIONS`).
- `custom_components/omnibattery/frontend/marstek-panel.js`: the dashboard panel. `SYS_SECTIONS` defines the settings cards and their rows; `I18N` holds labels, `SYS_HELP` the tooltips, both in six languages (en, es, ca, de, fr, nl).
- `custom_components/omnibattery/translations/*.json` and `strings.json`: Home Assistant entity names and setup-form texts.
- `site-docs/`: the user documentation, in English (`*.md`) and Spanish (`*.es.md`).
- `tests/`: pytest suite. `CHANGELOG.md`: one entry per user-visible change.

## Workflow

- Pull requests go to the current `release/vX.Y.Z` branch. Bug fixes need no prior approval; features need a discussion or issue labelled `approved` (see `.github/pull_request_template.md`).
- Tests: `pytest` runs the unit suite (the Home Assistant plugin is off, see `pytest.ini`); the flow tests listed in `.github/workflows/tests.yml` run with `pytest -o addopts=""`. The panel's runtime tests need Node 24. CI must stay green.
- `CHANGELOG.md`: add the entry to the `Unreleased` section under Added, Changed or Fixed. A bold title, then what changes for the user, and "Thanks to @user" for the reporter or author.
- Entity identity: keep `unique_id` on `SYSTEM_UNIQUE_ID_PREFIX` (it carries the registry history); build entity ids with `system_entity_id()`. Never rename a translation key that the panel or users' automations rely on without a migration.

## A setting is more than its entity

When you add or change a user setting (a switch, number or select an end user sets), cover all of these in the same change:

1. **Panel row** in `SYS_SECTIONS`: the right card and `grp` (one group per feature: its switch, its settings, its status row), the order within the card, `adv: true` for advanced settings, and `dep: "<switch key>"` so a feature's settings show only while the feature is on. `dep` follows a chain (a row hides while any switch above it is off) and may name a switch on another card. Per-device rows (excluded devices) are grouped by the entity attribute `excluded_device_index` and resolve `dep` within their device. A per-kWh slider whose entity range is far wider than anyone drags gets a panel-only `range: [min, max, step]`.
2. **Label** in `I18N` and **tooltip** in `SYS_HELP`, in all six languages. A tooltip says what the setting does and when it applies, and ends with one sentence stating the default: "Default: on." / "Default: off." / "Default: 20 %." / "Default: not set (off)." / for a derived default, from what ("Default: 5 % of the total battery capacity."). Take the value from the `DEFAULT_*` constant or the entity's fallback, never from memory. Labels per language: Default / Por defecto / Per defecte / Standard / Par défaut / Standaard. Status rows and buttons get no default sentence.
3. **Entity name** in `translations/*.json` and `strings.json`, matching the panel label in meaning.
4. **No hidden state:** a number must not sit at `unknown` (the panel drops such rows). Show "not set" as the value that means the same (for example 0 = off), or give it a "use default" switch (`default_switch` in `CONFIG_NUMBER_DEFINITIONS`) instead of a magic value that means "automatic".
5. **Takes effect without a manual step:** if the setting feeds the predictive plan (which slots to buy, how much, the weekly full charge), add it to `predictive_balance_fingerprint()` so a change re-plans on the next cycle. A setting read live every cycle needs nothing.
6. **Status:** a feature with its own switch shows its status row in its group, like the discharge reserve or the surplus price hold, labelled "<feature> status" (its own label key, not the feature's). A row whose entity has the attribute `applies: false` is not rendered.
7. **Tests:** `tests/test_panel_tooltip_defaults.py` fails for a setting row without its default sentence: add the key and its default (from the constant) there, or to `NO_DEFAULT` for a status row or button. Update the other panel tests (`tests/test_panel_*.py`), and add one that a change re-plans when item 5 applies. Prefer `async def` tests over `asyncio.run()`, which runs Windows out of socket buffers in a full run.
8. **User docs:** update the matching page in `site-docs/` in English and Spanish.

When you remove a setting, remove its row, label, tooltip, entity name and docs as well, and migrate stored values if needed.
