import requests
import pandas as pd

def get_previsao(cidade):
    API_KEY = "abac4128c474b16db22cb93fe7cb99e5"
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={cidade}&appid={API_KEY}&units=metric&lang=pt_br"

    response = requests.get(url)

    if response.status_code != 200:
        print("Erro ao conectar com a API:", response.status_code)
        return pd.DataFrame(columns=[
            "Hora", "Chuva (mm)", "Temperatura (°C)", "Umidade (%)",
            "Velocidade do Vento (m/s)", "Pressão Atmosférica (hPa)"
        ])

    data = response.json()

    if "list" not in data:
        print("Resposta inesperada da API:", data)
        return pd.DataFrame(columns=[
            "Hora", "Chuva (mm)", "Temperatura (°C)", "Umidade (%)",
            "Velocidade do Vento (m/s)", "Pressão Atmosférica (hPa)"
        ])

    registros = []

    for item in data["list"]:
        registros.append({
            "Hora": item["dt_txt"],
            "Chuva (mm)": item.get("rain", {}).get("3h", 0.0),
            "Temperatura (°C)": item["main"]["temp"],
            "Umidade (%)": item["main"]["humidity"],
            "Velocidade do Vento (m/s)": item["wind"]["speed"],
            "Pressão Atmosférica (hPa)": item["main"]["pressure"]
        })

    return pd.DataFrame(registros)
