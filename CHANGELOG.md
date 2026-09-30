# Changelog

All notable changes to this fork will be documented in this file.

This project is forked from the original [`caboose014/ICT-Protege-Home-Assistant`](https://github.com/caboose014/ICT-Protege-Home-Assistant) integration by **caboose014**. Earlier history belongs to the upstream project; entries below document changes made in this fork.

## 2.0.3 - 2026-09-30

### Fixed
- Automation Service fallback scans are now treated as non-authoritative. Existing configured records are retained without being labelled **not found** merely because the fallback scan did not reach or verify them.
- The Select / Remove screen now clearly states whether it used the authoritative WX database or an Automation Service fallback.
- When WX credentials are configured but lookup fails, the source line reports **WX lookup unavailable** instead of silently looking like a normal Automation Service search.
- When WX lookup is not configured, the source line explicitly says so.

### Notes
- The Automation Service fallback still discovers what it can, but sparse IDs and some Area records cannot be reliably proven absent through that protocol. Only the WX database list is used to make an authoritative missing-record judgement.

## 2.0.2 - 2026-09-30

### Fixed
- WX database search now trusts the WX database record lists directly instead of revalidating each record through Automation Service status probes. This avoids valid records, especially Areas, being incorrectly marked **not found in latest search**.
- Fresh WX programmed names now take precedence over stale saved programmed names, so refreshed searches immediately show current Protege names instead of generic names such as `Door 0`.

### Changed
- Moved **Rename Entity** into **Manage Protege Entities** so search, selection/removal, manual add and rename are all grouped together.
- The rename submenu now returns to **Manage Protege Entities** rather than the top-level setup menu.

## 2.0.1 - 2026-09-30

### Fixed
- Published the completed v2 entity-management implementation under a new patch release after the initial `v2.0.0` tag was created before all source updates had landed.
- No additional entity-ID migration is introduced; `v2.0.1` is the release to install for the completed v2 workflow.

## 2.0.0 - 2026-09-30

### Changed
- Redesigned **Manage Protege Entities** as the central add/search/remove workflow.
- Added **Search / Refresh Controller** inside entity management. Search results feed the four selection lists but are not automatically enabled.
- Added **Select / Remove Entities** with separate multi-selects for Doors, Areas, Inputs and Outputs. Existing configured records remain preselected.
- Restored manual addition through **Manually Add Entity**, allowing Door, Area, Input or Output database IDs plus an optional custom Home Assistant name.
- Removed the redundant top-level **Discover / Rescan Devices** menu entry.
- Search uses full WX database lists and programmed names when WX Name Lookup is configured; Automation Service scanning remains the fallback when WX metadata is unavailable.
- Removal confirmation remains in place before configured records are deleted from Home Assistant.

### Compatibility
- Stable entity unique IDs remain unchanged, so retained entities keep their Home Assistant identity and existing dashboards/automations continue to point at the same entities.
- Existing `programmed_name` and `custom_name` metadata is preserved.
- Manual additions use the same structured record model as discovered records.

## 1.11.1 - 2026-09-30

### Fixed
- Kept the config-flow version at `1` so existing installations do not require a separate Home Assistant config-entry migration handler.
- Changed option updates to use the normal Home Assistant OptionsFlow save path rather than updating the config entry prematurely while the flow is still open.

## 1.11.0 - 2026-09-30

### Added
- Added a single **Manage Protege Entities** screen for Doors, Areas, Inputs and Outputs.
- Added transactional add/remove diff handling with a confirmation screen before any record is removed.
- Added structured record metadata with separate `programmed_name` and `custom_name` values.
- Added safe migration helpers for legacy string-based record names.

### Changed
- Replaced the separate Add Door / Add Area / Add Input / Add Output / Remove Device menu entries with one four-section multi-select manager.
- Existing configured records are preselected; selecting a record adds it and clearing it removes it.
- With WX Name Lookup configured, the manager loads actual programmed names and available record IDs from the controller.
- Existing custom names are preserved while programmed WX names can continue to refresh.
- Renaming an entity now stores only a Home Assistant override; clearing that override returns the entity to its Protege programmed name.
- Discover / Rescan Devices remains available as a fallback and discovery tool.

### Compatibility
- Stable entity unique IDs are unchanged (`ict_door_<id>`, `ict_area_<id>`, `ict_input_<id>`, etc.), so retained records keep their existing Home Assistant identity.
- Legacy record dictionaries such as `{"1": "Door Name"}` remain readable and are normalized automatically when records are managed, scanned or renamed.

## 1.10.0 - 2026-09-30

### Changed
- Consolidated all Protege entities under a single Home Assistant device named **ICT Protege Controller**.
- Doors, door contacts, areas, inputs, input troubles, input bypass controls and outputs now all belong to the same controller device.
- Removed per-door, per-area, per-input and per-output Home Assistant device shells.
- Added automatic cleanup of legacy per-record device shells after entities migrate to the controller device.

### Notes
- Entity IDs and unique IDs are unchanged, so existing dashboards and automations should continue to work.
- Only the Home Assistant device grouping changes; Protege monitoring and control behaviour is unchanged.

## 1.9.1 - 2026-09-30

### Fixed
- Fixed device scans incorrectly failing with `invalid_auth` before any read-only status requests were attempted.
- Device scans no longer perform an Automation Service PIN login when scanning records. This matches the documented controller configuration requirement **Allow Status Requests When Not Logged In**.
- Separated optional Protege WX web-operator authentication from the Automation Service PIN.
- Editing connection settings with a blank Service PIN now preserves the existing PIN instead of replacing it with a blank value.

### Changed
- Added a dedicated **Configure WX Name Lookup** options step for the optional WX web operator username/password used only for programmed-name discovery.
- WX name-lookup credentials are validated when saved and now report a dedicated WX authentication error instead of the misleading Automation Service `invalid_auth` error.
- Updated the release workflow so changing `manifest.json` automatically publishes the corresponding GitHub/HACS release.

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
