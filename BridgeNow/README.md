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
```

## Prerequisites

Before you begin, make sure you have:

* **Docker & Docker Compose** installed on the host machine ([get Docker](https://docs.docker.com/get-docker/)).
* A **Milesight UG65 Gateway** already paired with your Milesight sensors (AM308/AM307/AM103/WT401) and reachable on the same local network as your Docker host.
* The **LAN IP address** of the machine running Docker (not `localhost`) — you'll need this for the gateway's MQTT settings. Find it with:
  * Linux: `hostname -I`
  * Windows: `ipconfig` (look for "IPv4 Address")
  * Mac: `ipconfig getifaddr en0`

  💡 **Tip:** If your router supports DHCP reservations/static leases, set one for this host's MAC address. Otherwise its IP can change after a router reboot or lease renewal, which will silently disconnect the gateway from the broker.

## Installation & First-Time Setup

1. **Clone the project** to your Docker host machine and `cd` into the `BridgeNow` folder (where `docker-compose.yml` lives).

2. **Review `bridge/config.json`** and confirm the ThingsBoard gateway token matches the device/token you intend to use in your ThingsBoard instance (see "Configuring ThingsBoard" below if you're starting fresh).

3. **Make the startup script executable** (first time only):
   ```bash
   chmod +x start.sh
   ```

4. **Run the startup script:**
   ```bash
   ./start.sh
   ```
   This does two things:
   - Runs the one-time ThingsBoard installer (`--profile install`), which sets up the database schema and optional demo data.
   - Brings up the full stack (`postgres`, `thingsboard-ce`, `mosquitto`, `bridgenow`) in the background.

   The installer step only needs to run once. On future restarts, just use:
   ```bash
   docker compose up -d
   ```

5. **Check that everything started correctly:**
   ```bash
   docker compose ps
   ```
   All services should show as `running` (postgres should also show `healthy`).

6. **Watch the bridge logs** to confirm it connected successfully:
   ```bash
   docker compose logs -f bridgenow
   ```
   You should see:
   ```
   [TB] Gateway connected successfully.
   [TB] Gateway ready.
   [MOSQ] Connected successfully.
   [MOSQ] Subscribed to v1/gateway/telemetry
   🚀 BridgeNow running...
   ```
   If it stops right after "Listening..." with no further activity, telemetry isn't reaching the broker yet — see the Troubleshooting section below.

## 🌐 Accessing ThingsBoard

Once the stack is running, open ThingsBoard in your browser:

```
http://<docker-host-ip>:8080
```

Log in with the default ThingsBoard CE admin credentials (or the ones set up during your install), then create/verify the **Gateway device** whose access token matches `gateway_token` in `bridge/config.json`. Child devices (your Milesight sensors) will be created automatically under this gateway the first time they send telemetry.

## 📡 Configuring the Milesight Gateway (UG65) for MQTT Uplink

This is the step most installs get wrong — the gateway needs to point at your Docker host's **mapped external MQTT port**, not the internal Docker network.

1. Log into the UG65 web UI.
2. Go to the **Applications** section and add/edit an MQTT application.
3. Set the following:

   | Field | Value |
   |---|---|
   | **Broker Address** | Your Docker host's LAN IP (e.g. `192.168.1.50`) — **not** `localhost` or `mosquitto` |
   | **Broker Port** | `1884` |
   | **Client ID** | Any unique identifier (e.g. `ug65-gateway`) |
   | **Topic (Uplink data)** | `v1/gateway/telemetry` (must match `mosquitto.topic` in `bridge/config.json`) |
   | **Data Type** | JSON |
   | **QoS** | 0 or 1 |
   | **TLS** | Disabled (this local stack does not use TLS by default) |

4. Save and check the application's **Status** — it should change to **Connected** within a few seconds. If it stays **Disconnected**, double check the Broker Address/Port and that the host's firewall allows inbound traffic on port 1884.

## 🔍 Verifying Data Flow End-to-End

Use these checks in order if sensors aren't showing up or data isn't updating in ThingsBoard:

1. **Is the gateway connected to the broker?**
   Check the MQTT application's Status in the UG65 web UI — it should say "Connected."

2. **Is anything reaching the broker at all?**
   ```bash
   docker ps
   ```
   Find your mosquitto container's name or ID, then:
   ```bash
   docker exec -it <mosquitto_container_name_or_id> mosquitto_sub -h localhost -t '#' -v
   ```
   This subscribes to *all* topics. If packets appear here, the gateway is reaching the broker — compare the topic name shown to `v1/gateway/telemetry` (it must match exactly). If nothing appears at all, the problem is upstream (Step 1 above, or your network).

3. **Is BridgeNow receiving and forwarding it?**
   ```bash
   docker compose logs -f bridgenow
   ```
   Look for `========== MESSAGE RECEIVED ==========` blocks followed by `[TB] Sending telemetry:`. If you see MQTT connect/subscribe messages but never a MESSAGE RECEIVED block, telemetry still isn't reaching mosquitto — go back to Step 2.

4. **Is ThingsBoard receiving it?**
   In the ThingsBoard UI, open the Gateway device and check its **Latest Telemetry** and connected child devices. New sensors appear automatically the first time they report data.

## 🛠️ Troubleshooting

**Devices show "Inactive" in ThingsBoard even though the physical gateway shows them active:**
This almost always means telemetry isn't reaching ThingsBoard right now — ThingsBoard marks devices inactive after a period without incoming data (default ~5 minutes), regardless of what the physical LoRaWAN gateway shows. Work through "Verifying Data Flow End-to-End" above to find where the chain is broken. Once telemetry resumes, devices flip back to active automatically — no manual fix needed in ThingsBoard itself.

**Gateway MQTT application shows "Disconnected":**
Almost always a wrong Broker Address or Port. Common cause: the Docker host's LAN IP changed (e.g. after a router/DHCP lease renewal) and the gateway is still pointed at the old IP. Re-check the host's current IP and the Prerequisites section above about setting a DHCP reservation to prevent this recurring.

**BridgeNow logs stop right after "🚀 BridgeNow running..." with no further updates:**
This means the bridge is up and technically listening, but nothing is arriving on the MQTT topic. Follow steps 2–3 in "Verifying Data Flow End-to-End" to isolate whether it's a gateway-to-broker issue or a bridge issue.

**Need to fully reset the stack:**
```bash
docker compose down
docker volume rm bridgenow_postgres-data
./start.sh
```
⚠️ This deletes all ThingsBoard data (devices, dashboards, users) and reruns the installer from scratch.