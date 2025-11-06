from flask import Flask, render_template_string, jsonify
from gtts import gTTS
import os, threading, time
import paho.mqtt.client as mqtt
import speech_recognition as sr
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: RPi.GPIO not available. Running in simulation mode.")

app = Flask(__name__)

# --- GPIO Configuration ---
if GPIO_AVAILABLE:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

# Define GPIO pins for your components
GPIO_PINS = {
    'led_red': 17,
    'led_green': 27,
    'led_blue': 22,
    'motor1': 23,
    'motor2': 24,
    'servo': 18
}

# Initialize GPIO pins
if GPIO_AVAILABLE:
    for pin in GPIO_PINS.values():
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

# Global variables
current_color = "#222222"
last_message = "Waiting for commands..."
gpio_status = {name: False for name in GPIO_PINS.keys()}
voice_active = False

def speak(text):
    """Convert text to speech using gTTS and play it."""
    try:
        tts = gTTS(text, lang='es')  # Changed to Spanish
        tts.save("voice.mp3")
        os.system("mpg123 voice.mp3 > /dev/null 2>&1")
    except Exception as e:
        print(f"Speech error: {e}")

def control_gpio(component, state):
    """Control a GPIO component."""
    if component in GPIO_PINS:
        pin = GPIO_PINS[component]
        if GPIO_AVAILABLE:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        gpio_status[component] = state
        status = "encendido" if state else "apagado"
        speak(f"{component.replace('_', ' ')} {status}")
        return True
    return False

def process_voice_command(command):
    """Process voice commands for GPIO and system control."""
    global current_color, last_message
    
    command = command.lower()
    last_message = f"Voice: {command}"
    
    # LED commands
    if "led rojo" in command or "rojo" in command:
        state = "encender" in command or "activar" in command
        control_gpio('led_red', state)
        current_color = "#ff0000" if state else "#222222"
    
    elif "led verde" in command or "verde" in command:
        state = "encender" in command or "activar" in command
        control_gpio('led_green', state)
        current_color = "#00ff00" if state else "#222222"
    
    elif "led azul" in command or "azul" in command:
        state = "encender" in command or "activar" in command
        control_gpio('led_blue', state)
        current_color = "#0000ff" if state else "#222222"
    
    # Motor commands
    elif "motor uno" in command or "motor 1" in command:
        state = "encender" in command or "activar" in command
        control_gpio('motor1', state)
    
    elif "motor dos" in command or "motor 2" in command:
        state = "encender" in command or "activar" in command
        control_gpio('motor2', state)
    
    elif "servo" in command:
        state = "encender" in command or "activar" in command
        control_gpio('servo', state)
    
    # All off command
    elif "apagar todo" in command or "todo apagado" in command:
        for component in GPIO_PINS.keys():
            control_gpio(component, False)
        current_color = "#222222"
        speak("Todos los componentes apagados")
    
    # Status command
    elif "estado" in command or "status" in command:
        active = [name for name, status in gpio_status.items() if status]
        if active:
            speak(f"Activos: {', '.join(active)}")
        else:
            speak("Todos los componentes están apagados")
    
    else:
        speak("Comando no reconocido")

def voice_recognition_loop():
    """Continuous voice recognition loop."""
    global voice_active, last_message
    
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 4000
    recognizer.dynamic_energy_threshold = True
    
    while True:
        if not voice_active:
            time.sleep(1)
            continue
        
        try:
            with sr.Microphone() as source:
                print("Listening for commands...")
                last_message = "Escuchando..."
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            try:
                command = recognizer.recognize_google(audio, language='es-MX')
                print(f"Recognized: {command}")
                process_voice_command(command)
            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError as e:
                print(f"Recognition error: {e}")
                last_message = "Error de reconocimiento"
                
        except Exception as e:
            print(f"Voice loop error: {e}")
            time.sleep(2)

