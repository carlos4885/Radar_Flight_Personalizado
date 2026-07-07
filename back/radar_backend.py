from math import radians, sin, cos, sqrt, atan2
import requests
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("Client_ID_Open_Sky")
CLIENT_SECRET = os.getenv("API_KEY_Open_Sky")

api_key = os.getenv("MI_API_KEY")

# Rutas absolutas basadas en la ubicación de ESTE archivo, no en el directorio
# desde el que se ejecute "python radar_backend.py". Esto es lo que fallaba:
# las rutas relativas ('../front/...') dependían del cwd y se rompían según
# desde dónde lanzaras el script.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.join(BASE_DIR, '..', 'front')
STATIC_DIR = os.path.join(FRONT_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app)

# ========== CONFIGURACIÓN ==========
HOME_LAT = float(os.getenv("LATITUDE_HOME"))
HOME_LON = float(os.getenv("LONGITUDE_HOME"))

# Variables globales modificables
RADIO_KM = 30  
VELOCIDAD_MINIMA_KNOTS = 150

# ========== DICCIONARIO LOCAL DE AEROLÍNEAS ==========
AEROLINEAS = {
    "EWG": "Eurowings",
    "DLH": "Lufthansa",
    "IBE": "Iberia",
    "RYR": "Ryanair",
    "VLG": "Vueling",
    "AEA": "Air Europa",
    "BAW": "British Airways",
    "AFR": "Air France",
    "KLM": "KLM",
    "EZY": "easyJet",
    "EJU": "easyJet Europe",
    "EZS": "easyJet Switzerland",
    "NOR": "Norwegian",
    "SAS": "Scandinavian Airlines",
    "FIN": "Finnair",
    "TAP": "TAP Air Portugal",
    "SWR": "Swiss International",
    "AUA": "Austrian Airlines",
    "BEL": "Brussels Airlines",
    "LOT": "LOT Polish Airlines",
    "CSA": "Czech Airlines",
    "ELY": "El Al",
    "THY": "Turkish Airlines",
    "AEE": "Aegean Airlines",
    "AAL": "American Airlines",
    "UAL": "United Airlines",
    "DAL": "Delta Air Lines",
    "SWA": "Southwest Airlines",
    "JBU": "JetBlue",
    "ASA": "Alaska Airlines",
    "ACA": "Air Canada",
    "WJA": "WestJet",
    "AMX": "Aeroméxico",
    "UAE": "Emirates",
    "ETD": "Etihad Airways",
    "QTR": "Qatar Airways",
    "SVA": "Saudia",
    "CCA": "Air China",
    "CES": "China Eastern",
    "CSN": "China Southern",
    "ANA": "All Nippon Airways",
    "JAL": "Japan Airlines",
    "KAL": "Korean Air",
    "SIA": "Singapore Airlines",
    "THA": "Thai Airways",
    "MAS": "Malaysia Airlines",
    "FDX": "FedEx Express",
    "UPS": "UPS Airlines",
    "DHK": "DHL Air",
    "ABX": "ABX Air",
    "ANE": "Air Nostrum",
    "NAX": "Norwegian Air",
    "EXS": "Jet2.com",
    "TVS": "Smartwings",
    "CYL": "Cyprus Airways",
    "VJT": "VistaJet",
    "NJE": "NetJets Europe",
    "EJM": "Executive Jet Management",
    "GAJ": "Gama Aviation",
    "LNX": "Luxaviation",
    "SYG": "SkyGreece",
    "JFA": "Jetfly Aviation",
    "BKK": "Bangkok Airways",
    "OOL": "Vuelo privado",
    "XXX": "Vuelo privado",
    "YYY": "Vuelo privado",
}

# ========== FUNCIONES ==========
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

def obtener_aerolinea(callsign):
    if not callsign:
        return "Desconocida"
    codigo = callsign[:3]
    return AEROLINEAS.get(codigo, f"Código: {codigo}")

def obtener_modelo(icao24):
    return "Avión comercial"

def obtener_token():
    """Obtiene token de autenticación de OpenSky"""
    try:
        resp = requests.post(
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            timeout=10
        )
        return resp.json().get("access_token")
    except:
        return None

