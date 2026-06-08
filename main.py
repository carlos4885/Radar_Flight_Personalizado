from math import radians, sin, cos, sqrt, atan2
import requests

# ========== CONFIGURACIÓN ==========
HOME_LAT = 40.466555
HOME_LON = -3.593562
RADIO_KM = 30
VELOCIDAD_MINIMA_KNOTS = 150

# ========== DICCIONARIO LOCAL DE AEROLÍNEAS ==========
AEROLINEAS = {
    # Europa
    "EWG": "Eurowings",
    "DLH": "Lufthansa",
    "IBE": "Iberia",
    "RYR": "Ryanair",
    "VLG": "Vueling",
    "AEA": "Air Europa",
    "BAW": "British Airways",
    "AFR": "Air France",
    "KLM": "KLM",
    "SWA": "Southwest Airlines",
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
    
    # América
    "AAL": "American Airlines",
    "UAL": "United Airlines",
    "DAL": "Delta Air Lines",
    "SWA": "Southwest Airlines",
    "JBU": "JetBlue",
    "ASA": "Alaska Airlines",
    "ACA": "Air Canada",
    "WJA": "WestJet",
    "AMX": "Aeroméxico",
    
    # Asia y Medio Oriente
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
    
    # Carga
    "FDX": "FedEx Express",
    "UPS": "UPS Airlines",
    "DHK": "DHL Air",
    "ABX": "ABX Air",
    
    # España adicional
    "ANE": "Air Nostrum",
    "NAX": "Norwegian Air",
    "EXS": "Jet2.com",
    "TVS": "Smartwings",
    "CYL": "Cyprus Airways",
    
    #PRIVADA 

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
    """Obtiene aerolínea del diccionario local"""
    if not callsign:
        return "Desconocida"
    
    # Extraer código ICAO (primeros 3 caracteres)
    codigo = callsign[:3]
    return AEROLINEAS.get(codigo, f"Código: {codigo}")

def obtener_modelo(icao24):
    """Obtiene modelo del avión (simplificado)"""
    # Por ahora devuelve genérico
    # En futuro se puede ampliar con más datos
    return "Avión comercial"

def aviones_cerca_de_punto(lat_centro, lon_centro, radio_km, velocidad_min_knots=150):
    delta_lat = radio_km / 111.0
    delta_lon = radio_km / (111.0 * cos(radians(lat_centro)))
    
    params = {
        "lamin": lat_centro - delta_lat,
        "lamax": lat_centro + delta_lat,
        "lomin": lon_centro - delta_lon,
        "lomax": lon_centro + delta_lon
    }
    
    print(f"Buscando aviones...")
    
    try:
        resp = requests.get("https://opensky-network.org/api/states/all", params=params, timeout=10)
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
        
        if lat and lon and callsign:
            dist = haversine(lat_centro, lon_centro, lat, lon)
            
            if dist <= radio_km and velocidad_kmh >= velocidad_min_kmh:
                aviones_cerca.append({
                    "callsign": callsign,
                    "aerolinea": obtener_aerolinea(callsign),
                    "modelo": obtener_modelo(icao24),
                    "latitud": lat,
                    "longitud": lon,
                    "distancia_km": round(dist, 1),
                    "altitud_m": round(state[7], 1) if state[7] else 0,
                    "velocidad_kmh": round(velocidad_kmh),
                })
    
    return aviones_cerca

# ========== EJECUTAR ==========
if __name__ == "__main__":
    print(f"\n✈️ Buscando aviones cerca de tu casa...")
    print(f"Radio: {RADIO_KM} km | Mínimo: {VELOCIDAD_MINIMA_KNOTS} nudos\n")
    
    aviones = aviones_cerca_de_punto(HOME_LAT, HOME_LON, RADIO_KM, VELOCIDAD_MINIMA_KNOTS)
    
    print(f"\n✅ Aviones encontrados: {len(aviones)}")
    print("=" * 70)
    
    for avion in aviones:
        print(f"\n✈️ {avion['callsign']}")
        print(f"   🏢 Aerolínea: {avion['aerolinea']}")
        print(f"   📦 Modelo: {avion['modelo']}")
        print(f"   📍 Distancia: {avion['distancia_km']} km")
        print(f"   📏 Altitud: {avion['altitud_m']} m")
        print(f"   💨 Velocidad: {avion['velocidad_kmh']} km/h")
        print(f"   🗺️ Posición: {avion['latitud']:.4f}, {avion['longitud']:.4f}")