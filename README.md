# Dashboard Domotique MQTT

Application web en Python (FastAPI) pour piloter lumières, volets roulants, surveiller les températures et les détecteurs incendie d'une maison via MQTT.

## Fonctionnalités

- Contrôle des lumières par pièce (ON/OFF)
- Contrôle des volets roulants (OPEN/CLOSE)
- Température en temps réel par pièce
- Historique des températures en base SQLite
- Modale avec histogramme des températures (Chart.js)
- Détecteurs incendie avec état `NORMAL`/`ALERT`
- Bouton de test incendie par pièce

## Pièces supportées

- `salle_de_bain`
- `wc`
- `chambre1`
- `chambre2`
- `salon`
- `cuisine`

## Convention MQTT

Racine: `CONNECTLEARNING/DURAND/`

- `home/<room>/temperature` (telemetry)
- `home/<room>/light/set` (commande)
- `home/<room>/light/state` (etat)
- `home/<room>/shutter/set` (commande)
- `home/<room>/shutter/state` (etat)
- `home/<room>/fire/state` (etat incendie)
- `home/<room>/fire/test` (commande de test)

Payloads JSON recommandes:

- Temperature telemetry: `{"value": 22.4, "unit": "C", "ts": "2026-04-28T09:00:00Z"}`
- Light set: `{"on": true, "source": "ui", "ts": "..."}`
- Light state: `{"on": true, "ts": "..."}`
- Shutter set: `{"command": "OPEN"}` ou `{"command": "CLOSE"}`
- Shutter state: `{"state": "OPEN"}` ou `{"state": "CLOSE"}`
- Fire state: `{"state": "NORMAL"}` ou `{"state": "ALERT"}`
- Fire test: `{"test": true, "source": "ui", "ts": "..."}`

## Lancement local

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Puis ouvrir [http://localhost:8000](http://localhost:8000).

## Variables d'environnement

- `MQTT_HOST` (defaut `broker.emqx.io`)
- `MQTT_PORT` (defaut `8084`)
- `MQTT_TOPIC_ROOT` (defaut `CONNECTLEARNING/DURAND/`)
- `MQTT_CLIENT_ID` (defaut `durand-domotique-dashboard`)

## Tests

Depuis la racine du projet:

```bash
python3 -m pytest -q
```
