# ============================================================
#  SISTEMA DE DOMÓTICA - ALMACÉN DE MEDICAMENTOS
#  Electrónica Digital 2 | ESP32 + MicroPython
# ============================================================
#  Sensores  : DHT11 (temp + humedad), HC-SR04 (presencia),
#              Botón (apertura manual de emergencia)
#  Actuadores: Servo (puerta), LED rojo (alerta temp),
#              LED azul (alerta humedad), OLED SSD1306
# ============================================================

from machine import Pin, PWM, time_pulse_us, I2C
from utime import sleep, sleep_us, ticks_ms, ticks_diff
import network
import socket
import ujson
import dht
from ssd1306 import SSD1306_I2C

# ============================================================
#  WIFI  — cambia estos datos al de tu red
# ============================================================
SSID     = "NombreDetuRed"
PASSWORD = "contraseña"

wifi = network.WLAN(network.STA_IF)
wifi.active(False)
sleep(0.5)
wifi.active(True)
print("Conectando a:", SSID)
wifi.connect(SSID, PASSWORD)

intentos = 0
while not wifi.isconnected() and intentos < 15:
    sleep(1)
    intentos += 1
    print(f"  intento {intentos}...")

if wifi.isconnected():
    ip = wifi.ifconfig()[0]
    print(f"\n✓ Conectado — IP del dashboard: {ip}")
else:
    ip = "sin_wifi"
    print("\n✗ Sin WiFi — el sistema físico sigue funcionando.")

# ============================================================
#  PINES
# ============================================================
# Sensores
TRIG        = Pin(5,  Pin.OUT)
ECHO        = Pin(18, Pin.IN)
dht_sensor  = dht.DHT11(Pin(4))         # DHT11, no DHT22
boton       = Pin(15, Pin.IN, Pin.PULL_UP)   # botón emergencia

# Actuadores
servo       = PWM(Pin(23), freq=50)
led_temp    = Pin(19, Pin.OUT)   # rojo  — alerta temperatura
led_hum     = Pin(17, Pin.OUT)   # azul  — alerta humedad
i2c         = I2C(0, scl=Pin(22), sda=Pin(21))
oled        = SSD1306_I2C(128, 64, i2c)

# ============================================================
#  UMBRALES PARA ALMACÉN DE MEDICAMENTOS
# ============================================================
TEMP_MIN        = 20
TEMP_MAX        = 25
HUM_MIN         = 40
HUM_MAX         = 60
DIST_UMBRAL     = 10   # cm — detección de presencia
TIEMPO_UMBRAL   = 2    # ciclos consecutivos para abrir por presencia

# ============================================================
#  ESTADO GLOBAL
# ============================================================
puerta_abierta      = False
tiempo_presencia    = 0
emergencia_activa   = False
ultimo_irq          = 0

registro_eventos    = []   # lista de strings, máx 30 entradas

datos_actuales = {
    "temperatura" : "--",
    "humedad"     : "--",
    "distancia"   : "--",
    "presencia"   : "No",
    "puerta"      : "Cerrada",
    "led_temp"    : "Apagado",
    "led_hum"     : "Apagado",
    "emergencia"  : False,
    "alerta_temp" : False,
    "alerta_hum"  : False,
    "eventos"     : []
}

