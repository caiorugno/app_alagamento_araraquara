import requests
import pandas as pd

def get_previsao(cidade):
    API_KEY = "abac4128c474b16db22cb93fe7cb99e5"
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={cidade}&appid={API_KEY}&units=metric&lang=pt_br"
    response = requests.get(url).json()

    # Verifica se a resposta contém dados válidos
    if "list" not in response:
        print("Erro na resposta da API:", response)
        return pd.DataFrame(columns=["Hora", "Chuva (mm)"])

    horas = []
    chuva_mm = []

    for item in response["list"]:
        hora = item["dt_txt"]
        chuva = item.get("rain", {}).get("3h", 0)  # Chuva acumulada em 3h
        horas.append(hora)
        chuva_mm.append(chuva)

    df = pd.DataFrame({
        "Hora": horas,
        "Chuva (mm)": chuva_mm
    })

    return df
