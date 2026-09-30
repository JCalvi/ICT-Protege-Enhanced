<p align="center">
  <img src="custom_components/ict_automation/icon.png" width="150" height="150" alt="ICT Automation Icon">
</p>

# ICT Protege Automation for Home Assistant

A custom Home Assistant integration for **ICT Protege WX** and **Protege GX** systems using the controller's Automation and Control service.

> **Fork attribution:** This repository is forked from the original [caboose014/ICT-Protege-Home-Assistant](https://github.com/caboose014/ICT-Protege-Home-Assistant) project by **caboose014**. The original author created the integration and protocol implementation this fork is based on. This fork is maintained by **JCalvi** and adds fixes and behaviour changes discovered while testing against Protege WX.

The integration connects directly to the ICT controller's **Automation and Control** service, normally on **TCP port 21000**, for real-time status and control of Doors, Areas, Inputs and Outputs.

On **Protege WX**, the integration can also use a separate **WX web operator account** to read the controller database over HTTPS. This second login is what allows Home Assistant to obtain the actual programmed record names and the complete record lists used by the entity manager.

## Features

* **Single Home Assistant device**
  * All configured Protege entities are grouped under one device: **ICT Protege Controller**.
* **🚪 Doors**
  * Lock and unlock controls.
  * Real-time door contact and lock status.
  * Combined `door_state` attribute on the lock entity: `Open`, `Closed`, or `Locked`.
  * Door icon changes to match the combined state.
  * Normal Home Assistant **Unlock** uses Protege's timed/normal unlock command rather than latched unlock, allowing controller-side area/schedule logic to remain authoritative.
* **🛡️ Areas**
  * Arm (Away) and Disarm controls.
  * Real-time Armed/Disarmed and alarm state.
* **🔌 Inputs & Troubles**
  * Monitors physical state (Open/Closed).
  * Automatically creates a secondary Trouble entity for each input.
  * Supports input bypass/unbypass controls.
* **💡 Outputs**
  * Turn PGMs and other outputs On/Off.
* **🧭 Manage Protege Entities**
  * One central menu for search, selection/removal, manual addition and renaming.
  * Four multi-select lists for Doors, Areas, Inputs and Outputs.
  * Existing configured records are preselected.
  * Searching does **not** automatically enable every discovered record.
  * Clearing a selected record removes it from Home Assistant after confirmation.
  * Manual addition remains available when discovery cannot find a record.
* **🔎 Protege WX database discovery**
  * With WX web operator credentials configured, Home Assistant reads the controller's actual programmed record lists and names.
  * Sparse database IDs are handled correctly because discovery comes from the WX database rather than sequential status probing.
  * Without WX database access, the integration can fall back to Automation Service probing, but that fallback is intentionally best-effort and should not be treated as an authoritative inventory of a WX controller.

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## ⚙️ ICT Controller Configuration

Before installing, configure an **Automation and Control** service on the ICT controller.

For Protege WX this is normally found under:

**Programming → Services**

Create or edit a service with **Service Type = Automation and Control**.

Recommended settings:

| Setting | Value | Note |
| :--- | :--- | :--- |
| **Service Mode** | `Start With Controller OS` | Starts automatically with the controller |
| **IP Port** | `21000` | Default Automation and Control port |
| **Encryption Level** | `None` | Currently supported mode |
| **Checksum Type** | `8 Bit Sum` | Required for protocol matching |
| **Numbers are Big Endian** | Off | Integration uses little-endian IDs |
| **Allow Status Requests When Not Logged In** | On | Allows read-only status requests without a service login |
| **Ack Commands** | On | Recommended |
| **Expect Ack For Status Monitoring** | Off | Recommended |

After creating the service, verify that it is running under **Monitoring → Services**. A newly created service can also be started manually from there without rebooting the controller.

> **Important:** The port is `21000`, not `2100`.

---

## 🔐 Two Separate Credentials

Protege WX users should understand that this integration can use **two completely separate authentication paths**.

| Credential | Used for | Required? |
| :--- | :--- | :--- |
| **Automation Service PIN** | Door/area/output control over TCP port 21000. Status requests use the Automation and Control service as well. | Required for normal integration setup and authenticated control commands. |
| **Protege WX Web Operator username/password** | Read-only HTTPS database lookup for programmed names and complete Door/Area/Input/Output record lists. | Strongly recommended on WX. Required if you want reliable WX database enumeration and actual programmed names. |

The **Service PIN is not the WX web password**, and the WX web operator account is not used to unlock doors, arm areas or switch outputs.

### Why the WX operator account matters

The Automation and Control protocol is excellent for live status and control, but it is not a reliable database-enumeration interface. A fallback scan can probe record IDs and ask whether something responds, but it may miss sparse records and should not be considered a complete inventory of a WX database.

The WX web operator login lets the integration query the controller's local read-only database list endpoints instead. That gives Home Assistant:

* the actual programmed names, such as `Front Entry` instead of `Door 0`;
* the complete set of programmed Doors, Areas, Inputs and Outputs;
* correct handling of sparse IDs, for example Areas at IDs `0`, `16`, `17`, `18`, `19` and `20`;
* a much better source list for **Manage Protege Entities**.

For a Protege WX installation, configuring this account is therefore the recommended setup. If you omit it, the integration still works for configured entities, but **Search / Refresh Controller** falls back to Automation Service probing and discovered counts/names may be incomplete or generic.

The WX credentials are only sent to the local controller's HTTPS interface and are used for database/name lookup. The integration closes the API session after retrieving the requested metadata.

Once a selected record's programmed name has been saved in the Home Assistant configuration, that saved name remains available even if WX lookup is temporarily unavailable. WX access is needed again when you want to refresh the database, discover changes or retrieve updated programmed names.

---

## 📥 Installation

### HACS

1. Open **HACS** in Home Assistant.
2. Go to **Integrations → Custom repositories**.
3. Add:

   `https://github.com/JCalvi/ICT-Protege-Home-Assistant`

4. Select **Integration** as the repository type.
5. Download the integration.
6. Restart Home Assistant.

### Manual

1. Download this repository.
2. Copy `custom_components/ict_automation` into Home Assistant's `/config/custom_components/` directory.
3. Restart Home Assistant.

---

## 🔧 Initial Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **ICT Protege Automation**.
3. Enter:
   * **Host:** IP address of the ICT controller.
   * **Port:** `21000` unless you deliberately configured another port.
   * **Service PIN:** A valid Protege user PIN for the Automation and Control service.

The Protege user associated with that PIN must have the appropriate access level/permissions for any doors, areas or outputs Home Assistant is expected to control.

### Configure Protege WX Name Lookup

For Protege WX, after creating the integration entry go to:

**Settings → Devices & Services → ICT Protege Automation → Configure → Configure WX Name Lookup**

Enter a valid **Protege WX web operator username and password**.

This account must be able to log in to the controller's local WX web interface. It is used only for read-only database/name lookup; it does not replace the Automation Service PIN.

When editing these settings later:

* leave the password blank to keep the saved password;
* clear the username to disable WX name lookup.

---

## 🧭 Manage Protege Entities

Entity configuration is now centred on:

**Settings → Devices & Services → ICT Protege Automation → Configure → Manage Protege Entities**

The menu contains:

* **Search / Refresh Controller**
* **Select / Remove Entities**
* **Manually Add Entity**
* **Rename Entity**

### Search / Refresh Controller

On a Protege WX system with a working WX operator login, this reads the controller's WX database and retrieves the complete available record sets and programmed names for:

```text
Doors
Areas
Inputs
Outputs / PGMs
```

After the search, Home Assistant opens the selection screen. **Newly discovered records are not automatically enabled.**

The source line tells you which discovery method was used, for example:

```text
Source: WX database search complete (6 doors, 6 areas, 63 inputs, 41 outputs).
```

If WX lookup is unavailable, the source line explicitly shows an Automation Service fallback instead.

### Select / Remove Entities

The selection screen has four multi-select sections:

```text
Doors
Areas
Inputs
Outputs
```

Existing configured records are preselected.

* Select a new record to expose it in Home Assistant.
* Leave an existing record selected to keep it.
* Clear an existing record to remove its Home Assistant entities.
* Removals require a confirmation step.
* Nothing is deleted from the Protege controller.

Entity identity is based on **record type + Protege database ID**, not the display name. Renaming a record therefore does not change its Home Assistant unique ID.

### Manually Add Entity

Use **Manually Add Entity** when discovery does not provide the required record, particularly on GX or unusual configurations.

Choose:

* Record Type: Door / Area / Input / Output
* Database ID
* Optional custom Home Assistant name

The manually added record then behaves like any other selected record.

### Rename Entity

**Rename Entity** is also inside **Manage Protege Entities**.

A custom Home Assistant name is stored separately from the programmed Protege name. Clearing the custom name returns the entity to the saved/programmed Protege name.

---

## 🚪 Door Behaviour

Each configured door creates a Home Assistant lock entity and a contact binary sensor.

The lock entity also exposes a combined `door_state` attribute:

| Contact | Lock state | `door_state` |
| :--- | :--- | :--- |
| Open | Any | `Open` |
| Closed | Locked | `Locked` |
| Closed | Unlocked | `Closed` |

This makes it possible to show a compact dashboard row using the lock entity's `door_state` attribute without creating separate template entities.

### Unlock behaviour

Protege supports both normal/timed unlock and latched unlock. In this fork, Home Assistant's standard **Unlock** action sends the Protege **normal/timed unlock** command.

This is intentional: doors controlled by Protege area/schedule rules can immediately override a latched unlock. A normal unlock releases the door for its configured activation time while preserving the controller's existing security logic.

---

## 🔎 Protege Record IDs and WX Names

The integration uses Protege **database record IDs** unless the controller has explicitly been configured with `ACPUseDisplayOrder = true`.

Database ID `0` is valid and is commonly the first record.

### Protege WX read-only database API

When WX Name Lookup is configured, the integration uses the controller's local HTTPS DLL API to retrieve record lists and names. The equivalent list can be viewed manually while authenticated to WX, for example:

```text
https://CONTROLLER/PRT_CTRL_DIN_ISAPI.dll?Request&Type=List&SubType=GXT_DOORS_TBL
```

Common table names include:

```text
GXT_DOORS_TBL    Doors
GXT_AREAS_TBL    Areas
GXT_INPUTS_TBL   Inputs / Sensors
GXT_PGMS_TBL     Outputs / PGMs
```

These `Request&Type=List` operations are used only for metadata discovery. Status monitoring and control continue to use the Automation and Control service.

### Display-order mode

Only use display-order numbering if you have deliberately added this controller command:

```text
ACPUseDisplayOrder = true
```

Otherwise use the actual Protege database record IDs.

---

## 📝 Troubleshooting

**Authentication failed / Service PIN rejected**

* Confirm the controller address and port first.
* Confirm the Automation and Control service is running.
* Confirm the configured value is a valid Protege user PIN.
* Confirm that user has an access level permitting the intended controls.

**Protege WX web login failed**

* Confirm the username/password can log in to the controller's normal local Protege WX web interface.
* Remember this is a **WX web operator account**, not the Automation Service PIN.
* Re-enter it under **Configure → Configure WX Name Lookup**.
* A blank password means "keep the saved password"; clear the username if you intentionally want to disable WX lookup.

**Search says `Automation Service fallback (WX lookup not configured)`**

No WX web operator credentials are currently saved. Configure **WX Name Lookup** if you want programmed names and authoritative WX database record lists.

**Search says `Automation Service fallback (WX lookup unavailable)`**

WX credentials are saved, but the HTTPS database lookup failed. Check the WX login and then run **Search / Refresh Controller** again.

**Fallback search shows generic names or unexpected counts**

The Automation Service fallback is only a best-effort status probe; it is not the authoritative WX database inventory. Configure a working WX operator login and repeat **Search / Refresh Controller**. The source line should then begin with:

```text
Source: WX database search complete (...)
```

**Contacts work but door control does not**

Status requests can be permitted without login, while door control requires authenticated user permissions. Check the Service PIN and the Protege user's access level.

**Door IDs appear offset by one**

Older versions of the integration scanned from ID `1` and therefore missed database ID `0`. Current versions use database ID `0` correctly.

**Inputs or doors appear to use incorrect IDs**

Ensure **Numbers are Big Endian** is disabled on the Automation and Control service.

**Status updates are slow**

The integration uses controller status updates and also performs periodic status polling. `Ack Commands` should normally be enabled and `Expect Ack For Status Monitoring` disabled.

---

## Credits

Original integration and protocol implementation: **caboose014** — [caboose014/ICT-Protege-Home-Assistant](https://github.com/caboose014/ICT-Protege-Home-Assistant)

Fork maintenance and subsequent WX fixes: **JCalvi**.

ICT, Protege WX and Protege GX are trademarks/products of Integrated Control Technology Limited. This project is an independent Home Assistant integration and is not an official ICT product.
