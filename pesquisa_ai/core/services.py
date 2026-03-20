import csv
import io
import os
import statistics
from collections import Counter

# ── Column classification helpers ────────────────────────────────────────────

# Columns whose names match any of these fragments are silently dropped.
_TIMESTAMP_FRAGMENTS = [
    'carimbo de data',
    'carimbo de hora',
    'timestamp',
    'data/hora',
    'data e hora',
    'datetime',
    'created_at',
    'submitted_at',
    'hora de envio',
]

# Columns whose names match any of these fragments are treated as consent
# columns — their stats are replaced by a fixed message.
_CONSENT_FRAGMENTS = [
    'concorda em participar',
    'concordo em participar',
    'aceita participar',
    'aceito participar',
    'autorizo',
    'consentimento',
    'consent',
    'você concorda',
    'voce concorda',
    'concorda com a participação',
]


def _is_timestamp_column(name: str) -> bool:
    lower = name.lower().strip()
    return any(frag in lower for frag in _TIMESTAMP_FRAGMENTS)


def _is_consent_column(name: str) -> bool:
    lower = name.lower().strip()
    return any(frag in lower for frag in _CONSENT_FRAGMENTS)


# ── Statistical helpers ──────────────────────────────────────────────────────

def calc_stats(numbers):
    """Compute descriptive stats for a numeric column."""
    if not numbers:
        return None
    n = len(numbers)
    media = sum(numbers) / n
    mediana = statistics.median(numbers)
    desvio = statistics.pstdev(numbers)
    total = sum(numbers)
    minimo = min(numbers)
    maximo = max(numbers)

    contagem = Counter(numbers)
    max_freq = max(contagem.values())
    moda = sorted([k for k, v in contagem.items() if v == max_freq])

    cv = desvio / media if media != 0 else 0
    if cv < 0.1:
        insight = "Dados muito concentrados próximos da média."
    elif cv < 0.3:
        insight = f"Dispersão moderada (σ = {desvio:.2f})."
    else:
        insight = f"Alta variação nos valores (σ = {desvio:.2f})."
    if moda:
        v = moda[0]
        insight += f" Valor mais frequente: {round(v, 2) if isinstance(v, float) else v}."
    insight += f" Amplitude: {maximo - minimo:.2f} (de {minimo} a {maximo})."
    if media > mediana:
        insight += " Distribuição assimétrica à direita."
    elif media < mediana:
        insight += " Distribuição assimétrica à esquerda."
    else:
        insight += " Distribuição aproximadamente simétrica."

    def fmt(v):
        return round(v, 2) if isinstance(v, float) else v

    # Frequency-based numeric representation for chart rendering / AI context
    freq = Counter(numbers)
    sorted_freq = sorted(freq.items(), key=lambda x: -x[1])
    labels = [str(fmt(k)) for k, _ in sorted_freq[:20]]
    values = [v for _, v in sorted_freq[:20]]

    return {
        'count': n,
        'media': round(media, 2),
        'mediana': round(mediana, 2),
        'moda': [fmt(m) for m in moda],
        'desvio_padrao': round(desvio, 2),
        'total': round(total, 2),
        'min': fmt(minimo),
        'max': fmt(maximo),
        'insight': insight,
        # Chart-ready structure
        'labels': labels,
        'values': values,
    }


def calc_categorical_stats(values):
    """Compute frequency stats for a categorical column.

    Categorical data is fully converted to a frequency-based numeric
    representation: ``labels`` (category names) and ``values`` (counts).
    This canonical form is used for dashboard charts and AI context alike.
    """
    if not values:
        return None
    total = len(values)
    freq = Counter(values)
    most_common = freq.most_common()
    unicos = len(freq)
    diversidade = round(unicos / total * 100, 1)

    # Canonical numeric representation — sorted by frequency descending
    sorted_freq = most_common[:20]
    labels = [item[0] for item in sorted_freq]
    counts = [item[1] for item in sorted_freq]

    return {
        'total': total,
        'unique': unicos,
        'diversity': diversidade,
        'most_common': most_common[0][0] if most_common else '',
        'most_common_count': most_common[0][1] if most_common else 0,
        'most_common_pct': round(most_common[0][1] / total * 100, 1) if most_common else 0,
        # Standard frequency table (used by existing template rendering)
        'frequencies': [
            {'value': k, 'count': v, 'pct': round(v / total * 100, 1)}
            for k, v in sorted_freq
        ],
        # Canonical chart-ready structure (labels + values)
        'labels': labels,
        'values': counts,
    }