# --- HTML UI ---
html = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Control Robot Raspberry Pi</title>
<style>
body { 
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white; 
    font-family: 'Segoe UI', sans-serif; 
    text-align: center;
    margin: 0;
    padding: 20px;
}
.container { max-width: 1200px; margin: 0 auto; }
h1 { 
    font-size: 2.5em; 
    margin: 20px 0;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
}
.color-box { 
    width: 250px; 
    height: 250px; 
    margin: 30px auto; 
    border-radius: 20px; 
    background: {{ color }}; 
    box-shadow: 0 0 40px {{ color }}, 0 10px 30px rgba(0,0,0,0.5);
    transition: all 0.3s ease;
}
.status { 
    background: rgba(255,255,255,0.1); 
    padding: 20px; 
    border-radius: 15px;
    margin: 20px 0;
    backdrop-filter: blur(10px);
}
.controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin: 30px 0;
}
.btn {
    padding: 15px 25px;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: bold;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.4); }
.btn-red { background: #e74c3c; color: white; }
.btn-green { background: #2ecc71; color: white; }
.btn-blue { background: #3498db; color: white; }
.btn-yellow { background: #f39c12; color: white; }
.btn-purple { background: #9b59b6; color: white; }
.btn-danger { background: #c0392b; color: white; }
.voice-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px 40px;
    font-size: 18px;
    margin: 20px 0;
}
.voice-active { animation: pulse 1.5s infinite; }
@keyframes pulse {
    0%, 100% { box-shadow: 0 0 20px #667eea; }
    50% { box-shadow: 0 0 40px #667eea; }
}
.gpio-status {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 10px;
    margin: 20px 0;
}
.gpio-item {
    background: rgba(255,255,255,0.05);
    padding: 15px;
    border-radius: 10px;
    border: 2px solid transparent;
}
.gpio-on { border-color: #2ecc71; background: rgba(46,204,113,0.1); }
.gpio-off { border-color: #e74c3c; background: rgba(231,76,60,0.1); }
</style>
</head>
<body>
<div class="container">
    <h1>🤖 Control Robot Raspberry Pi</h1>
    
    <div class="color-box" id="colorBox"></div>
    
    <div class="status">
        <h2 id="lastMessage">{{ message }}</h2>
    </div>
    
    <button class="btn voice-btn" onclick="toggleVoice()" id="voiceBtn">
        🎤 Activar Control por Voz
    </button>
    
    <div class="controls">
        <button class="btn btn-red" onclick="sendCommand('led_red', 'on')">LED Rojo ON</button>
        <button class="btn btn-danger" onclick="sendCommand('led_red', 'off')">LED Rojo OFF</button>
        <button class="btn btn-green" onclick="sendCommand('led_green', 'on')">LED Verde ON</button>
        <button class="btn btn-danger" onclick="sendCommand('led_green', 'off')">LED Verde OFF</button>
        <button class="btn btn-blue" onclick="sendCommand('led_blue', 'on')">LED Azul ON</button>
        <button class="btn btn-danger" onclick="sendCommand('led_blue', 'off')">LED Azul OFF</button>
        <button class="btn btn-yellow" onclick="sendCommand('motor1', 'on')">Motor 1 ON</button>
        <button class="btn btn-danger" onclick="sendCommand('motor1', 'off')">Motor 1 OFF</button>
        <button class="btn btn-purple" onclick="sendCommand('all', 'off')">APAGAR TODO</button>
    </div>
    
    <h3>Estado GPIO</h3>
    <div class="gpio-status" id="gpioStatus"></div>
</div>

<script>
let voiceActive = false;

function toggleVoice() {
    fetch('/voice/toggle', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            voiceActive = data.active;
            const btn = document.getElementById('voiceBtn');
            if(voiceActive) {
                btn.textContent = '🎤 Desactivar Control por Voz';
                btn.classList.add('voice-active');
            } else {
                btn.textContent = '🎤 Activar Control por Voz';
                btn.classList.remove('voice-active');
            }
        });
}

function sendCommand(component, action) {
    fetch('/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({component, action})
    }).then(r => r.json()).then(updateStatus);
}

function updateStatus(data) {
    document.getElementById('colorBox').style.background = data.color;
    document.getElementById('colorBox').style.boxShadow = `0 0 40px ${data.color}`;
    document.getElementById('lastMessage').textContent = data.message;
    
    const gpioDiv = document.getElementById('gpioStatus');
    gpioDiv.innerHTML = '';
    for(let [name, status] of Object.entries(data.gpio)) {
        const item = document.createElement('div');
        item.className = `gpio-item ${status ? 'gpio-on' : 'gpio-off'}`;
        item.innerHTML = `<strong>${name}</strong><br>${status ? '✅ ON' : '❌ OFF'}`;
        gpioDiv.appendChild(item);
    }
}

// Auto-refresh status every 2 seconds
setInterval(() => {
    fetch('/status').then(r => r.json()).then(updateStatus);
}, 2000);
</script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(html, color=current_color, message=last_message)

@app.route('/status')
def status():
    return jsonify({
        'color': current_color,
        'message': last_message,
        'gpio': gpio_status,
        'voice_active': voice_active
    })

@app.route('/control', methods=['POST'])
def control():
    from flask import request
    data = request.json
    component = data.get('component')
    action = data.get('action')
    
    global current_color, last_message
    
    if component == 'all' and action == 'off':
        for comp in GPIO_PINS.keys():
            control_gpio(comp, False)
        current_color = "#222222"
        last_message = "Todos los componentes apagados"
    else:
        state = action == 'on'
        if control_gpio(component, state):
            if 'led' in component:
                colors = {'led_red': '#ff0000', 'led_green': '#00ff00', 'led_blue': '#0000ff'}
                current_color = colors.get(component, '#222222') if state else '#222222'
            last_message = f"{component} {action}"
    
    return jsonify({
        'color': current_color,
        'message': last_message,
        'gpio': gpio_status
    })

@app.route('/voice/toggle', methods=['POST'])
def toggle_voice():
    global voice_active
    voice_active = not voice_active
    status = "activado" if voice_active else "desactivado"
    speak(f"Control por voz {status}")
    return jsonify({'active': voice_active})

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code:", rc)
    client.subscribe("robot/control")

def on_message(client, userdata, msg):
    global current_color, last_message
    payload = msg.payload.decode().strip().lower()
    print(f"Received MQTT message: {payload}")
    last_message = f"MQTT: {payload}"

    if payload.startswith("color="):
        colors = {"red": "#ff0000", "green": "#00ff00", "blue": "#0000ff", "yellow": "#ffff00"}
        color = payload.split("=")[1]
        current_color = colors.get(color, "#ffffff")
        speak(f"Color {color} activado")
    elif payload.startswith("gpio="):
        # Format: gpio=led_red:on
        parts = payload.split("=")[1].split(":")
        if len(parts) == 2:
            component, state = parts
            control_gpio(component, state == 'on')
    elif payload.startswith("speak="):
        text = payload.split("=", 1)[1]
        speak(text)

# --- MQTT Setup ---
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect("localhost", 1883, 60)
    threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()
    print("MQTT connected successfully")
except Exception as e:
    print(f"MQTT connection failed: {e}")

# --- Start Voice Recognition Thread ---
voice_thread = threading.Thread(target=voice_recognition_loop, daemon=True)
voice_thread.start()

# --- Cleanup on exit ---
def cleanup():
    if GPIO_AVAILABLE:
        GPIO.cleanup()

import atexit
atexit.register(cleanup)

# --- Run Flask ---
if __name__ == "__main__":
    print("=" * 50)
    print("Robot Control System Starting...")
    print(f"GPIO Available: {GPIO_AVAILABLE}")
    print("Web Interface: http://0.0.0.0:8080")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8080, debug=False)