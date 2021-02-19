# NXP HoverGames Challenge 2: Help Drones, Help Others During Pandemics

These are the codes developed in the frame of NXP HoverGames Challenge 2: Help Drones, Help Others During Pandemics competition 

## Videos
- [Human detection - 1 subject (github)](https://github.com/dmdobrea/HoverGames_Challenge2/blob/main/05_RealApplication_NavQ/output/v1_rez.avi)
- [Human detection - 3 subjects (github)](https://github.com/dmdobrea/HoverGames_Challenge2/blob/main/05_RealApplication_NavQ/output/v2_rez.avi)
- [Human detection - in real time YouTube](https://youtu.be/pCcItZNOWmc)

## Overview

In this project, I propose a solution to sustain and enforce the quarantine zones. The solution is based on an autonomous unmanned aerial vehicle (a NXPHoverGames drone) to detect humans and timely send warnings to a control center.

![NXPHoverGames drone, basic schematic](./SchBloc_Main.PNG)

## Components

### Hardware components:

- 1 x **NXP KIT-HGDRONEK66** (carbon frame kit, BLDC motors, ESCs, PDB, propellers, etc.)
- 1 x **NXP RDDRONE-FMUK66** - flight management unit
- 1 x **NXP RDDRONE-8MMNavQ** - an embedded computer (i.MX 8M Mini Quad, 2GB LPDDR4, 16GB eMMC, WiFi/BT)
- 1 x **Google Coral camera**
- 1 x **NXP HGD-TELEM433** - 433Mhz Telemetry Radio 
- 1 x 4S 5000 mAh battery (3S can work too)

### Software components

#### Official software

- **PX4** - an open source flight control software for drones and other unmanned vehicles
- **PX4 MAVSDK** - a package used to control NXPHoverGames using MAVLink
- **PX4 QGroundControl** - Ground Control Station for the MAVLink protocol
- **NXP MCUXpresso IDE** - Eclipse-based IDE tool used to develop applications on NXP RDDRONE-FMUK66

#### Main software components developed for NXP HoverGames Challenge 2

- **hr_RealAppNavQ.py** (placed in 05_RealApplication_NavQ) - a human recognition application (running on NXP RDDRONE-8MMNavQ embedded system ) developed in Python based on MobileNet-SSD (MobileNet Single-Shot multibox Detection) deep neural network and on a correlation tracker algorithm
- **server_jpg.py** (placed in 03_ZMQ_base) - ZeroMQ server (running on the ground station PC) able to talk with hr_RealAppNavQ.py (placed in working mode 1: "-m 1").
- **uorb_mavlink** (placed in 06_FMUK66/test_commCompCom) - the application running on the RDDRONE-FMUK66 FMU able to receive custom MAVlink messages (sent it by **server_jpg.py** application placed in workinh mode 2: "-m 2") as uORB messages

