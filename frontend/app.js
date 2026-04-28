const roomsOrder = ["salle_de_bain", "wc", "chambre1", "chambre2", "salon", "cuisine"];
const roomLabels = {
  salle_de_bain: "Salle de bain",
  wc: "WC",
  chambre1: "Chambre 1",
  chambre2: "Chambre 2",
  salon: "Salon",
  cuisine: "Cuisine",
};

const state = { rooms: {} };
let chart;

const roomsEl = document.getElementById("rooms");
const modal = document.getElementById("temperatureModal");
const closeModalBtn = document.getElementById("closeModal");
const modalTitle = document.getElementById("modalTitle");
const alarmSound = document.getElementById("alarmSound");

closeModalBtn.addEventListener("click", () => modal.close());

async function callApi(path, method = "GET") {
  const res = await fetch(path, { method });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

function render() {
  roomsEl.innerHTML = "";
  roomsOrder.forEach((room) => {
    const roomState = state.rooms[room] || {};
    const card = document.createElement("article");
    card.className = "room-card";

    const fireClass = roomState.fire_state === "ALERT" ? "chip-alert" : "chip-ok";
    const tempText = typeof roomState.temperature === "number" ? `${roomState.temperature.toFixed(1)} °C` : "N/A";

    card.innerHTML = `
      <h3>${roomLabels[room]}</h3>
      <p class="metric">Température: <strong>${tempText}</strong></p>
      <p class="metric">Incendie: <span class="chip ${fireClass}">${roomState.fire_state || "NORMAL"}</span></p>
      <div class="controls">
        <button data-action="toggle-light" data-room="${room}">💡 ${roomState.light_on ? "Éteindre" : "Allumer"}</button>
        <button data-action="toggle-shutter" data-room="${room}">🪟 ${roomState.shutter_open ? "Fermer volet" : "Ouvrir volet"}</button>
        <button data-action="show-temp" data-room="${room}" class="ghost">🌡 Historique</button>
        <button data-action="fire-test" data-room="${room}" class="ghost">🚨 Test incendie</button>
      </div>
    `;
    roomsEl.appendChild(card);
  });
}

roomsEl.addEventListener("click", async (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const room = btn.dataset.room;
  const action = btn.dataset.action;
  try {
    if (action === "toggle-light") await callApi(`/api/rooms/${room}/light/toggle`, "POST");
    if (action === "toggle-shutter") await callApi(`/api/rooms/${room}/shutter/toggle`, "POST");
    if (action === "fire-test") await callApi(`/api/rooms/${room}/fire/test`, "POST");
    if (action === "show-temp") await showTemperatureModal(room);
  } catch (error) {
    console.error(error);
    alert("Action impossible pour le moment.");
  }
});

async function showTemperatureModal(room) {
  const now = new Date();
  const before = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  const query = `from=${encodeURIComponent(before.toISOString())}&to=${encodeURIComponent(now.toISOString())}&bucket=hour`;
  const data = await callApi(`/api/rooms/${room}/temperature/history?${query}`);

  modalTitle.textContent = `Historique température - ${roomLabels[room]}`;
  const labels = data.points.map((p) => new Date(p.measured_at).toLocaleTimeString("fr-FR"));
  const values = data.points.map((p) => p.value);
  const ctx = document.getElementById("temperatureChart");

  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Température (°C)", data: values }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  modal.showModal();
}

function applyRoomUpdate(room, roomState) {
  state.rooms[room] = { ...state.rooms[room], ...roomState };
  if (state.rooms[room].fire_state === "ALERT") {
    alarmSound.currentTime = 0;
    alarmSound.play().catch(() => {});
  }
  render();
}

function connectRealtime() {
  const wsProtocol = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${wsProtocol}://${location.host}/ws/state`);

  ws.onmessage = (evt) => {
    const message = JSON.parse(evt.data);
    if (message.type === "snapshot") {
      state.rooms = message.payload.rooms || {};
      render();
      return;
    }
    if (message.type === "room_state") {
      applyRoomUpdate(message.payload.room, message.payload.state);
      return;
    }
    if (message.type === "temperature") {
      const room = message.payload.room;
      applyRoomUpdate(room, { temperature: message.payload.value });
    }
  };

  ws.onopen = () => ws.send("ready");
  ws.onclose = () => setTimeout(connectRealtime, 1500);
}

async function bootstrap() {
  const data = await callApi("/api/rooms/state");
  state.rooms = data.rooms || {};
  render();
  connectRealtime();
}

bootstrap().catch((error) => {
  console.error(error);
  roomsEl.innerHTML = "<p>Erreur de chargement de l'interface.</p>";
});
