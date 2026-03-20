import csv
import io
import os
import statistics
from collections import Counter


def calc_stats(numbers):
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
        insight += f" Valor mais frequente: {round(v,2) if isinstance(v, float) else v}."
    insight += f" Amplitude: {maximo - minimo:.2f} (de {minimo} a {maximo})."
    if media > mediana:
        insight += " Distribuição assimétrica à direita."
    elif media < mediana:
        insight += " Distribuição assimétrica à esquerda."
    else:
        insight += " Distribuição aproximadamente simétrica."

    def fmt(v):
        return round(v, 2) if isinstance(v, float) else v

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
    }


def calc_categorical_stats(values):
    if not values:
        return None
    total = len(values)
    freq = Counter(values)
    most_common = freq.most_common()
    unicos = len(freq)
    diversidade = round(unicos / total * 100, 1)
    return {
        'total': total,
        'unique': unicos,
        'diversity': diversidade,
        'most_common': most_common[0][0] if most_common else '',
        'most_common_count': most_common[0][1] if most_common else 0,
        'most_common_pct': round(most_common[0][1] / total * 100, 1) if most_common else 0,
        'frequencies': [
            {'value': k, 'count': v, 'pct': round(v / total * 100, 1)}
            for k, v in most_common[:20]
        ],
    }


def parse_csv_as_analysis(content, source_name=''):
    try:
        reader = csv.DictReader(io.StringIO(content))
        fieldnames = reader.fieldnames or []
        if not fieldnames:
            return None, "CSV sem cabeçalhos. A primeira linha deve conter os nomes das colunas."

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
            values = raw_columns[col_name]
            if not values:
                continue

            numeric_values = []
            for v in values:
                try:
                    numeric_values.append(float(v.replace(',', '.')))
                except ValueError:
                    pass

            numeric_ratio = len(numeric_values) / len(values) if values else 0
            col_data = {'name': col_name, 'total': len(values)}

            if numeric_ratio >= 0.8 and numeric_values:
                col_data['type'] = 'numeric'
                col_data['values'] = numeric_values
                col_data['stats'] = calc_stats(numeric_values)
            else:
                col_data['type'] = 'categorical'
                col_data['values'] = values
                col_data['stats'] = calc_categorical_stats(values)

            columns.append(col_data)

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


def build_analysis_from_form(formulario):
    from .models import ItemResposta
    from collections import Counter

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


def get_groq_client():
    try:
        from groq import Groq
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            return None
        return Groq(api_key=api_key)
    except Exception:
        return None


def generate_ai_response(question, context_data=None):
    client = get_groq_client()
    if not client:
        return None, "Chave GROQ_API_KEY não configurada."

    context = ""
    if context_data:
        columns = context_data.get('columns', [])
        source = context_data.get('source_name', '')
        total = context_data.get('total_responses', 0)
        context = f"Análise de dados: {total} respostas"
        if source:
            context += f" de '{source}'"
        context += ".\n\n"
        for col in columns[:5]:
            context += f"Coluna '{col['name']}' ({col.get('type', '?')}):\n"
            stats = col.get('stats')
            if stats and col.get('type') == 'numeric':
                context += (
                    f"  - Média: {stats.get('media')}, Mediana: {stats.get('mediana')}, "
                    f"Desvio: {stats.get('desvio_padrao')}, "
                    f"Min: {stats.get('min')}, Max: {stats.get('max')}\n"
                )
            elif stats and col.get('type') == 'categorical':
                context += (
                    f"  - Total: {stats.get('total')}, Categorias: {stats.get('unique')}, "
                    f"Mais comum: '{stats.get('most_common')}' ({stats.get('most_common_pct')}%)\n"
                )

    prompt = (
        "Você é um analista de dados especialista. "
        "Responda sempre em português brasileiro de forma clara e objetiva.\n\n"
    )
    if context:
        prompt += context + "\n"
    prompt += f"Pergunta: {question}"

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
        )
        return response.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)
