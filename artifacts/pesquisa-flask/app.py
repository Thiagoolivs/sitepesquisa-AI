import os
import signal
import socket
import math
from collections import Counter
from flask import Flask, render_template, request, jsonify

def liberar_porta(porta):
    """Mata qualquer processo usando a porta antes de iniciar."""
    try:
        import subprocess
        result = subprocess.run(['fuser', f'{porta}/tcp'], capture_output=True, text=True)
        pids = result.stdout.strip().split()
        for pid in pids:
            try:
                os.kill(int(pid), signal.SIGKILL)
            except Exception:
                pass
    except Exception:
        pass

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ── Armazenamento em memória (suporta 150+ respostas) ─────────────────────
formulario_salvo = None
respostas_armazenadas = []  # lista de listas: cada item = uma submissão
ultimo_analise = None


# ── Funções estatísticas ──────────────────────────────────────────────────

def calcular_estatisticas(numeros):
    if not numeros:
        return None
    n = len(numeros)
    total = sum(numeros)
    media = total / n
    s = sorted(numeros)
    mid = n // 2
    mediana = s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2
    freq = Counter(numeros)
    max_freq = max(freq.values())
    moda = [] if max_freq == 1 else [k for k, v in freq.items() if v == max_freq]
    variancia = sum((x - media) ** 2 for x in numeros) / n
    desvio_padrao = math.sqrt(variancia)
    return {
        "media": round(media, 2),
        "mediana": round(mediana, 2),
        "moda": sorted(moda),
        "total": round(total, 2),
        "count": n,
        "min": min(numeros),
        "max": max(numeros),
        "desvio_padrao": round(desvio_padrao, 2),
    }


def parse_csv_numeros(content):
    numeros = []
    for line in content.splitlines():
        for cell in line.split(","):
            try:
                n = float(cell.strip())
                if not math.isnan(n):
                    numeros.append(n)
            except Exception:
                pass
    return numeros


def gerar_insight(stats):
    """Gera texto automático de insight sem usar IA."""
    cv = stats["desvio_padrao"] / stats["media"] if stats["media"] != 0 else 0
    partes = []
    if cv < 0.1:
        partes.append("Os dados estão muito concentrados próximos da média.")
    elif cv < 0.3:
        partes.append(f"Os dados apresentam dispersão moderada (σ = {stats['desvio_padrao']}).")
    else:
        partes.append(f"Há alta variação nos valores (σ = {stats['desvio_padrao']}).")
    if stats["moda"]:
        partes.append(f"O valor mais frequente é {stats['moda'][0]}.")
    amp = round(stats["max"] - stats["min"], 2)
    partes.append(f"Amplitude: {amp} (de {stats['min']} a {stats['max']}).")
    if stats["media"] > stats["mediana"]:
        partes.append("Distribuição assimétrica à direita — valores altos puxam a média.")
    elif stats["media"] < stats["mediana"]:
        partes.append("Distribuição assimétrica à esquerda — valores baixos puxam a média.")
    else:
        partes.append("Distribuição aproximadamente simétrica.")
    return " ".join(partes)


