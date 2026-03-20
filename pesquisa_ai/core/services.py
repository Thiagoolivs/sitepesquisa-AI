
import csv
import io
import os
import re
import statistics
from collections import Counter

# ── Column classification helpers ────────────────────────────────────────────

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
    'data de envio',
    'submission time',
    'response date',
]

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


# ── Numeric parsing helpers ───────────────────────────────────────────────────

_STRIP_RE = re.compile(r'[R$€£¥%\s_]')


def _try_parse_float(raw: str):
    """Try to parse a string as float, handling Brazilian and international formats.

    Handles:
    - Currency symbols and % (stripped)
    - Comma as decimal separator       → "3,14"       → 3.14
    - Period as thousand separator     → "1.234,56"   → 1234.56
    - Integer with thousand separator  → "R$ 5.000"   → 5000
    - Multiple thousand separators     → "1.234.567"  → 1234567
    - Standard English format          → "1,234.56"   → 1234.56
    Returns float or None.
    """
    v = _STRIP_RE.sub('', raw.strip())
    if not v:
        return None
    has_comma = ',' in v
    has_dot = '.' in v
    try:
        if has_comma and has_dot:
            # Determine which is the decimal separator by position of last occurrence
            if v.rindex(',') > v.rindex('.'):
                # Brazilian: 1.234,56 or 5.000,00
                v = v.replace('.', '').replace(',', '.')
            else:
                # English: 1,234.56
                v = v.replace(',', '')
        elif has_comma:
            # Comma only: decimal comma (BR) or thousand comma
            parts = v.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # "8,5" or "8,50" → decimal separator
                v = v.replace(',', '.')
            else:
                # "1,234,567" → thousand separators
                v = v.replace(',', '')
        elif has_dot:
            parts = v.split('.')
            if len(parts) > 2:
                # "1.234.567" → multiple dots, all thousand separators
                v = v.replace('.', '')
            elif len(parts) == 2 and len(parts[1]) == 3 and parts[1].isdigit():
                # Exactly 3 digits after single dot: Brazilian thousand separator
                # "5.000" → 5000, "1.234" → 1234
                # Edge case: "1.234" could be 1.234 in English, but in a Brazilian
                # survey context, three-digit groups after dot → thousand separator
                v = v.replace('.', '')
            # else: normal decimal "5.5" → 5.5, handled by float() directly
        return float(v)
    except ValueError:
        return None


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
        'labels': labels,
        'values': values,
    }


def calc_categorical_stats(values):
    """Compute frequency stats for a categorical column."""
    if not values:
        return None
    total = len(values)
    freq = Counter(values)
    most_common = freq.most_common()
    unicos = len(freq)
    diversidade = round(unicos / total * 100, 1)

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
        'frequencies': [
            {'value': k, 'count': v, 'pct': round(v / total * 100, 1)}
            for k, v in sorted_freq
        ],
        'labels': labels,
        'values': counts,
    }


# ── CSV parsing ──────────────────────────────────────────────────────────────

_ENCODINGS = ('utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16')


def _decode_content(raw_bytes: bytes) -> tuple:
    """Try multiple encodings and return (text, encoding_used) or (None, None)."""
    for enc in _ENCODINGS:
        try:
            return raw_bytes.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return None, None


def _detect_delimiter(sample: str) -> str:
    """Detect the CSV delimiter from a text sample."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
        return dialect.delimiter
    except csv.Error:
        pass
    # Fallback: count occurrences of common delimiters in first line
    first_line = sample.split('\n')[0] if '\n' in sample else sample
    counts = {d: first_line.count(d) for d in (',', ';', '\t', '|')}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ','


def parse_csv_as_analysis(content, source_name=''):
    """Parse a CSV file (bytes or string) into the standard analysis dict.

    Refinements applied automatically:
    - Multiple encoding detection (UTF-8-BOM, UTF-8, Latin-1, CP1252, UTF-16)
    - Auto-detect delimiter (comma, semicolon, tab, pipe)
    - Strip BOM / extra whitespace from column headers
    - Brazilian number format support (1.234,56 → 1234.56)
    - Currency / percent symbols stripped from numeric values
    - Timestamp columns silently dropped
    - Consent columns → type='consent' with fixed message
    - ≥ 70% parseable as float → numeric column (relaxed from 80%)
    - All categorical columns use canonical labels/values frequency structure
    """
    # ── Decode bytes if needed ────────────────────────────────────────────
    if isinstance(content, (bytes, bytearray)):
        text, enc = _decode_content(content)
        if text is None:
            return None, (
                "Não foi possível decodificar o arquivo CSV. "
                "Salve como UTF-8 e tente novamente."
            )
    else:
        text = content

    if not text.strip():
        return None, "Arquivo CSV vazio."

    # ── Detect delimiter ──────────────────────────────────────────────────
    delimiter = _detect_delimiter(text[:8192])

    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        raw_fieldnames = reader.fieldnames

        if not raw_fieldnames:
            return None, "CSV sem cabeçalhos. A primeira linha deve conter os nomes das colunas."

        # Clean column names: strip whitespace, BOM, zero-width chars
        fieldnames = [
            re.sub(r'[\ufeff\u200b\r]', '', name).strip()
            for name in raw_fieldnames
        ]
        # Build mapping old → new name for row access
        name_map = dict(zip(raw_fieldnames, fieldnames))

        raw_columns = {name: [] for name in fieldnames}
        total_rows = 0

        for row in reader:
            total_rows += 1
            for raw_name, clean_name in name_map.items():
                val = str(row.get(raw_name, '') or '').strip()
                if val and val.lower() not in ('n/a', 'na', 'null', 'none', '-', ''):
                    raw_columns[clean_name].append(val)

        if total_rows == 0:
            return None, "Arquivo CSV sem linhas de dados."

        columns = []
        for col_name in fieldnames:

            # 1. Skip blank column names
            if not col_name:
                continue

            # 2. Drop timestamp columns entirely
            if _is_timestamp_column(col_name):
                continue

            values = raw_columns[col_name]

            # 3. Consent columns → fixed message, no statistics
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

            # 4. Classify as numeric or categorical
            numeric_values = []
            for v in values:
                parsed = _try_parse_float(v)
                if parsed is not None:
                    numeric_values.append(parsed)

            numeric_ratio = len(numeric_values) / len(values) if values else 0

            # Relaxed threshold: 70% parseable → numeric
            if numeric_ratio >= 0.70 and len(numeric_values) >= 2:
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
                parsed = _try_parse_float(v)
                if parsed is not None:
                    numeric_values.append(parsed)
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
    """Build a structured context string for the AI prompt."""
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

        if col_type == 'consent':
            lines.append(f"Coluna '{col['name']}': Todos concordaram em participar.")
            continue

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
