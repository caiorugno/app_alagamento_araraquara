def calcular_risco(chuva_mm):
    if chuva_mm > 15:
        return "Alto"
    elif chuva_mm > 8:
        return "Moderado"
    else:
        return "Baixo"
