# Sistema de Domótica Hospitalaria — Almacén de Medicamentos

---

## Descripción del trabajo

Este proyecto implementa un sistema de domótica hospitalaria para el monitoreo y control de un almacén de medicamentos, usando una ESP32 programada en MicroPython y una interfaz web local para visualización en tiempo real.

El sistema monitorea las condiciones ambientales críticas para la conservación de medicamentos (temperatura y humedad), detecta presencia mediante ultrasonido para control automático de acceso, y permite apertura de emergencia mediante botón físico con interrupción por hardware.

### Funcionalidades principales

- Monitoreo continuo de temperatura y humedad con alertas visuales cuando los valores salen del rango seguro (20–25 °C / 40–60 %)
- Control automático de puerta (servo) por detección de presencia con sensor ultrasónico HC-SR04
- Apertura/cierre manual de emergencia mediante botón físico (interrupción IRQ)
- Visualización local en pantalla OLED SSD1306 con estado en tiempo real
- Dashboard web con gráficas, registro de eventos, alarmas visuales y control manual remoto
- Servidor HTTP embebido en la ESP32 con rutas para datos y control

---

## Lista de materiales

| Cantidad | Componente | Descripción |
|---|---|---|
| 1 | ESP32 DevKit | Microcontrolador principal |
| 1 | DHT11 | Sensor de temperatura y humedad |
| 1 | HC-SR04 | Sensor ultrasónico de distancia/presencia |
| 1 | Pulsador | Botón de apertura de emergencia |
| 1 | Servomotor SG90 | Simula apertura/cierre de puerta |
| 1 | LED rojo | Alerta de temperatura fuera de rango |
| 1 | LED azul | Alerta de humedad fuera de rango |
| 1 | OLED SSD1306 128×64 | Pantalla de visualización local (I2C) |
| 2 | Resistencia 10K Ω | Limitadora de corriente para LEDs |
| 1 | Protoboard | Montaje del circuito |
| — | Cables jumper | Conexiones |

---

## Pines usados en la ESP32

### Sensores (entrada)

| Dispositivo | Pin ESP32 | Tipo |
|---|---|---|
| DHT11 — DATA | GPIO 4 | Digital |
| HC-SR04 — TRIG | GPIO 5 | Digital salida |
| HC-SR04 — ECHO | GPIO 18 | Digital entrada |
| Botón emergencia | GPIO 15 | Digital (PULL_UP, IRQ) |

### Actuadores (salida)

| Dispositivo | Pin ESP32 | Tipo |
|---|---|---|
| Servomotor (puerta) | GPIO 23 | PWM (50 Hz) |
| LED rojo (alerta temp) | GPIO 19 | Digital |
| LED azul (alerta hum) | GPIO 17 | Digital |
| OLED SDA | GPIO 21 | I2C |
| OLED SCL | GPIO 22 | I2C |

### Alimentación

| Pin ESP32 | Conectar a |
|---|---|
| 3.3 V | VCC del DHT11, OLED |
| GND | GND de todos los componentes |
| 5 V (VIN) | VCC del servomotor, HC-SR04 |

---

## Archivos del proyecto

```
final digital/
├── main.py        → lógica principal: sensores, actuadores y servidor HTTP
├── ssd1306.py     → driver de la pantalla OLED (subir a la ESP32)
├── index.html     → estructura del dashboard web
├── style.css      → estilos visuales del dashboard
└── datos.js       → actualización dinámica, gráficas y control remoto
```

---

## Instrucciones de operación

### 1. Configuración de la ESP32

1. Conectar todos los sensores y actuadores según la tabla de pines.
2. Abrir Thonny y conectar la ESP32.
3. En `main.py`, editar las líneas 15–16 con el nombre y contraseña de la red WiFi:
   ```python
   SSID     = "NombreDetuRed"
   PASSWORD = "contraseña"
   ```
4. Subir `ssd1306.py` a la ESP32: `View → Files` → clic derecho → **Upload to /**.
5. Subir `main.py` a la ESP32 de la misma forma.
6. Ejecutar `main.py`. En la consola aparecerá la IP asignada, por ejemplo:
   ```
   ✓ Conectado — IP del dashboard: 192.168.1.100
   ```

### 2. Ejecución del dashboard web

1. Abrir la carpeta del proyecto en Visual Studio Code.
2. En `datos.js`, línea 5, cambiar la IP por la que apareció en Thonny:
   ```javascript
   const ESP32_IP = "http://192.168.1.100";
   ```
3. Abrir `index.html` con **Live Server** (clic derecho → *Open with Live Server*).
4. El dashboard se actualizará automáticamente cada 3 segundos.

### 3. Lógica de operación

**Control automático de puerta:**
- Si el HC-SR04 detecta un objeto a mas de 5 cm y menos de 10 cm durante 2 ciclos consecutivos → el servo abre la puerta a 90°.
- Al alejarse el objeto → el servo cierra la puerta a 0°.

**Botón de emergencia (interrupción IRQ):**
- Presionar el botón fuerza la apertura inmediata de la puerta.
- Presionar nuevamente la cierra.
- Desde el dashboard también se puede resetear el modo emergencia u activar.

**Alertas de temperatura y humedad:**
- Rango seguro: temperatura 20–25 °C, humedad 40–60 %.
- Si cualquier valor sale del rango: se enciende el LED correspondiente, aparece badge "FUERA DE RANGO" en el dashboard y se registra el evento.

**Control manual remoto (dashboard):**
- Botones *Abrir puerta* y *Cerrar puerta* envían comandos HTTP POST a la ESP32.

---

## Dashboard web

La interfaz muestra en tiempo real:

- **Temperatura** y **humedad** con indicador de estado (OK / fuera de rango)
- **Distancia** medida por el HC-SR04 con detección de presencia
- **Estado del botón** de emergencia
- **Estado de la puerta** (servo abierto/cerrado)
- **Estado de los LEDs** de alerta
- **Gráficas** de temperatura y humedad con historial de los últimos 12 puntos
- **Registro de eventos** con timestamp (últimas 30 entradas)
- **Banner de emergencia** animado cuando el modo emergencia está activo

---

## Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Microcontrolador | ESP32 + MicroPython |
| Comunicación | HTTP / socket TCP (servidor embebido en ESP32) |
| Frontend | HTML, CSS, JavaScript |
| Gráficas | Chart.js |
| Visualización local | OLED SSD1306 vía I2C |
| Repositorio | GitHub |

---

## Umbrales del sistema

| Variable | Mínimo | Máximo |
|---|---|---|
| Temperatura | 20 °C | 25 °C |
| Humedad | 40 % | 60 % |
| Distancia presencia | 5 cm | 10 cm |
| Tiempo confirmación presencia | 2 ciclos | — |
