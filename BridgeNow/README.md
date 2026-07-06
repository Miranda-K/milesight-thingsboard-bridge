# Milesight to ThingsBoard IoT Bridge (cmi-iot-dashboard)

A Dockerized local IoT stack using Python and MQTT to forward Milesight LoRaWAN sensor telemetry directly into ThingsBoard CE. 

This project was developed for **CMI Tech** to act as a highly customizable upgrade and replacement for the BeaverIoT platform using ThingsBoard. It enables real-time monitoring, advanced time-series dashboarding, and bidirectional threshold controls for smart building environments.

## Project Overview & Hardware

Unlike standard cloud-based TTS (The Things Stack) architectures, this project leverages the embedded Network/Application server on a local Milesight gateway to keep all data securely on the local network. 

**Target Hardware Assets:**
* **Milesight AM308:** 8-in-1 indoor air quality sensor (CO2, Temp, Humidity, PM2.5, etc.)
* **Milesight AM307:** 7-in-1 indoor air quality sensor
* **Milesight AM103:** 3-in-1 indoor air quality sensor
* **Milesight WT401:** Wireless Smart Thermostat
* **Milesight UG65:** LoRaWAN Gateway (Acting as local Network & App Server)

## Tech Stack

* **ThingsBoard Community Edition (CE):** Open-source IoT platform for device management, data collection, processing, and visualization.
* **Eclipse Mosquitto:** Lightweight MQTT broker to intercept local gateway traffic.
* **Python 3.12:** Custom `BridgeNow` application using `paho-mqtt` to format and route telemetry to the ThingsBoard Gateway API.
* **PostgreSQL 17:** Persistent database for ThingsBoard entity and time-series data.
* **Docker & Docker Compose:** Containerized orchestration for easy deployment.

## 📂 Project Structure

```text
├── bridge/
│   ├── bridge.py          # Python MQTT forwarding script
│   ├── config.json        # Mosquitto and ThingsBoard credentials/host mapping
│   ├── Dockerfile         # Python environment builder
│   └── requirements.txt   # Python dependencies (paho-mqtt)
├── mosquitto/
│   └── mosquitto.conf     # MQTT broker configuration
├── .gitignore             # Git ignore rules (protects postgres-data)
├── docker-compose.yml     # Complete stack architecture
├── start.sh               # One-click startup and install script
└── README.md              # This documentation