def groq_analise(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente de análise de dados estatísticos. "
                        "Responda sempre em português, de forma clara e objetiva."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def get_respostas_por_pergunta(pergunta_id):
    """Retorna lista de valores (em ordem de envio) para uma pergunta específica."""
    valores = []
    for submissao in respostas_armazenadas:
        for r in submissao:
            if r.get("pergunta_id") == pergunta_id:
                valores.append(r.get("valor", ""))
    return valores


# ── Páginas HTML ──────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    perguntas_numericas = []
    pergunta_principal_id = None
    if formulario_salvo:
        perguntas_numericas = [
            p for p in formulario_salvo.get("perguntas", [])
            if p.get("tipo") == "numerica"
        ]
        # Busca a pergunta marcada como principal
        for p in formulario_salvo.get("perguntas", []):
            if p.get("principal") and p.get("tipo") == "numerica":
                pergunta_principal_id = p["id"]
                break
        # Fallback: primeira numérica
        if not pergunta_principal_id and perguntas_numericas:
            pergunta_principal_id = perguntas_numericas[0]["id"]
    return render_template(
        "dashboard.html",
        analise=ultimo_analise,
        formulario=formulario_salvo,
        perguntas_numericas=perguntas_numericas,
        pergunta_principal_id=pergunta_principal_id,
        total_respostas=len(respostas_armazenadas),
    )


@app.route("/pesquisa")
def pesquisa():
    return render_template(
        "pesquisa.html",
        formulario=formulario_salvo,
        total_respostas=len(respostas_armazenadas),
    )


@app.route("/ia")
def ia_page():
    return render_template("ia.html", analise=ultimo_analise)


# ── Rotas de API ──────────────────────────────────────────────────────────

@app.route("/analisar", methods=["POST"])
def analisar():
    global ultimo_analise
    data = request.get_json() or {}
    numeros = data.get("numeros", [])
    if not numeros:
        return jsonify({"error": "Lista de números vazia."}), 400
    stats = calcular_estatisticas([float(x) for x in numeros])
    stats["insight"] = gerar_insight(stats)
    ultimo_analise = stats
    return jsonify(stats)


@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    global ultimo_analise
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado. Use o campo 'arquivo'."}), 400
    content = request.files["arquivo"].read().decode("utf-8", errors="ignore")
    numeros = parse_csv_numeros(content)
    if not numeros:
        return jsonify({"error": "Nenhum valor numérico encontrado no CSV."}), 400
    stats = calcular_estatisticas(numeros)
    stats["insight"] = gerar_insight(stats)
    stats["valores"] = numeros
    ultimo_analise = stats
    return jsonify(stats)


@app.route("/formulario", methods=["GET"])
def get_formulario():
    if not formulario_salvo:
        return jsonify({"error": "Nenhum formulário salvo ainda."}), 404
    return jsonify({**formulario_salvo, "total_respostas": len(respostas_armazenadas)})


@app.route("/formulario", methods=["POST"])
def salvar_formulario():
    global formulario_salvo, respostas_armazenadas
    formulario_salvo = request.get_json() or {}
    respostas_armazenadas = []
    return jsonify({"mensagem": "Formulário salvo!", "formulario": formulario_salvo})


@app.route("/formulario/responder", methods=["POST"])
def responder_formulario():
    global respostas_armazenadas, ultimo_analise
    data = request.get_json() or {}
    respostas_armazenadas.append(data.get("respostas", []))

    # Conta totais e válidos
    total_respostas = len(respostas_armazenadas)
    numeros_todos = []
    for sub in respostas_armazenadas:
        for r in sub:
            try:
                numeros_todos.append(float(r["valor"]))
            except Exception:
                pass

    analise = None
    if numeros_todos:
        analise = calcular_estatisticas(numeros_todos)
        analise["insight"] = gerar_insight(analise)
        ultimo_analise = analise

    return jsonify(
        {
            "mensagem": f"Resposta registrada! Total: {total_respostas} envio(s).",
            "respostas_numericas": len(numeros_todos),
            "total_respostas": total_respostas,
            "analise": analise,
        }
    )


@app.route("/formulario/dados", methods=["GET"])
def get_dados_pergunta():
    """Retorna dados de uma pergunta específica para os gráficos do dashboard."""
    pergunta_id = request.args.get("pergunta_id")
    if not formulario_salvo:
        return jsonify({"error": "Nenhum formulário disponível."}), 404

    perguntas = formulario_salvo.get("perguntas", [])
    pergunta = next((p for p in perguntas if p["id"] == pergunta_id), None)

    # Se nenhum pergunta_id informado ou não encontrado, usa a primeira numérica
    if not pergunta:
        pergunta = next((p for p in perguntas if p.get("tipo") == "numerica"), None)
    if not pergunta:
        return jsonify({"error": "Nenhuma pergunta numérica encontrada."}), 404

    pid = pergunta["id"]
    valores_raw = get_respostas_por_pergunta(pid)

    # Separa válidos e inválidos
    valores_numericos = []
    for v in valores_raw:
        try:
            valores_numericos.append(float(v))
        except Exception:
            pass

    total_respostas = len(respostas_armazenadas)
    respostas_validas = len(valores_numericos)

    if not valores_numericos:
        return jsonify({
            "pergunta": pergunta,
            "valores": [],
            "stats": None,
            "insight": None,
            "total_respostas": total_respostas,
            "respostas_validas": 0,
            "percentual_validas": 0,
        })

    stats = calcular_estatisticas(valores_numericos)
    percentual = round((respostas_validas / total_respostas * 100), 1) if total_respostas else 0

    return jsonify({
        "pergunta": pergunta,
        "valores": valores_numericos,      # Evolução em ordem de envio
        "stats": stats,
        "insight": gerar_insight(stats),
        "total_respostas": total_respostas,
        "respostas_validas": respostas_validas,
        "percentual_validas": percentual,
    })


@app.route("/ia", methods=["POST"])
def ia_api():
    data = request.get_json() or {}
    pergunta = data.get("pergunta", "").strip()
    dados = data.get("dados") or ultimo_analise

    if not pergunta:
        return jsonify({"error": "Nenhuma pergunta enviada."}), 400

    contexto = ""
    if dados:
        contexto = (
            f"Analise os seguintes dados:\n"
            f"Média: {dados['media']}\n"
            f"Mediana: {dados['mediana']}\n"
            f"Desvio padrão: {dados['desvio_padrao']}\n"
            f"Mínimo: {dados['min']}\n"
            f"Máximo: {dados['max']}\n\n"
            "Explique de forma clara os padrões e possíveis conclusões.\n\n"
        )

    prompt = f"{contexto}Pergunta do usuário: {pergunta}\n\nResponda em português."
    resposta = groq_analise(prompt)
    if not resposta and dados:
        resposta = gerar_insight(dados)
    elif not resposta:
        resposta = "Nenhum dado disponível. Carregue números ou um CSV primeiro."

    return jsonify({"resposta": resposta})


@app.route("/ia_csv", methods=["POST"])
def ia_csv():
    global ultimo_analise
    if "arquivo" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado."}), 400
    content = request.files["arquivo"].read().decode("utf-8", errors="ignore")
    numeros = parse_csv_numeros(content)
    if not numeros:
        return jsonify({"error": "Nenhum valor numérico encontrado no CSV."}), 400

    stats = calcular_estatisticas(numeros)
    ultimo_analise = stats

    prompt = (
        f"Analise os seguintes dados:\n"
        f"Média: {stats['media']}\n"
        f"Mediana: {stats['mediana']}\n"
        f"Desvio padrão: {stats['desvio_padrao']}\n"
        f"Mínimo: {stats['min']}\n"
        f"Máximo: {stats['max']}\n\n"
        "Explique de forma clara os padrões e possíveis conclusões."
    )
    insight = groq_analise(prompt) or gerar_insight(stats)

    return jsonify({**stats, "valores": numeros, "insight": insight})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    liberar_porta(port)
    app.run(host="0.0.0.0", port=port, debug=False)
