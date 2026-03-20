import statistics
from collections import Counter


def calcular_estatisticas(numeros):
    if not numeros:
        return None

    n = len(numeros)
    media = sum(numeros) / n
    mediana = statistics.median(numeros)
    desvio = statistics.pstdev(numeros)
    total = sum(numeros)
    minimo = min(numeros)
    maximo = max(numeros)

    contagem = Counter(numeros)
    max_freq = max(contagem.values())
    moda = sorted([k for k, v in contagem.items() if v == max_freq])

    cv = desvio / media if media != 0 else 0
    if cv < 0.1:
        insight = "Os dados estão muito concentrados próximos da média."
    elif cv < 0.3:
        insight = f"Os dados apresentam dispersão moderada (σ = {desvio:.2f})."
    else:
        insight = f"Há alta variação nos valores (σ = {desvio:.2f})."

    if moda:
        insight += f" Valor mais frequente: {moda[0]:.2f}." if isinstance(moda[0], float) else f" Valor mais frequente: {moda[0]}."

    amplitude = maximo - minimo
    insight += f" Amplitude: {amplitude:.2f} (de {minimo} a {maximo})."

    if media > mediana:
        insight += " Distribuição assimétrica à direita."
    elif media < mediana:
        insight += " Distribuição assimétrica à esquerda."
    else:
        insight += " Distribuição aproximadamente simétrica."

    def fmt(v):
        if isinstance(v, float):
            return round(v, 2)
        return v

    return {
        "count": n,
        "media": round(media, 2),
        "mediana": round(mediana, 2),
        "moda": [fmt(m) for m in moda],
        "desvio_padrao": round(desvio, 2),
        "total": round(total, 2),
        "min": fmt(minimo),
        "max": fmt(maximo),
        "insight": insight,
    }