# ── CSV parsing ──────────────────────────────────────────────────────────────

def parse_csv_as_analysis(content, source_name=''):
    """Parse a CSV file into the standard analysis dict.

    Rules applied automatically:
    - Timestamp columns (e.g. "Carimbo de data/hora") are silently dropped.
    - Consent columns (e.g. "Você concorda em participar da pesquisa?") are
      kept in the column list but their stats are replaced by the fixed message
      "Todos concordaram em participar da pesquisa" and their type is set to
      ``consent``.
    - Each remaining column is classified as ``numeric`` (≥ 80 % parseable as
      float) or ``categorical``.
    - Categorical data is always stored with the canonical ``labels``/``values``
      numeric frequency structure.
    """
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return None, "CSV sem cabeçalhos. A primeira linha deve conter os nomes das colunas."

        # Collect raw values per column
        raw_columns = {name: [] for name in fieldnames}
        total_rows = 0
        for row in reader:
            total_rows += 1
            for name in fieldnames:
                val = str(row.get(name, '')).strip()
                if val:
                    raw_columns[name].append(val)

        if total_rows == 0:
            return None, "Arquivo CSV sem linhas de dados."

        columns = []
        for col_name in fieldnames:

            # 1. Drop timestamp columns entirely
            if _is_timestamp_column(col_name):
                continue

            values = raw_columns[col_name]

            # 2. Consent columns → fixed message, no statistics
            if _is_consent_column(col_name):
                columns.append({
                    'name': col_name,
                    'type': 'consent',
                    'total': len(values),
                    'values': [],
                    'stats': None,
                    'consent_message': 'Todos concordaram em participar da pesquisa.',
                })
                continue

            if not values:
                continue

            # 3. Classify as numeric or categorical
            numeric_values = []
            for v in values:
                try:
                    numeric_values.append(float(v.replace(',', '.')))
                except ValueError:
                    pass

            numeric_ratio = len(numeric_values) / len(values) if values else 0

            if numeric_ratio >= 0.8 and numeric_values:
                columns.append({
                    'name': col_name,
                    'type': 'numeric',
                    'total': len(numeric_values),
                    'values': numeric_values,
                    'stats': calc_stats(numeric_values),
                })
            else:
                columns.append({
                    'name': col_name,
                    'type': 'categorical',
                    'total': len(values),
                    'values': values,
                    'stats': calc_categorical_stats(values),
                })

        if not columns:
            return None, "Nenhum dado válido encontrado nas colunas do CSV."

        return {
            'type': 'csv',
            'source_name': source_name,
            'columns': columns,
            'total_responses': total_rows,
        }, None

    except Exception as e:
        return None, f"Erro ao processar CSV: {e}"


# ── Form → analysis ──────────────────────────────────────────────────────────

def build_analysis_from_form(formulario):
    """Build the standard analysis dict from a Formulario instance."""
    from .models import ItemResposta

    columns = []
    for pergunta in formulario.perguntas.order_by('ordem'):
        pid = pergunta.pergunta_id
        valores_raw = list(
            ItemResposta.objects.filter(
                resposta__formulario=formulario,
                pergunta_id=pid,
            ).exclude(valor='').values_list('valor', flat=True)
        )

        if not valores_raw:
            columns.append({
                'name': pergunta.texto,
                'type': 'empty',
                'total': 0,
                'values': [],
                'stats': None,
            })
            continue

        if pergunta.tipo == 'numerica':
            numeric_values = []
            for v in valores_raw:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    pass
            columns.append({
                'name': pergunta.texto,
                'type': 'numeric',
                'total': len(numeric_values),
                'values': numeric_values,
                'stats': calc_stats(numeric_values) if numeric_values else None,
            })
        elif pergunta.tipo == 'multipla_escolha':
            columns.append({
                'name': pergunta.texto,
                'type': 'categorical',
                'total': len(valores_raw),
                'values': valores_raw,
                'stats': calc_categorical_stats(valores_raw),
            })
        else:
            columns.append({
                'name': pergunta.texto,
                'type': 'text',
                'total': len(valores_raw),
                'values': valores_raw,
                'stats': None,
            })

    return {
        'type': 'form',
        'source_name': formulario.titulo,
        'form_id': formulario.pk,
        'columns': columns,
        'total_responses': formulario.respostas.count(),
    }


