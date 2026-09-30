import asyncio
import logging

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AREAS,
    CONF_DOORS,
    CONF_ENABLE_AWAY,
    CONF_ENABLE_BYPASS,
    CONF_ENABLE_NIGHT,
    CONF_ENABLE_STAY,
    CONF_HOST,
    CONF_INPUTS,
    CONF_OUTPUTS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_WX_PASSWORD,
    CONF_WX_USERNAME,
    DOMAIN,
)
from .ict_library import ICTClient
from .records import (
    RECORD_PREFIXES,
    build_selected_records,
    diff_record_sets,
    effective_name,
    normalize_records,
    selected_ids,
)
from .wx_api import ProtegeWXAPI

_LOGGER = logging.getLogger(__name__)

RECORD_SPECS = (
    (CONF_DOORS, "Door", 1, 20),
    (CONF_AREAS, "Area", 2, 10),
    (CONF_INPUTS, "Input", 4, 100),
    (CONF_OUTPUTS, "Output", 3, 20),
)


class ICTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title=f"ICT ({user_input[CONF_HOST]})",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=21000): int,
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ICTOptionsFlowHandler(config_entry)


class ICTOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry
        self.options = dict(config_entry.options)
        self.data = dict(config_entry.data)

        self.options.setdefault(CONF_DOORS, {})
        self.options.setdefault(CONF_AREAS, {})
        self.options.setdefault(CONF_INPUTS, {})
        self.options.setdefault(CONF_OUTPUTS, {})
        self.options.setdefault(CONF_ENABLE_AWAY, True)
        self.options.setdefault(CONF_ENABLE_STAY, True)
        self.options.setdefault(CONF_ENABLE_NIGHT, True)
        self.options.setdefault(CONF_ENABLE_BYPASS, False)

        self._edit_type = None
        self._edit_id = None
        self._manage_available = {}
        self._manage_discovered = {key: set() for key, *_ in RECORD_SPECS}
        self._manage_name_maps = {key: {} for key, *_ in RECORD_SPECS}
        self._manage_source = "Configured records only"
        self._manage_authoritative = False
        self._pending_options = None
        self._pending_diff = None

    def _raw_records(self, key):
        value = self.options.get(key, {})
        return value if isinstance(value, dict) else {}

    def _normalized_records(self, key, discovered=None):
        return normalize_records(
            self._raw_records(key),
            RECORD_PREFIXES[key],
            discovered,
        )

    def _save_options(self, new_options=None):
        """Stage options for the standard OptionsFlow create-entry save."""
        if new_options is not None:
            self.options = new_options

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "manage_entities",
                "configure_arming",
                "configure_connection",
                "configure_wx_names",
                "raw_editor",
            ],
        )

    async def async_step_manage_entities(self, user_input=None):
        return self.async_show_menu(
            step_id="manage_entities",
            menu_options=[
                "manage_search",
                "manage_select",
                "manual_add",
                "edit_device",
                "back",
            ],
        )

    async def _get_wx_name_maps(self):
        username = str(self.data.get(CONF_WX_USERNAME, "")).strip()
        password = str(self.data.get(CONF_WX_PASSWORD, ""))
        if not username or not password:
            return {}

        api = ProtegeWXAPI(self.data[CONF_HOST], username, password)
        try:
            return await api.fetch_name_maps(
                {
                    CONF_DOORS: "GXT_DOORS_TBL",
                    CONF_AREAS: "GXT_AREAS_TBL",
                    CONF_INPUTS: "GXT_INPUTS_TBL",
                    CONF_OUTPUTS: "GXT_PGMS_TBL",
                }
            )
        except Exception as err:
            _LOGGER.warning(
                "Could not retrieve Protege WX names; using Automation Service scan: %s",
                err,
            )
            return {}

    async def _get_scan_client(self):
        if (
            DOMAIN in self.hass.data
            and self._config_entry.entry_id in self.hass.data[DOMAIN]
        ):
            return self.hass.data[DOMAIN][self._config_entry.entry_id], False

        client = ICTClient(
            self.data[CONF_HOST],
            self.data[CONF_PORT],
            self.data.get(CONF_PASSWORD, ""),
        )
        if not await client.start_temp_connection():
            return None, False
        return client, True

    async def async_step_manage_search(self, user_input=None):
        """Search the controller, then return directly to entity selection."""
        if user_input is None:
            return self.async_show_form(
                step_id="manage_search",
                data_schema=vol.Schema(
                    {
                        vol.Required("limit_doors", default=20): int,
                        vol.Required("limit_areas", default=10): int,
                        vol.Required("limit_inputs", default=100): int,
                        vol.Required("limit_outputs", default=20): int,
                    }
                ),
            )

        limits = {
            CONF_DOORS: max(0, int(user_input["limit_doors"])),
            CONF_AREAS: max(0, int(user_input["limit_areas"])),
            CONF_INPUTS: max(0, int(user_input["limit_inputs"])),
            CONF_OUTPUTS: max(0, int(user_input["limit_outputs"])),
        }

        wx_configured = bool(
            str(self.data.get(CONF_WX_USERNAME, "")).strip()
            and str(self.data.get(CONF_WX_PASSWORD, ""))
        )
        name_maps = await self._get_wx_name_maps()
        discovered = {}

        if name_maps:
            # WX database list results are authoritative record lists. Do not
            # revalidate them with Automation Service status requests: some
            # valid records (especially areas) do not answer the existence
            # probe even though they are present in the WX database.
            for key, _prefix, _group, _default_limit in RECORD_SPECS:
                discovered[key] = {
                    int(record_id) for record_id in name_maps.get(key, {})
                }
            source_name = "WX database"
            self._manage_authoritative = True
        else:
            client, temporary = await self._get_scan_client()
            if client is None:
                return self.async_abort(reason="cannot_connect")

            try:
                for key, _prefix, group, _default_limit in RECORD_SPECS:
                    found = set()
                    consecutive_fails = 0
                    for record_id in range(0, limits[key] + 1):
                        exists = await client.check_exists(group, record_id)
                        await asyncio.sleep(0.1)
                        if exists:
                            found.add(record_id)
                            consecutive_fails = 0
                        else:
                            consecutive_fails += 1
                            if consecutive_fails >= 5:
                                break
                    discovered[key] = found
            finally:
                if temporary:
                    await client.stop()

            self._manage_authoritative = False
            if wx_configured:
                source_name = "Automation Service fallback (WX lookup unavailable)"
            else:
                source_name = "Automation Service fallback (WX lookup not configured)"

        self._manage_discovered = discovered
        self._manage_name_maps = {
            key: name_maps.get(key, {}) for key, *_ in RECORD_SPECS
        }
        counts = ", ".join(
            f"{len(discovered[key])} {prefix.lower()}s"
            for key, prefix, *_ in RECORD_SPECS
        )
        self._manage_source = f"{source_name} search complete ({counts})"

        return await self.async_step_manage_select()

    def _selector_for_records(self, key, prefix):
        discovered_names = self._manage_name_maps.get(key, {})
        current = self._normalized_records(key, discovered_names)
        configured_ids = selected_ids(current)
        available_ids = configured_ids | self._manage_discovered.get(key, set())
        self._manage_available[key] = available_ids

        options = []
        for record_id in sorted(available_ids):
            record = current.get(str(record_id))
            if record is None:
                record = {
                    "programmed_name": discovered_names.get(record_id),
                    "custom_name": None,
                }
            name = effective_name(prefix, record_id, record)
            if (
                self._manage_authoritative
                and self._manage_discovered.get(key)
                and record_id not in self._manage_discovered[key]
            ):
                name = f"{name} (not found in current WX database)"
            options.append(
                selector.SelectOptionDict(
                    value=str(record_id),
                    label=f"{record_id} — {name}",
                )
            )

        return selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options,
                mode=selector.SelectSelectorMode.DROPDOWN,
                multiple=True,
            )
        )

    async def async_step_manage_select(self, user_input=None):
        """Select exactly which discovered/configured records HA exposes."""
        if user_input is not None:
            errors = {}
            proposed = dict(self.options)
            diffs = {}

            try:
                for key, prefix, *_ in RECORD_SPECS:
                    raw_selected = user_input.get(key, []) or []
                    submitted = {int(value) for value in raw_selected}
                    if any(record_id < 0 for record_id in submitted):
                        raise ValueError("negative ID")
                    if not submitted.issubset(self._manage_available.get(key, set())):
                        raise ValueError("unknown submitted ID")

                    proposed[key] = build_selected_records(
                        prefix,
                        self._raw_records(key),
                        submitted,
                        self._manage_name_maps.get(key, {}),
                    )
                    diffs[key] = diff_record_sets(
                        self._raw_records(key), proposed[key]
                    )
            except (TypeError, ValueError):
                errors["base"] = "invalid_selection"

            if not errors:
                has_removals = any(diff["removed"] for diff in diffs.values())
                if has_removals:
                    self._pending_options = proposed
                    self._pending_diff = diffs
                    return await self.async_step_confirm_entity_changes()

                self._save_options(proposed)
                return self.async_create_entry(title="", data=self.options)

        self._manage_available = {}
        schema = {}
        for key, prefix, *_ in RECORD_SPECS:
            current_ids = sorted(selected_ids(self._raw_records(key)))
            schema[
                vol.Optional(key, default=[str(value) for value in current_ids])
            ] = self._selector_for_records(key, prefix)

        return self.async_show_form(
            step_id="manage_select",
            data_schema=vol.Schema(schema),
            errors={} if user_input is None else errors,
            description_placeholders={"source": self._manage_source},
        )

    async def async_step_manual_add(self, user_input=None):
        """Manually add one record by type and database ID."""
        errors = {}
        if user_input is not None:
            key = user_input["record_type"]
            record_id = int(user_input["record_id"])
            custom_name = str(user_input.get("name", "")).strip() or None

            if record_id < 0:
                errors["base"] = "invalid_selection"
            else:
                records = self._normalized_records(key)
                if str(record_id) in records:
                    errors["base"] = "id_exists"
                else:
                    records[str(record_id)] = {
                        "programmed_name": None,
                        "custom_name": custom_name,
                    }
                    proposed = dict(self.options)
                    proposed[key] = records
                    self._save_options(proposed)
                    return self.async_create_entry(title="", data=self.options)

        type_selector = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    {"value": CONF_DOORS, "label": "Door"},
                    {"value": CONF_AREAS, "label": "Area"},
                    {"value": CONF_INPUTS, "label": "Input"},
                    {"value": CONF_OUTPUTS, "label": "Output"},
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
        return self.async_show_form(
            step_id="manual_add",
            data_schema=vol.Schema(
                {
                    vol.Required("record_type"): type_selector,
                    vol.Required("record_id"): int,
                    vol.Optional("name", default=""): str,
                }
            ),
            errors=errors,
        )

    def _removal_summary(self):
        if not self._pending_diff:
            return ""
        lines = []
        for key, prefix, *_ in RECORD_SPECS:
            removed = sorted(self._pending_diff.get(key, {}).get("removed", set()))
            old = self._normalized_records(key)
            for record_id in removed:
                name = effective_name(prefix, record_id, old.get(str(record_id)))
                lines.append(f"{prefix} {record_id} — {name}")
        return "\n".join(lines)

    async def async_step_confirm_entity_changes(self, user_input=None):
        if self._pending_options is None:
            return await self.async_step_manage_select()

        if user_input is not None:
            if user_input.get("confirm"):
                self._save_options(self._pending_options)
                self._pending_options = None
                self._pending_diff = None
                return self.async_create_entry(title="", data=self.options)
            self._pending_options = None
            self._pending_diff = None
            return await self.async_step_manage_select()

        return self.async_show_form(
            step_id="confirm_entity_changes",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            description_placeholders={"changes": self._removal_summary()},
        )

    async def async_step_configure_arming(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            self._save_options()
            return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="configure_arming",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ENABLE_AWAY,
                        default=self.options.get(CONF_ENABLE_AWAY, True),
                    ): bool,
                    vol.Required(
                        CONF_ENABLE_STAY,
                        default=self.options.get(CONF_ENABLE_STAY, True),
                    ): bool,
                    vol.Required(
                        CONF_ENABLE_NIGHT,
                        default=self.options.get(CONF_ENABLE_NIGHT, True),
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_BYPASS,
                        default=self.options.get(CONF_ENABLE_BYPASS, False),
                    ): bool,
                }
            ),
        )

    async def async_step_edit_device(self, user_input=None):
        return self.async_show_menu(
            step_id="edit_device",
            menu_options=[
                "edit_door",
                "edit_area",
                "edit_input",
                "edit_output",
                "manage_entities",
            ],
        )

    async def _edit_select_step(self, user_input, storage_key, prefix, step_id):
        records = self._normalized_records(storage_key)
        if user_input:
            self._edit_id = int(user_input["item"])
            self._edit_type = storage_key
            return await self.async_step_edit_confirm()

        if not records:
            return self.async_abort(reason="no_devices")

        options = [
            selector.SelectOptionDict(
                value=str(record_id),
                label=f"{record_id} — {effective_name(prefix, record_id, record)}",
            )
            for record_id, record in sorted(
                ((int(key), value) for key, value in records.items()),
                key=lambda item: item[0],
            )
        ]
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required("item"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_edit_confirm(self, user_input=None):
        key = self._edit_type
        prefix = RECORD_PREFIXES[key]
        records = self._normalized_records(key)
        record = records.get(str(self._edit_id), {})

        if user_input is not None:
            custom_name = str(user_input.get("name", "")).strip() or None
            record["custom_name"] = custom_name
            records[str(self._edit_id)] = record
            self.options[key] = records
            self._save_options()
            return self.async_create_entry(title="", data=self.options)

        current_custom = record.get("custom_name") or ""
        programmed = record.get("programmed_name") or f"{prefix} {self._edit_id}"
        return self.async_show_form(
            step_id="edit_confirm",
            data_schema=vol.Schema({vol.Optional("name", default=current_custom): str}),
            description_placeholders={
                "id": str(self._edit_id),
                "programmed_name": programmed,
            },
        )

    async def async_step_edit_door(self, user_input=None):
        return await self._edit_select_step(
            user_input, CONF_DOORS, "Door", "edit_door"
        )

    async def async_step_edit_area(self, user_input=None):
        return await self._edit_select_step(
            user_input, CONF_AREAS, "Area", "edit_area"
        )

    async def async_step_edit_input(self, user_input=None):
        return await self._edit_select_step(
            user_input, CONF_INPUTS, "Input", "edit_input"
        )

    async def async_step_edit_output(self, user_input=None):
        return await self._edit_select_step(
            user_input, CONF_OUTPUTS, "Output", "edit_output"
        )

    async def async_step_raw_editor(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                raw_data = yaml.safe_load(user_input["config_yaml"])
                if not isinstance(raw_data, dict):
                    raise ValueError("root must be a dictionary")
                for key, prefix, *_ in RECORD_SPECS:
                    section = raw_data.get(key, {})
                    self.options[key] = normalize_records(section, prefix)
                self._save_options()
                return self.async_create_entry(title="", data=self.options)
            except Exception:
                errors["base"] = "yaml_error"

        current = {key: self._normalized_records(key) for key, *_ in RECORD_SPECS}
        return self.async_show_form(
            step_id="raw_editor",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "config_yaml",
                        default=yaml.dump(current, sort_keys=True, allow_unicode=True),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_configure_connection(self, user_input=None):
        if user_input is not None:
            merged = dict(self.data)
            merged[CONF_HOST] = user_input[CONF_HOST]
            merged[CONF_PORT] = user_input[CONF_PORT]
            new_pin = str(user_input.get(CONF_PASSWORD, "")).strip()
            if new_pin:
                merged[CONF_PASSWORD] = new_pin
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=merged
            )
            self.data = merged
            return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="configure_connection",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self.data.get(CONF_HOST)): str,
                    vol.Required(CONF_PORT, default=self.data.get(CONF_PORT)): int,
                    vol.Optional(CONF_PASSWORD, default=""): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
        )

    async def async_step_configure_wx_names(self, user_input=None):
        errors = {}
        if user_input is not None:
            username = str(user_input.get(CONF_WX_USERNAME, "")).strip()
            new_password = str(user_input.get(CONF_WX_PASSWORD, ""))
            merged = dict(self.data)

            if not username:
                merged.pop(CONF_WX_USERNAME, None)
                merged.pop(CONF_WX_PASSWORD, None)
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=merged
                )
                self.data = merged
                return self.async_create_entry(title="", data=self.options)

            password = new_password or str(merged.get(CONF_WX_PASSWORD, ""))
            if not password:
                errors["base"] = "wx_auth"
            else:
                try:
                    api = ProtegeWXAPI(merged[CONF_HOST], username, password)
                    await api.fetch_name_maps({CONF_DOORS: "GXT_DOORS_TBL"})
                except Exception as err:
                    _LOGGER.warning(
                        "Protege WX web login/name lookup failed: %s", err
                    )
                    errors["base"] = "wx_auth"
                else:
                    merged[CONF_WX_USERNAME] = username
                    merged[CONF_WX_PASSWORD] = password
                    self.hass.config_entries.async_update_entry(
                        self._config_entry, data=merged
                    )
                    self.data = merged
                    return self.async_create_entry(title="", data=self.options)

        return self.async_show_form(
            step_id="configure_wx_names",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_WX_USERNAME,
                        default=self.data.get(CONF_WX_USERNAME, ""),
                    ): str,
                    vol.Optional(CONF_WX_PASSWORD, default=""): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_back(self, user_input=None):
        return await self.async_step_init()
