# Changelog

All notable changes to this fork will be documented in this file.

This project is forked from the original [`caboose014/ICT-Protege-Home-Assistant`](https://github.com/caboose014/ICT-Protege-Home-Assistant) integration by **caboose014**. Earlier history belongs to the upstream project; entries below document changes made in this fork.

## 1.8.0 - 2026-09-30

### Changed
- Changed Home Assistant door **Unlock** to use the Protege normal/timed unlock command instead of **Unlock Latched**.
  - This allows Protege area/schedule logic to remain authoritative.
  - Fixes doors that were immediately re-locked when a latched unlock was overridden by controller logic.
- Added a combined `door_state` attribute directly to each door lock entity:
  - `Open` when the door contact is open.
  - `Locked` when the contact is closed and the door is locked.
  - `Closed` when the contact is closed and the door is unlocked.
- Added dynamic door icons matching the combined state.
- Updated device scanning to include **database record ID 0**.

### Fixed
- Fixed the scanner skipping the first Protege database record because it previously started at ID `1`.
- Fixed the practical Front Entry-style case where Protege controller logic immediately overrode an HA latched unlock.

### Notes
- Existing door contact binary sensors remain available for backwards compatibility with automations and dashboards.
- Scanner behaviour still stops after five consecutive missing IDs; sparse databases may still require manual configuration.

## Upstream history

For changes prior to this fork, see the original project:

[`caboose014/ICT-Protege-Home-Assistant`](https://github.com/caboose014/ICT-Protege-Home-Assistant)
