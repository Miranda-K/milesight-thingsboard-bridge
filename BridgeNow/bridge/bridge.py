import json
import time
import paho.mqtt.client as mqtt
import threading

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
bridge_start = time.time()
messages_forwarded = 0
last_packet = None
BRIDGE_VERSION = "1.0.0"
STATUS_DEVICE = "BridgeNow Status"

# ------------------------
# MQTT clients
# ------------------------
tb_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mosq_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# ------------------------
# DEFINE ALL FUNCTIONS FIRST
# ------------------------

def publish_status():
    uptime = int(time.time() - bridge_start)
    values = {
        "bridgeRunning": True,
        "gatewayConnected": gateway_connected,
        "connectedDevices": len(connected_devices),
        "messagesForwarded": messages_forwarded,
        "bridgeVersion": BRIDGE_VERSION,
        "uptimeSeconds": uptime
    }
    
    if last_packet:
        values["secondsSinceLastPacket"] = round(time.time() - last_packet, 1)
        
    payload = {
        STATUS_DEVICE: [values]
    }
    
    tb_client.publish(
        "v1/gateway/telemetry",
        json.dumps(payload),
        qos=1
    )

def status_loop():
    while True:
        publish_status()
        time.sleep(5)

def connect_device(device_name):
    if device_name in connected_devices:
        return True
        
    payload = {"device": device_name}
    print(f"[TB] Connecting child device '{device_name}'...")
    
    info = tb_client.publish("v1/gateway/connect", json.dumps(payload), qos=1)
    
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        print("[TB] Failed to publish child device connection.")
        return False
        
    connected_devices.add(device_name)
    print("[TB] Child device connected.")
    return True

def forward_telemetry(device_name, values):
    payload = {device_name: [values]}
    print("[TB] Sending telemetry:")
    print(json.dumps(payload, indent=2))
    tb_client.publish("v1/gateway/telemetry", json.dumps(payload), qos=1)
    publish_status()

def on_tb_connect(client, userdata, flags, reason_code, properties):
    global gateway_connected
    if reason_code == 0:
        gateway_connected = True
        print("[TB] Gateway connected successfully.")
        client.subscribe("v1/gateway/rpc")
        print("[TB] Listening for downlink commands on v1/gateway/rpc...")
    else:
        print(f"[TB] Connection failed: {reason_code}")

def on_tb_disconnect(client, userdata, flags, reason_code, properties):
    global gateway_connected
    gateway_connected = False
    connected_devices.clear()
    print(f"[TB] Gateway disconnected: {reason_code}")

def on_tb_publish(client, userdata, mid, reason_code, properties):
    pass # Print statement muted to prevent log spam

def on_tb_message(client, userdata, msg):
    print("\n========== DOWNLINK RECEIVED FROM THINGSBOARD ==========")
    try:
        payload = json.loads(msg.payload.decode())
        print(json.dumps(payload, indent=2))
        
        DOWNLINK_TOPIC = "gateway/downlink" 
        mosq_client.publish(DOWNLINK_TOPIC, json.dumps(payload))
        print(f"[MOSQ] Forwarded downlink to local gateway on topic: {DOWNLINK_TOPIC}")

        tb_client.publish(
            "v1/gateway/rpc", 
            json.dumps({"device": payload["device"], "id": payload["data"]["id"], "data": {"success": True}})
        )
    except Exception as e:
        print("[ERROR parsing downlink]", e)

def on_message(client, userdata, msg):
    print("\n========== MESSAGE RECEIVED ==========")
    try:
        data = json.loads(msg.payload.decode())
        
        global messages_forwarded
        global last_packet
        messages_forwarded += 1
        last_packet = time.time()
        
        print(json.dumps(data, indent=2))
        
        device_name = data.get("deviceName", "UNKNOWN_DEVICE")
        
        values = {
            k: v
            for k, v in data.items()
            if k not in ["deviceName", "devEUI", "devEui", "applicationID"]
        }
        
        if connect_device(device_name):
            forward_telemetry(device_name, values)
            
    except Exception as e:
        print("[ERROR]", e)

def on_mosq_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[MOSQ] Connected successfully.")
        client.subscribe(MOSQ_TOPIC)
        print(f"[MOSQ] Subscribed to {MOSQ_TOPIC}")
    else:
        print(f"[MOSQ] Connection failed: {reason_code}")

def on_mosq_disconnect(client, userdata, flags, reason_code, properties):
    print(f"[MOSQ] Disconnected: {reason_code}")

# ------------------------
# MAIN EXECUTION & CLIENT SETUP
# ------------------------
tb_client.username_pw_set(config["thingsboard"]["gateway_token"])

tb_client.on_connect = on_tb_connect
tb_client.on_disconnect = on_tb_disconnect
tb_client.on_publish = on_tb_publish
tb_client.on_message = on_tb_message

tb_client.reconnect_delay_set(min_delay=1, max_delay=30)

print("[TB] Connecting to ThingsBoard...")
tb_client.connect_async(TB_HOST, TB_PORT, 60)
tb_client.loop_start()
print("[TB] Connection initiated.")

print("[TB] Waiting for gateway connection...")
while not gateway_connected:
    time.sleep(0.2)

print("[TB] Gateway ready.")

print("[TB] Registering BridgeNow Status device...")
tb_client.publish(
    "v1/gateway/connect",
    json.dumps({"device": STATUS_DEVICE}),
    qos=1
)

# Start status loop thread safely now that publish_status is defined
threading.Thread(target=status_loop, daemon=True).start()

# ------------------------
# Mosquitto setup
# ------------------------
mosq_client.on_connect = on_mosq_connect
mosq_client.on_disconnect = on_mosq_disconnect
mosq_client.on_message = on_message

print("[MOSQ] Connecting...")
mosq_client.connect(MOSQ_HOST, MOSQ_PORT, 60)

print("[MOSQ] Listening...")
print("🚀 BridgeNow running...\n")

mosq_client.loop_forever()