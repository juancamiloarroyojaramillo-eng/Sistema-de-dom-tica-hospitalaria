// =====================================================
//  ALMACÉN DE MEDICAMENTOS — datos.js
//  Cambia ESP32_IP por la IP que aparece en Thonny
// =====================================================

const ESP32_IP = "http://172.20.10.2";   // ← CAMBIA ESTA IP

// ---------- GRÁFICAS ----------
const MAX_PUNTOS = 12;

const datosTemp = { labels: [], data: [] };
const datosHum  = { labels: [], data: [] };

function crearGrafica(id, label, color) {
  const ctx = document.getElementById(id).getContext("2d");
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: datosTemp.labels,
      datasets: [{
        label,
        data: id === "chartTemp" ? datosTemp.data : datosHum.data,
        borderColor: color,
        backgroundColor: color + "22",
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      animation: { duration: 400 },
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8b949e", font: { size: 10 } }, grid: { color: "#21262d" } },
        y: { ticks: { color: "#8b949e", font: { size: 11 } }, grid: { color: "#21262d" }, beginAtZero: false }
      }
    }
  });
}

const grafTemp = crearGrafica("chartTemp", "Temperatura °C", "#58a6ff");
const grafHum  = crearGrafica("chartHum",  "Humedad %",      "#3fb950");

function pushDato(arr, val) {
  const hora = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  arr.labels.push(hora);
  arr.data.push(val);
  if (arr.labels.length > MAX_PUNTOS) { arr.labels.shift(); arr.data.shift(); }
}

// ---------- ACTUALIZAR UI ----------
function set(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerText = val;
}

function actualizarUI(d) {
  // Sensores
  set("val-temp",  d.temperatura);
  set("val-hum",   d.humedad);
  set("val-dist",  d.distancia);
  set("val-emerg", d.emergencia ? "ACTIVA ⚠" : "Normal");

  // Badges temperatura
  const ct = document.getElementById("card-temp");
  const bt = document.getElementById("badge-temp");
  if (d.alerta_temp) {
    ct.className = "card alerta";
    bt.className = "card-badge alerta"; bt.innerText = "FUERA DE RANGO";
  } else {
    ct.className = "card ok";
    bt.className = "card-badge ok"; bt.innerText = "OK";
  }

  // Badges humedad
  const ch = document.getElementById("card-hum");
  const bh = document.getElementById("badge-hum");
  if (d.alerta_hum) {
    ch.className = "card alerta";
    bh.className = "card-badge alerta"; bh.innerText = "FUERA DE RANGO";
  } else {
    ch.className = "card ok";
    bh.className = "card-badge ok"; bh.innerText = "OK";
  }

  // Badge presencia
  const bp = document.getElementById("badge-pres");
  if (d.presencia === "Sí") {
    bp.className = "card-badge ok"; bp.innerText = "DETECTADA";
  } else {
    bp.className = "card-badge"; bp.innerText = "";
  }

  // Puerta
  const cpuerta = document.getElementById("card-puerta");
  set("val-puerta", d.puerta);
  cpuerta.className = "card " + (d.puerta === "Abierta" ? "abierta" : "");

  // LEDs
  const circT = document.getElementById("led-temp-circle");
  const circH = document.getElementById("led-hum-circle");
  circT.className = "led-circle " + (d.led_temp === "Encendido" ? "on-rojo" : "off");
  circH.className = "led-circle " + (d.led_hum  === "Encendido" ? "on-azul" : "off");
  set("val-led-temp", d.led_temp);
  set("val-led-hum",  d.led_hum);

  // Emergencia
  const cEmerg = document.getElementById("card-boton");
  const banner = document.getElementById("banner-emergencia");
  if (d.emergencia) {
    cEmerg.className = "card emerg";
    banner.classList.remove("oculto");
  } else {
    cEmerg.className = "card";
    banner.classList.add("oculto");
  }

  // Gráficas
  if (typeof d.temperatura === "number") {
    pushDato(datosTemp, d.temperatura);
    grafTemp.update();
  }
  if (typeof d.humedad === "number") {
    pushDato(datosHum, d.humedad);
    // Labels compartidos — sincronizar
    datosHum.labels = [...datosTemp.labels];
    grafHum.update();
  }

  // Registro de eventos
  if (d.eventos && d.eventos.length) {
    const box = document.getElementById("log-box");
    box.innerHTML = "";
    [...d.eventos].reverse().forEach(e => {
      const div = document.createElement("div");
      div.className = "log-entry" +
        (e.includes("ALERTA") || e.includes("EMERGENCIA") ? " alerta" :
         e.includes("Abierta") || e.includes("ABIERTA") ? " info" :
         e.includes("Cerrada") || e.includes("CERRADA") ? " ok" : "");
      div.innerText = e;
      box.appendChild(div);
    });
  }

  // Estado conexión
  document.getElementById("status-dot").className = "status-dot ok";
  set("status-label", "Conectado");
}

// ---------- CONTROL MANUAL ----------
function controlPuerta(accion) {
  fetch(`${ESP32_IP}/${accion}`, { method: "POST" })
    .then(r => r.json())
    .then(() => console.log(`Acción: ${accion}`))
    .catch(e => console.warn("Error control:", e));
}

function resetEmergencia() {
  fetch(`${ESP32_IP}/reset_emergencia`, { method: "POST" })
    .catch(e => console.warn("Error reset:", e));
}

// ---------- POLLING ----------
function actualizarDatos() {
  fetch(`${ESP32_IP}/datos`)
    .then(r => { if (!r.ok) throw new Error(); return r.json(); })
    .then(d => actualizarUI(d))
    .catch(() => {
      document.getElementById("status-dot").className = "status-dot error";
      set("status-label", "Sin conexión");
    });
}

setInterval(actualizarDatos, 3000);
actualizarDatos();
