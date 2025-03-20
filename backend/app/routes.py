# app/routes.py
from fastapi import APIRouter
import requests

router = APIRouter()

SYNGENTA_WEATHER_API = "https://services.cehub.syngenta-ais.com/api/Forecast/ShortRangeForecastDaily"
# key 6
API_KEY = "1f3f9b58-f6d5-4ddc-8891-fa8ee79890ee"

@router.get("/")
async def read_root():
    return {"message": "Welcome to the Hackathon API!"}

@router.get("/weather/{date}/{lat}/{lon}")
def get_weather(date: str, lat: float, lon: float):
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": date,
        "endDate": date,
        "supplier": "Meteoblue",
        "measureLabel": "TempAir_DailyAvg (C);Precip_DailySum (mm);Soilmoisture_0to10cm_DailyAvg (vol%)",
        "format": "json",
        "ApiKey": API_KEY
    }
    response = requests.get(SYNGENTA_WEATHER_API, params=params)

    if response.status_code == 200:
        data = response.json()
        print(data)
        return {
            "temperature": data[0].get("dailyValue", "N/A"),
            "rainfall": data[1].get("dailyValue", "N/A"),
            "soil_moisture": data[2].get("dailyValue", "N/A")
        }
    else:
        return {"error": "Could not fetch weather data"}

@router.get("/risk/heat/{crop}/{date}/{lat}/{lon}")
def get_heat_risk(date: str, crop: str, lat: float, lon: float):

    crop_temp_limits = {
            "soybean": {"TMaxOptimum": 32, "TMaxLimit": 45},
            "corn": {"TMaxOptimum": 33, "TMaxLimit": 44},
            "cotton": {"TMaxOptimum": 32, "TMaxLimit": 38},
            "rice": {"TMaxOptimum": 32, "TMaxLimit": 38},
            "wheat": {"TMaxOptimum": 25, "TMaxLimit": 32},
        }

    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": date,
        "endDate": date,
        "supplier": "Meteoblue",
        "measureLabel": "TempAir_DailyMax (C)",
        "format": "json",
        "ApiKey": API_KEY
    }
    response = requests.get(SYNGENTA_WEATHER_API, params=params)

    if response.status_code != 200:
        return {"error": "Wetterdaten konnten nicht abgerufen werden."}

    data = response.json()
    TMAX = float(data[0].get("dailyValue", "N/A"))  # Extrahiere maximale Temperatur

    # Temperaturgrenzen für die gewählte Kulturpflanze
    TMaxOptimum = crop_temp_limits[crop.lower()]["TMaxOptimum"]
    TMaxLimit = crop_temp_limits[crop.lower()]["TMaxLimit"]

    # Berechnung des Diurnal Heat Stress
    if TMAX <= TMaxOptimum:
        heat_stress = 0
    elif TMaxOptimum < TMAX < TMaxLimit:
        heat_stress = 9 * ((TMAX - TMaxOptimum) / (TMaxLimit - TMaxOptimum))
    else:
        heat_stress = 9


    return {
                "heat_stress": int(heat_stress)
       }

@router.get("/risk/frost/{crop}/{date}/{lat}/{lon}")
def get_frost_risk(date: str, crop: str, lat: float, lon: float):

    crop_temp_limits = {
        "soybean": {"TMinNoFrost": 4, "TMinFrost": -3},
        "corn": {"TMinNoFrost": 4, "TMinFrost": -3},
        "cotton": {"TMinNoFrost": 4, "TMinFrost": -3},
        "rice": {"TMinNoFrost": None, "TMinFrost": None},  # Kein Frost-Risiko definiert
        "wheat": {"TMinNoFrost": None, "TMinFrost": None},  # Kein Frost-Risiko definiert
    }

    # Falls die Pflanze keinen Frost-Risiko-Wert hat, gib 0 zurück
    if crop.lower() not in crop_temp_limits or crop_temp_limits[crop.lower()]["TMinNoFrost"] is None:
        return 0

    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": date,
        "endDate": date,
        "supplier": "Meteoblue",
        "measureLabel": "TempAir_DailyMin (C)",
        "format": "json",
        "ApiKey": API_KEY
    }
    response = requests.get(SYNGENTA_WEATHER_API, params=params)

    if response.status_code != 200:
        return {"error": "Wetterdaten konnten nicht abgerufen werden."}

    data = response.json()
    TMIN = float(data[0].get("dailyValue", "N/A"))  # Extrahiere minimale Temperatur

    # Temperaturgrenzen für die gewählte Kulturpflanze
    TMinNoFrost = crop_temp_limits[crop.lower()]["TMinNoFrost"]
    TMinFrost = crop_temp_limits[crop.lower()]["TMinFrost"]



    # Berechnung des Frost Stress
    print(TMIN)
    if TMIN >= TMinNoFrost:
        frost_stress = 0
    elif TMinFrost < TMIN < TMinNoFrost:
        frost_stress = 9 * abs((TMIN - TMinNoFrost) / (TMinFrost - TMinNoFrost))
    else:
        frost_stress = 9

    #return int(frost_stress)
    return {
            "frost_stress": int(frost_stress)
        }

@router.get("/risk/drought/{date}/{lat}/{lon}")
def get_drought_risk(date: str, lat: float, lon: float):
    params = {
        "latitude": lat,
        "longitude": lon,
        "startDate": date,
        "endDate": date,
        "supplier": "Meteoblue",
        "measureLabel": ["Precipitation (mm)", "Evapotranspiration (mm)", "SoilMoisture (mm)", "TempAir_DailyAvg (C)"],
        "format": "json",
        "ApiKey": API_KEY
    }

    response = requests.get(SYNGENTA_WEATHER_API, params=params)

    if response.status_code != 200:
        return {"error": "Wetterdaten konnten nicht abgerufen werden."}

    data = response.json()

    # Extrahiere Werte aus der API-Antwort
    try:
        P = float(data[0].get("dailyValue", "0"))  # Rainfall
        E = float(data[1].get("dailyValue", "0"))  # Evapotranspiration
        SM = float(data[2].get("dailyValue", "0"))  # Soil Moisture
        T = float(data[3].get("dailyValue", "0"))  # Durchschnittstemperatur
    except (IndexError, ValueError):
        return {"error": "Unvollständige Wetterdaten"}

    # Berechnung des Drought Risk Index (DI)
    DI = (P - E) + (SM / T) if T != 0 else 0  # Falls T = 0, um Division durch 0 zu vermeiden

    # Klassifizierung des Drought Risks
    if DI > 1:
        drought_risk = "No risk"
    elif DI == 1:
        drought_risk = "Medium risk"
    else:
        drought_risk = "High risk"

    return {
        "drought_index": round(DI, 2),
        "risk_level": drought_risk
    }