# ============================================================
#  HELPERS
# ============================================================
def log(msg):
    """Agrega una entrada al registro con timestamp de ciclos."""
    ts = ticks_ms() // 1000
    h  = (ts // 3600) % 24
    m  = (ts % 3600) // 60
    s  = ts % 60
    entrada = f"{h:02d}:{m:02d}:{s:02d} — {msg}"
    registro_eventos.append(entrada)
    if len(registro_eventos) > 30:
        registro_eventos.pop(0)
    print(entrada)

def mover_servo(angulo):
    pulso = int((angulo * 2 / 180 + 0.5) / 20 * 1023)
    servo.duty(pulso)

def abrir_puerta(razon="presencia"):
    global puerta_abierta
    if not puerta_abierta:
        mover_servo(90)
        puerta_abierta = True
        log(f"Puerta ABIERTA ({razon})")

def cerrar_puerta():
    global puerta_abierta
    if puerta_abierta:
        mover_servo(0)
        puerta_abierta = False
        log("Puerta CERRADA")

def medir_distancia():
    TRIG.off()
    sleep_us(2)
    TRIG.on()
    sleep_us(10)
    TRIG.off()
    duracion = time_pulse_us(ECHO, 1, 30000)
    if duracion < 0:
        return 999
    return (duracion / 2) / 29.1

# ============================================================
#  INTERRUPCIÓN — Botón de emergencia
# ============================================================
def isr_boton(pin):
    global emergencia_activa, ultimo_irq
    ahora = ticks_ms()
    if ticks_diff(ahora, ultimo_irq) > 300:   # debounce 300 ms
        ultimo_irq = ahora
        emergencia_activa = not emergencia_activa
        # No podemos llamar funciones largas en IRQ; sólo se activa la bandera

boton.irq(trigger=Pin.IRQ_FALLING, handler=isr_boton)

# ============================================================
#  SERVIDOR WEB
# ============================================================
addr   = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(addr)
server.listen(1)
server.settimeout(0.05)
print("Servidor HTTP activo")

def responder_cors(client, body, ctype="application/json"):
    client.send("HTTP/1.1 200 OK\r\n")
    client.send(f"Content-Type: {ctype}\r\n")
    client.send("Access-Control-Allow-Origin: *\r\n")
    client.send("Connection: close\r\n\r\n")
    client.send(body)
    client.close()

# ============================================================
#  LOOP PRINCIPAL
# ============================================================
log("Sistema iniciado — Almacén de Medicamentos")
oled.fill(0)
oled.text("Iniciando...", 0, 28)
oled.show()
sleep(1)

while True:

    # ----------------------------------------------------------
    #  1. ATENDER PETICIONES HTTP
    # ----------------------------------------------------------
    try:
        client, _ = server.accept()
        req = client.recv(1024).decode()

        if "GET /datos" in req:
            datos_actuales["eventos"] = registro_eventos[-10:]
            responder_cors(client, ujson.dumps(datos_actuales))

        elif "POST /abrir" in req:
            abrir_puerta("manual web")
            responder_cors(client, '{"ok":true}')

        elif "POST /cerrar" in req:
            cerrar_puerta()
            responder_cors(client, '{"ok":true}')

        elif "POST /reset_emergencia" in req:
            emergencia_activa = False
            log("Emergencia reseteada desde web")
            responder_cors(client, '{"ok":true}')

        else:
            client.close()
    except:
        pass

    # ----------------------------------------------------------
    #  2. GESTIONAR EMERGENCIA (bandera de IRQ)
    # ----------------------------------------------------------
    if emergencia_activa:
        abrir_puerta("EMERGENCIA botón")
        led_temp.value(1)
        led_hum.value(1)
    # (si se desactiva, los actuadores se normalizan en el ciclo)

    # ----------------------------------------------------------
    #  3. LECTURA DE DISTANCIA (presencia)
    # ----------------------------------------------------------
    distancia = medir_distancia()
    hay_presencia = distancia < DIST_UMBRAL

    if hay_presencia:
        tiempo_presencia += 1
    else:
        if tiempo_presencia > 0:
            tiempo_presencia = 0
        if puerta_abierta and not emergencia_activa:
            cerrar_puerta()

    if tiempo_presencia >= TIEMPO_UMBRAL and not puerta_abierta and not emergencia_activa:
        abrir_puerta("presencia detectada")

    # ----------------------------------------------------------
    #  4. LECTURA DHT11 (temperatura y humedad)
    # ----------------------------------------------------------
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum  = dht_sensor.humidity()

        alerta_temp = temp < TEMP_MIN or temp > TEMP_MAX
        alerta_hum  = hum  < HUM_MIN  or hum  > HUM_MAX

        if not emergencia_activa:
            led_temp.value(int(alerta_temp))
            led_hum.value(int(alerta_hum))

        if alerta_temp and not datos_actuales.get("alerta_temp"):
            log(f"ALERTA: Temperatura fuera de rango ({temp}°C)")
        if alerta_hum and not datos_actuales.get("alerta_hum"):
            log(f"ALERTA: Humedad fuera de rango ({hum}%)")

        # ------ OLED ------
        oled.fill(0)
        oled.text("Almacen Medic.", 0, 0)
        oled.text(f"Temp: {temp}C", 0, 14)
        oled.text(f"Hum:  {hum}%", 0, 26)
        oled.text(f"Dist: {int(distancia)}cm", 0, 38)
        estado_puerta = "Abierta" if puerta_abierta else "Cerrada"
        oled.text(f"Puerta:{estado_puerta}", 0, 50)
        if emergencia_activa:
            oled.text("!! EMERGENCIA !!", 0, 0)   # sobreescribe
        oled.show()

        # ------ Actualizar diccionario ------
        datos_actuales.update({
            "temperatura" : round(temp, 1),
            "humedad"     : round(hum, 1),
            "distancia"   : round(distancia, 1),
            "presencia"   : "Sí" if hay_presencia else "No",
            "puerta"      : "Abierta" if puerta_abierta else "Cerrada",
            "led_temp"    : "Encendido" if alerta_temp else "Apagado",
            "led_hum"     : "Encendido" if alerta_hum  else "Apagado",
            "emergencia"  : emergencia_activa,
            "alerta_temp" : alerta_temp,
            "alerta_hum"  : alerta_hum,
        })

    except Exception as e:
        print("Error DHT11:", e)

    sleep(1)
