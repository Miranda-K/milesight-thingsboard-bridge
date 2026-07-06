import time
import requests
import random
# --- CONFIGURATION ---
THINGSBOARD_HOST = "localhost"
THINGSBOARD_PORT = "8080"
THINGSBOARD_ACCESS_TOKEN = "nRkP0XDuE7k1yhfXMCIr"  
# ---------------------
url = f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/{THINGSBOARD_ACCESS_TOKEN}/telemetry"
print("🚀 Starting Milesight AM300 Simulator... Press Ctrl+C to stop.")
# Loop forever
while True:
    # Generate realistic shifting numbers to mimic a real room
    sim_temp = round(random.uniform(21.0, 26.0), 1)
    sim_humidity = round(random.uniform(40.0, 55.0), 1)
    sim_co2 = random.randint(450, 1100) # Simulates fresh air vs stuffy spikes
    # Bundle it into JSON format
    data_packet = {
        "temperature": sim_temp,
        "humidity": sim_humidity,
        "co2": sim_co2
    }
    try:
        # Shoot the data to your local ThingsBoard instance
        response = requests.post(url, json=data_packet)
        if response.status_code == 200:
            print(f"✅ Sent Data: Temp={sim_temp}°C, Humidity={sim_humidity}%, CO2={sim_co2}ppm")
        else:
            print(f"❌ Failed to send. Status code: {response.status_code}")
    except Exception as e:
        print(f"💥 Error connecting to ThingsBoard: {e}")

    # Wait 5 seconds before generating the next data point
    time.sleep(5)
