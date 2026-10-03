<p align="center">
  <img src="custom_components/ict_automation/brands/icon@2x.png" width="150" height="150" alt="ICT Automation Icon">
</p>

# ICT Protege Automation for Home Assistant

A custom Home Assistant integration for **ICT Protege WX** and **Protege GX** systems using the controller's Automation and Control service.

> **Fork attribution:** This repository is forked from the original [caboose014/ICT-Protege-Home-Assistant](https://github.com/caboose014/ICT-Protege-Home-Assistant) project by **caboose014**. The original author created the integration and protocol implementation this fork is based on. This fork is maintained by **JCalvi** and adds fixes and behaviour changes discovered while testing against Protege WX.

The integration connects directly to the ICT controller's **Automation and Control** service, normally on **TCP port 21000**, for real-time status and control of Doors, Areas, Inputs and Outputs.

On **Protege WX**, optional WX web-operator credentials can also be configured. They are used only to authenticate to the controller's local HTTPS database API so Home Assistant can retrieve the actual programmed record names and complete Door/Area/Input/Output lists. If WX operator credentials are not configured, or the authenticated metadata lookup fails, discovery falls back to Automation Service status probing.

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
* **🔎 Protege WX programmed-name discovery**
  * Uses a configured Protege WX web operator to authenticate to the local WX database API.
  * Retrieves actual programmed names such as `Front Entry` instead of `Door 0`.
  * Handles sparse database IDs correctly because discovery comes from the WX database rather than sequential status probing.
  * Falls back to Automation Service probing when WX credentials are not configured or WX metadata lookup is unavailable.

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

## 🔐 Authentication and Discovery

There are two separate credentials and they serve different purposes.

| Credential / path | Used for | Required? |
| :--- | :--- | :--- |
| **Automation Service PIN** | Authenticated door/area/output control over TCP port 21000. Status monitoring and fallback discovery also use the Automation and Control service. | Required for normal integration setup and authenticated control commands. |
| **Protege WX Web Operator username/password** | Authenticated read-only lookup of complete WX database record lists and programmed names over HTTPS. | Optional for basic operation, but required to obtain authoritative WX programmed names and complete WX record lists. |

The **Service PIN is not the WX web password**, and the WX operator account is never used to unlock doors, arm areas or switch outputs.

### Discovery order

On Protege WX, **Search / Refresh Controller** uses this order:

```text
1. Authenticated WX database list lookup using the saved WX web operator
        ↓ if not configured or unavailable
2. Automation Service status probing fallback
```

The authenticated WX database lookup is authoritative for record IDs and programmed names. The Automation Service method is a best-effort probe: it can discover usable records, but sparse IDs can be missed and names are generic unless they were already saved from an earlier WX lookup or manually entered.

For example, the WX database path can return:

```text
6 doors
6 areas
63 inputs
41 outputs
```

with names such as:

```text
Front Entry
Roller Pedestrian Door
Site Area
Smoke - Office Area
```

instead of generic labels like `Door 0` or `Input 17`.

Once a selected record's programmed name has been saved in Home Assistant, that saved name remains available even if WX lookup is temporarily unavailable. A fresh authenticated WX lookup is needed only to discover database changes or refresh programmed names.

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

The integration can operate without WX web-operator credentials, but searches will use the Automation Service fallback and cannot retrieve fresh programmed names from the WX database.

### Configure Protege WX name lookup

For Protege WX, configure a web operator at:

**Settings → Devices & Services → ICT Protege Automation → Configure → Configure WX Name Lookup**

Enter a valid **Protege WX web operator username and password**. The integration validates the login before saving it.

These credentials are used only for read-only database/name discovery. They are separate from the Automation Service PIN.

When editing them later:

* leave the password blank to keep the saved password;
* tick **Remove saved WX operator credentials** to remove them completely.

---

## 🧭 Manage Protege Entities

Entity configuration is centred on:

**Settings → Devices & Services → ICT Protege Automation → Configure → Manage Protege Entities**

The menu contains:

* **Search / Refresh Controller**
* **Select / Remove Entities**
* **Manually Add Entity**
* **Rename Entity**

### Search / Refresh Controller

When WX operator credentials are configured, the integration logs in to the local Protege WX database API and retrieves the complete available record sets and programmed names for:

```text
Doors
Areas
Inputs
Outputs / PGMs
```

After the search, Home Assistant opens the selection screen. **Newly discovered records are not automatically enabled.**

A successful authenticated WX lookup reports a source such as:

```text
Source: WX database (operator login) search complete (6 doors, 6 areas, 63 inputs, 41 outputs).
```

If WX credentials are not configured, or the lookup fails, the source line identifies the Automation Service fallback instead.

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

### Protege WX database API

The integration uses the controller's local HTTPS DLL API to retrieve record lists and names after authenticating with the configured WX web operator.

The relevant list request is of the form:

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

The integration establishes an operator session first, then requests the record lists within that authenticated session. These operations are used only for metadata discovery. Status monitoring and control continue to use the Automation and Control service.

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

**Search shows `WX database (operator login)`**

The saved WX operator account authenticated successfully and the controller's database lists were used. This is the authoritative source for current record IDs and programmed names.

**Search falls back to Automation Service**

Either WX operator credentials are not configured or the authenticated WX lookup failed. The fallback scan can still discover records, but it is not an authoritative WX database inventory and may show generic names or incomplete counts when database IDs are sparse.

**Protege WX operator login failed**

* Confirm the username/password can log in to the controller's normal local Protege WX web interface.
* Remember this is a **WX web operator account**, not the Automation Service PIN.
* Re-enter it under **Configure → Configure WX Name Lookup**.

**Fallback search shows generic names or unexpected counts**

Configure valid WX operator credentials and repeat **Search / Refresh Controller**. A successful WX lookup should produce a source line beginning with:

```text
Source: WX database (operator login) ...
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
