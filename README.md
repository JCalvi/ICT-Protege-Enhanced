<p align="center">
  <img src="custom_components/ict_automation/icon.png" width="150" height="150" alt="ICT Automation Icon">
</p>

# ICT Protege Automation for Home Assistant

A custom Home Assistant integration for **ICT Protege WX** and **Protege GX** systems using the controller's Automation and Control service.

> **Fork attribution:** This repository is forked from the original [caboose014/ICT-Protege-Home-Assistant](https://github.com/caboose014/ICT-Protege-Home-Assistant) project by **caboose014**. The original author created the integration and protocol implementation this fork is based on. This fork is maintained by **JCalvi** and adds fixes and behaviour changes discovered while testing against Protege WX.

The integration connects directly to the ICT Controller's Automation and Control service, normally on **TCP port 21000**, for real-time status and control of Doors, Areas, Inputs, and Outputs.

## Features

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
* **🔎 Device scanning**
  * Scans Protege database record IDs starting at **ID 0**.

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
| **Allow Status Requests When Not Logged In** | On | Allows status monitoring |
| **Ack Commands** | On | Recommended |
| **Expect Ack For Status Monitoring** | Off | Recommended |

After creating the service, verify that it is running under **Monitoring → Services**. A newly created service can also be started manually from there without rebooting the controller.

> **Important:** The port is `21000`, not `2100`.

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

## 🔧 Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **ICT Protege Automation**.
3. Enter:
   * **Host:** IP address of the ICT controller.
   * **Port:** `21000` unless you deliberately configured another port.
   * **Service PIN:** A valid Protege **user PIN**.

The PIN is a Protege user PIN, not the Protege WX web login password. The user must have the appropriate access level/permissions for any doors, areas or outputs Home Assistant is expected to control.

---

## 🚪 Door behaviour

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

## 🔎 Finding Device IDs

The integration uses Protege **database record IDs** unless the controller has explicitly been configured with `ACPUseDisplayOrder = true`.

### Device scanner

The scanner now starts at **database ID 0**, which is valid in Protege and is commonly the first door/area/input record.

The scanner currently stops after five consecutive missing IDs. On systems with sparse database IDs, especially outputs/PGMs, manual configuration may still be required.

### Protege WX read-only API

On Protege WX, the controller's DLL API can also be used to retrieve database IDs while logged into the WX web interface. For example:

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

These `Request&Type=List` requests are read-only.

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

**Contacts work but door control does not**

Status requests can be permitted without login, while door control requires authenticated user permissions. Check the Service PIN and the Protege user's access level.

**Door IDs appear offset by one**

Older versions of the integration scanned from ID `1` and therefore missed database ID `0`. Version 1.8.0 and later scan from ID `0`.

**Inputs or doors appear to use incorrect IDs**

Ensure **Numbers are Big Endian** is disabled on the Automation and Control service.

**Status updates are slow**

The integration uses controller status updates and also performs periodic status polling. `Ack Commands` should normally be enabled and `Expect Ack For Status Monitoring` disabled.

---

## Credits

Original integration and protocol implementation: **caboose014** — [caboose014/ICT-Protege-Home-Assistant](https://github.com/caboose014/ICT-Protege-Home-Assistant)

Fork maintenance and subsequent WX fixes: **JCalvi**.

ICT, Protege WX and Protege GX are trademarks/products of Integrated Control Technology Limited. This project is an independent Home Assistant integration and is not an official ICT product.
