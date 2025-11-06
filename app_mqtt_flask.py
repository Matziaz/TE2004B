from flask import Flask, render_template_string
from gtts import gTTS
import os, threading
import paho.mqtt.client as mqtt

app = Flask(__name__)

current_color = "#222222"
last_message = "Waiting for MQTT data..."

def speak(text):
    """Convert text to speech using gTTS and play it."""
    tts = gTTS(text, lang='en')
    tts.save("voice.mp3")
    os.system("mpg123 voice.mp3 > /dev/null 2>&1")

# --- Simple HTML UI ---
html = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Robot Control Panel</title>
<style>
body { background:#121212; color:white; font-family:sans-serif; text-align:center; }
.color-box { width:200px; height:200px; margin:50px auto; border-radius:15px; background: {{ color }}; box-shadow: 0 0 20px {{ color }}; }
</style>
</head>
<body>
<h1>Robot Control Panel</h1>
<div class="color-box"></div>
<h2>Last message: {{ message }}</h2>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html, color=current_color, message=last_message)

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code:", rc)
    client.subscribe("robot/control")

def on_message(client, userdata, msg):
    global current_color, last_message
    payload = msg.payload.decode().strip().lower()
    print(f"Received MQTT message: {payload}")
    last_message = payload

    if payload.startswith("color="):
        colors = {
            "red": "#ff0000",
            "green": "#00ff00",
            "blue": "#0000ff",
            "yellow": "#ffff00"
        }
        color = payload.split("=")[1]
        print(f"Received color command: {color}")
        print(f"Color exists in dictionary: {color in colors}")
        current_color = colors.get(color, "#ffffff")
        print(f"Set color to: {current_color}")
        speak(f"Color {color} activated")
    elif payload.startswith("speak="):
        text = payload.split("=", 1)[1]
        speak(text)
    else:
        speak(f"Message received: {payload}")

# --- MQTT Setup ---
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect("localhost", 1883, 60)

# Run MQTT loop in a background thread
threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()

# --- Run Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