# ── AI integration ───────────────────────────────────────────────────────────

def get_groq_client():
    """Return a configured Groq client or None if the key is absent.

    The API key is read exclusively from the GROQ_API_KEY environment variable
    and is never embedded in source code or prompts.
    """
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception:
        return None


def _build_ai_context(context_data: dict) -> str:
    """Build a structured, unambiguous context string for the AI prompt.

    Uses the canonical labels/values frequency representation for all columns
    so the model receives numeric data regardless of the original column type.
    Timestamp and consent columns are excluded automatically.
    """
    if not context_data:
        return ""

    source = context_data.get('source_name', '')
    total = context_data.get('total_responses', 0)
    columns = context_data.get('columns', [])

    lines = [
        "=== CONTEXTO DA PESQUISA ===",
        f"Fonte: {source}" if source else "",
        f"Total de respostas: {total}",
        "",
    ]

    for col in columns:
        col_type = col.get('type', '')

        # Skip consent columns in AI context (already handled by the UI)
        if col_type == 'consent':
            lines.append(f"Coluna '{col['name']}': Todos concordaram em participar.")
            continue

        # Skip empty columns
        if col_type in ('empty', 'text') or not col.get('stats'):
            if col_type == 'text' and col.get('values'):
                lines.append(f"Coluna '{col['name']}' (texto livre): {col['total']} respostas")
            continue

        stats = col['stats']
        lines.append(f"Pergunta: \"{col['name']}\"")

        if col_type == 'numeric':
            lines.append(
                f"  Tipo: numérico | N={stats['count']} | "
                f"Média={stats['media']} | Mediana={stats['mediana']} | "
                f"DP={stats['desvio_padrao']} | Min={stats['min']} | Max={stats['max']}"
            )
            # Include top-frequency values as labels/values
            if stats.get('labels') and stats.get('values'):
                pairs = ', '.join(
                    f"{l}→{v}" for l, v in zip(stats['labels'][:10], stats['values'][:10])
                )
                lines.append(f"  Frequências (valor→contagem): {pairs}")

        elif col_type == 'categorical':
            labels = stats.get('labels', [])
            values = stats.get('values', [])
            lines.append(
                f"  Tipo: categórico | Total={stats['total']} | "
                f"Categorias distintas={stats['unique']} | "
                f"Mais comum: \"{stats['most_common']}\" ({stats['most_common_pct']}%)"
            )
            if labels and values:
                pairs = ', '.join(
                    f"\"{l}\"→{v}" for l, v in zip(labels, values)
                )
                lines.append(f"  Distribuição (categoria→contagem): [{pairs}]")

        lines.append("")

    return "\n".join(line for line in lines if line is not None)


def generate_ai_response(question, context_data=None):
    """Send a question + structured data context to Groq and return the answer.

    The GROQ_API_KEY is accessed only through environment variables and is
    never included in the prompt or logged.
    """
    client = get_groq_client()
    if not client:
        return None, "Chave GROQ_API_KEY não configurada."

    context = _build_ai_context(context_data) if context_data else ""

    system_prompt = (
        "Você é um analista de dados especialista em pesquisas e estatística. "
        "Responda sempre em português brasileiro de forma clara, objetiva e estruturada. "
        "Quando houver dados numéricos de frequência (labels e values), utilize-os para "
        "embasar suas análises com precisão. Não invente dados que não estejam no contexto."
    )

    user_message = ""
    if context:
        user_message += context + "\n\n=== PERGUNTA ===\n"
    user_message += question

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=900,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)