def aviones_cerca_de_punto(lat_centro, lon_centro, radio_km, velocidad_min_knots):
    delta_lat = radio_km / 111.0
    delta_lon = radio_km / (111.0 * cos(radians(lat_centro)))

    params = {
        "lamin": lat_centro - delta_lat,
        "lamax": lat_centro + delta_lat,
        "lomin": lon_centro - delta_lon,
        "lomax": lon_centro + delta_lon
    }

    try:
        token = obtener_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        resp = requests.get(
            "https://opensky-network.org/api/states/all", 
            params=params, 
            headers=headers,
            timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"Error: {e}")
        return []

    aviones_cerca = []
    velocidad_min_kmh = velocidad_min_knots * 1.852

    for state in data.get("states", []):
        callsign = state[1].strip() if state[1] else None
        lat = state[6]
        lon = state[5]
        velocidad_ms = state[9]
        velocidad_kmh = velocidad_ms * 3.6 if velocidad_ms else 0
        icao24 = state[0]
        heading = state[10] if state[10] is not None else 0

        if lat and lon and callsign:
            dist = haversine(lat_centro, lon_centro, lat, lon)
            if dist <= radio_km and velocidad_kmh >= velocidad_min_kmh:
                aviones_cerca.append({
                    "callsign": callsign,
                    "icao24": icao24,
                    "aerolinea": obtener_aerolinea(callsign),
                    "modelo": obtener_modelo(icao24),
                    "latitud": lat,
                    "longitud": lon,
                    "distancia_km": round(dist, 1),
                    "altitud_m": round(state[7], 1) if state[7] else 0,
                    "velocidad_kmh": round(velocidad_kmh),
                    "velocidad_knots": round(velocidad_kmh / 1.852),
                    "heading": heading,
                })

    return aviones_cerca

# ========== ENDPOINTS ==========
@app.route("/aviones")
def get_aviones():
    aviones = aviones_cerca_de_punto(HOME_LAT, HOME_LON, RADIO_KM, VELOCIDAD_MINIMA_KNOTS)
    return jsonify({
        "aviones": aviones,
        "total": len(aviones),
        "config": {
            "lat": HOME_LAT,
            "lon": HOME_LON,
            "radio_km": RADIO_KM,
            "velocidad_minima_knots": VELOCIDAD_MINIMA_KNOTS
        }
    })

@app.route("/config", methods=['GET'])
def get_config():
    """Devuelve la configuración actual"""
    return jsonify({
        "radio_km": RADIO_KM,
        "velocidad_minima_knots": VELOCIDAD_MINIMA_KNOTS
    })

@app.route("/config/radio", methods=['POST'])
def set_radio():
    """Modifica el radio en km"""
    global RADIO_KM
    try:
        data = request.get_json()
        nuevo_radio = data.get('radio_km')
        if nuevo_radio and 1 <= nuevo_radio <= 200:
            RADIO_KM = nuevo_radio
            return jsonify({"status": "ok", "radio_km": RADIO_KM})
        else:
            return jsonify({"status": "error", "message": "Radio debe estar entre 1 y 200 km"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/config/velocidad", methods=['POST'])
def set_velocidad():
    """Modifica la velocidad mínima en nudos"""
    global VELOCIDAD_MINIMA_KNOTS
    try:
        data = request.get_json()
        nueva_velocidad = data.get('velocidad_minima_knots')
        if nueva_velocidad and 0 <= nueva_velocidad <= 600:
            VELOCIDAD_MINIMA_KNOTS = nueva_velocidad
            return jsonify({"status": "ok", "velocidad_minima_knots": VELOCIDAD_MINIMA_KNOTS})
        else:
            return jsonify({"status": "error", "message": "Velocidad debe estar entre 0 y 600 nudos"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/")
def index():
    """Sirve el frontend desde la carpeta front/"""
    return send_file(os.path.join(FRONT_DIR, 'index.html'))

# ========== ARRANCAR ==========
if __name__ == "__main__":
    # Lee el puerto que te asigna Render, si no existe usa el 5000 (local)
    puerto = int(os.environ.get("PORT", 5000))
    
    print(f"\n✈️  Radar backend iniciado en el puerto {puerto}")
    print(f"   Endpoint: http://localhost:{puerto}/aviones")
    print(f"   Endpoint: http://localhost:{puerto}/config")
    print(f"   Interfaz: http://localhost:{puerto}/\n")
    
    # En producción desactivamos el debug por seguridad y rendimiento
    es_produccion = os.environ.get("PORT") is not None
    app.run(host="0.0.0.0", port=puerto, debug=not es_produccion)