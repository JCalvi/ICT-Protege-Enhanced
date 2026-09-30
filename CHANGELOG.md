# Changelog

All notable changes to this fork will be documented in this file.

This project is forked from the original [`caboose014/ICT-Protege-Home-Assistant`](https://github.com/caboose014/ICT-Protege-Home-Assistant) integration by **caboose014**. Earlier history belongs to the upstream project; entries below document changes made in this fork.

## 1.9.0 - 2026-09-30

### Added
- Added optional **Protege WX web operator credentials** to the integration connection settings.
- Added read-only Protege WX DLL API name lookup during device scans.
- Scanned Doors, Areas, Inputs and Outputs can now use their actual programmed Protege names, for example `Roller Pedestrian Door` instead of `Door 1`.

### Changed
- When WX web operator credentials are configured, the scanner uses the WX database record list to obtain actual names and identify sparse record IDs.
- Existing manually edited Home Assistant names are preserved; only missing names or generic scan names such as `Door 1` are automatically replaced.
- The Automation and Control Service PIN remains responsible for monitoring and control. WX web credentials are used only for read-only scan metadata.
- Updated scan UI text to reflect that scanning starts at database ID `0`.

### Notes
- Name lookup uses the controller's HTTPS `PRT_CTRL_DIN_ISAPI.dll` interface with ICT's documented server-side operator authentication.
- If WX web credentials are not configured, cannot authenticate, or the controller does not support the WX DLL API, scanning falls back to the existing Automation Service-only behaviour and generic names.
- GX systems continue to use the Automation Service-only scan path unless equivalent metadata lookup is added later.

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
- Without WX web name lookup, scanner behaviour still stops after five consecutive missing IDs; sparse databases may require manual configuration.

## Upstream history

For changes prior to this fork, see the original project:

[`caboose014/ICT-Protege-Home-Assistant`](https://github.com/caboose014/ICT-Protege-Home-Assistant)
