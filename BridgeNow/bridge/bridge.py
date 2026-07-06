import json
import time
import paho.mqtt.client as mqtt

# ------------------------
# Load config
# ------------------------
with open("config.json") as f:
    config = json.load(f)

MOSQ_HOST = config["mosquitto"]["host"]
MOSQ_PORT = config["mosquitto"]["port"]
MOSQ_TOPIC = config["mosquitto"]["topic"]

TB_HOST = config["thingsboard"]["host"]
TB_PORT = config["thingsboard"]["port"]

# ------------------------
# Device registry
# ------------------------
connected_devices = set()
gateway_connected = False

# ------------------------
# MQTT clients
# ------------------------
tb_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mosq_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# ------------------------
# ThingsBoard callbacks
# ------------------------

def on_tb_connect(client, userdata, flags, reason_code, properties):
    global gateway_connected

    if reason_code == 0:
        gateway_connected = True
        print("[TB] Gateway connected successfully.")
    else:
        print(f"[TB] Connection failed: {reason_code}")


def on_tb_disconnect(client, userdata, flags, reason_code, properties):
    global gateway_connected

    gateway_connected = False
    connected_devices.clear()

    print(f"[TB] Gateway disconnected: {reason_code}")


def on_tb_publish(client, userdata, mid, reason_code, properties):
    print(f"[TB] Publish acknowledged (MID={mid})")


# ------------------------
# Configure ThingsBoard client
# ------------------------

tb_client.username_pw_set(config["thingsboard"]["gateway_token"])

tb_client.on_connect = on_tb_connect
tb_client.on_disconnect = on_tb_disconnect
tb_client.on_publish = on_tb_publish

tb_client.reconnect_delay_set(min_delay=1, max_delay=30)

print("[TB] Connecting to ThingsBoard...")

tb_client.connect_async(TB_HOST, TB_PORT, 60)
tb_client.loop_start()
print("[TB] Connection initiated.")

tb_client.loop_start()

print("[TB] Waiting for gateway connection...")

while not gateway_connected:
    time.sleep(0.2)

print("[TB] Gateway ready.")

# ------------------------
# Connect child device
# ------------------------

def connect_device(device_name):

    if device_name in connected_devices:
        return True

    payload = {
        "device": device_name
    }

    print(f"[TB] Connecting child device '{device_name}'...")

    info = tb_client.publish(
        "v1/gateway/connect",
        json.dumps(payload),
        qos=1
    )

    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        print("[TB] Failed to publish child device connection.")
        return False

    connected_devices.add(device_name)

    print("[TB] Child device connected.")

    return True

# ------------------------
# Forward telemetry
# ------------------------

def forward_telemetry(device_name, values):

    payload = {
        device_name: [values]
    }

    print("[TB] Sending telemetry:")
    print(json.dumps(payload, indent=2))

    tb_client.publish(
        "v1/gateway/telemetry",
        json.dumps(payload),
        qos=1
    )

# ------------------------
# Incoming Mosquitto messages
# ------------------------

def on_message(client, userdata, msg):

    print("\n========== MESSAGE RECEIVED ==========")

    try:

        data = json.loads(msg.payload.decode())

        print(json.dumps(data, indent=2))

        device_name = data.get("deviceName", "UNKNOWN_DEVICE")

        values = {
            k: v
            for k, v in data.items()
            if k not in [
                "deviceName",
                "devEUI",
                "devEui",
                "applicationID"
            ]
        }

        if connect_device(device_name):
            forward_telemetry(device_name, values)

    except Exception as e:
        print("[ERROR]", e)

# ------------------------
# Mosquitto setup
# ------------------------

mosq_client.on_message = on_message

print("[MOSQ] Connecting...")

mosq_client.connect(MOSQ_HOST, MOSQ_PORT, 60)

mosq_client.subscribe(MOSQ_TOPIC)

print("[MOSQ] Listening...")
print("🚀 BridgeNow running...\n")

mosq_client.loop_forever()