# WMMT6 Telemetry for SimHub

A lightweight telemetry bridge for **Wangan Midnight Maximum Tune 6 (WMMT6)** that reads in-game vehicle data directly from the game process and sends it to **SimHub** over UDP.

Currently tested with:

* WMMT6 Version `1.03.04`
* SimHub

---

# Features

* Reads live telemetry data from `wmn6r.exe`
* Sends telemetry to SimHub using UDP
* Supports:

  * Speed
  * RPM
  * Gear
* Simple Python-based setup

---

# Requirements

## Software

* Python 3.x
* SimHub
* WMMT6

## Python Packages

Install required dependencies:

```bash
pip install pymem
```

---

# Installation

## 1. Import the SimHub Definition

1. Open SimHub
2. Go to:

```text
Games > SimHub Dash Studio > Sim Games Configuration
```

3. Open the **Sim Definition Editor**
4. Import:

```text
wmmt6.simdef
```

5. Register/enable the game definition

---

## 2. Start the Game

Launch:

```text
wmn6r.exe
```

Make sure the game is fully loaded before starting telemetry.

---

## 3. Run the Telemetry Script as Administrator

Open Command Prompt as Administrator.

Navigate to the project folder and run:

```bash
python telemetry.py
```

Or create a batch file:

```bat
@echo off
python "%~dp0telemetry.py"
pause
```

---

# How It Works

The script hooks into the WMMT6 process (`wmn6r.exe`) and reads memory values for:

* Vehicle speed
* Engine RPM
* Current gear

These values are then broadcast to:

```text
UDP Port: 20777
```

SimHub receives the telemetry and makes it available for:

* Dashboards
* LEDs
* Bass shakers
* Motion rigs
* Custom overlays
* Arduino displays

---

# Usage Notes

* The script must be run with administrator privileges.
* Memory offsets may break after game updates.
* Antivirus software may flag memory-reading tools.
* Designed for local/offline telemetry usage.

---

# File Overview

| File           | Description                  |
| -------------- | ---------------------------- |
| `telemetry.py` | Main telemetry bridge script |
| `wmmt6.simdef` | SimHub game definition       |
| `readme.txt`   | Original setup notes         |

---

# Troubleshooting

## SimHub Not Receiving Data

Check:

* SimHub is running
* The game definition is enabled
* UDP port `20777` is not blocked
* The script is running as admin
* WMMT6 is already open before launching telemetry

---

## Python Not Found

Install Python from:

urlPython Official Website[https://www.python.org/downloads/](https://www.python.org/downloads/)

Make sure:

```text
Add Python to PATH
```

is enabled during installation.

---

# Credits

Created for the WMMT6 sim racing and arcade community.

Compatible with:

* SimHub
* Custom dashboards
* Arduino projects
* Sim racing hardware
