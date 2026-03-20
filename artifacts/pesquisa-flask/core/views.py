import csv
import io
import json
import logging
import os
from collections import Counter

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .stats import calcular_estatisticas

logging.basicConfig(level=logging.DEBUG)


def _get_groq_client():
    try:
        from groq import Groq
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            return None
        return Groq(api_key=api_key)
    except Exception:
        return None


def _gerar_insight_ia(pergunta, dados):
    client = _get_groq_client()
    if not client:
        return None, "Chave GROQ_API_KEY não configurada."

    contexto = ""
    if dados:
        contexto = (
            f"Dados estatísticos analisados:\n"
            f"- Quantidade: {dados.get('count')} valores\n"
            f"- Média: {dados.get('media')}\n"
            f"- Mediana: {dados.get('mediana')}\n"
            f"- Moda: {dados.get('moda')}\n"
            f"- Desvio Padrão: {dados.get('desvio_padrao')}\n"
            f"- Mínimo: {dados.get('min')}\n"
            f"- Máximo: {dados.get('max')}\n"
            f"- Total: {dados.get('total')}\n"
        )

    prompt = (
        "Você é um analista de dados especialista. "
        "Responda sempre em português brasileiro de forma clara e objetiva.\n\n"
    )
    if contexto:
        prompt += f"{contexto}\n"
    prompt += f"Pergunta do usuário: {pergunta}"

    try:
        resposta = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
        )
        return resposta.choices[0].message.content.strip(), None
    except Exception as e:
        logging.error(f"Groq error: {e}")
        return None, str(e)


def _perguntas_numericas(formulario):
    if not formulario:
        return [], None
    perguntas = [p for p in formulario.get('perguntas', []) if p.get('tipo') == 'numerica']
    principal_id = next((p['id'] for p in perguntas if p.get('principal')), None)
    if not principal_id and perguntas:
        principal_id = perguntas[0]['id']
    return perguntas, principal_id


def _get_state(request):
    return {
        'formulario': request.session.get('formulario'),
        'respostas': request.session.get('respostas', []),
        'analise': request.session.get('analise'),
    }


def dashboard(request):
    state = _get_state(request)
    formulario = state['formulario']
    analise = state['analise']

    perguntas_num, pergunta_principal_id = _perguntas_numericas(formulario)

    if not analise and perguntas_num and state['respostas'] and pergunta_principal_id:
        valores = []
        for resp in state['respostas']:
            for item in resp:
                if item.get('pergunta_id') == pergunta_principal_id:
                    try:
                        valores.append(float(item['valor']))
                    except (ValueError, TypeError):
                        pass
        if valores:
            analise = calcular_estatisticas(valores)

    return render(request, 'dashboard.html', {
        'active_page': 'dashboard',
        'analise': analise,
        'perguntas_numericas': perguntas_num,
        'pergunta_principal_id': pergunta_principal_id,
    })


def pesquisa(request):
    state = _get_state(request)
    return render(request, 'pesquisa.html', {
        'active_page': 'pesquisa',
        'formulario': state['formulario'],
    })


def ia_page(request):
    state = _get_state(request)
    return render(request, 'ia.html', {
        'active_page': 'ia',
        'analise': state['analise'],
    })


@csrf_exempt
@require_http_methods(["POST"])
def analisar(request):
    try:
        body = json.loads(request.body)
        numeros = [float(n) for n in body.get('numeros', [])]
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Dados inválidos.'}, status=400)

    if not numeros:
        return JsonResponse({'error': 'Nenhum número válido fornecido.'}, status=400)
    if len(numeros) > 10000:
        return JsonResponse({'error': 'Máximo de 10.000 números.'}, status=400)

    result = calcular_estatisticas(numeros)
    request.session['analise'] = result
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def upload_csv(request):
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({'error': 'Nenhum arquivo enviado.'}, status=400)
    if arquivo.size == 0:
        return JsonResponse({'error': 'Arquivo vazio.'}, status=400)

    try:
        content = arquivo.read().decode('utf-8-sig', errors='ignore')
        reader = csv.reader(io.StringIO(content))
        valores = []
        for row in reader:
            for cell in row:
                cell = cell.strip().replace(',', '.')
                try:
                    valores.append(float(cell))
                except ValueError:
                    pass
    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar CSV: {e}'}, status=400)

    if not valores:
        return JsonResponse({'error': 'Nenhum valor numérico encontrado no CSV.'}, status=400)
    if len(valores) > 10000:
        return JsonResponse({'error': 'CSV com muitos valores (máx 10.000).'}, status=400)

    result = calcular_estatisticas(valores)
    result['valores'] = valores
    analise_salva = {k: v for k, v in result.items() if k != 'valores'}
    request.session['analise'] = analise_salva
    return JsonResponse(result)


@csrf_exempt
def formulario_api(request):
    if request.method == 'GET':
        formulario = request.session.get('formulario')
        if not formulario:
            return JsonResponse({'error': 'Nenhum formulário salvo.'}, status=404)
        resp = dict(formulario)
        resp['total_respostas'] = len(request.session.get('respostas', []))
        return JsonResponse(resp)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido.'}, status=400)

        titulo = body.get('titulo', '').strip()
        if not titulo:
            return JsonResponse({'error': 'Título é obrigatório.'}, status=400)
        perguntas = body.get('perguntas', [])
        if not perguntas:
            return JsonResponse({'error': 'Adicione ao menos uma pergunta.'}, status=400)
        for p in perguntas:
            if not p.get('texto', '').strip():
                return JsonResponse({'error': 'Todas as perguntas precisam de texto.'}, status=400)
            if p.get('tipo') == 'multipla_escolha':
                opcoes = p.get('opcoes', [])
                if len(opcoes) < 2:
                    return JsonResponse({'error': f'Pergunta de múltipla escolha precisa de ao menos 2 opções.'}, status=400)
                for op in opcoes:
                    if not op.get('texto', '').strip():
                        return JsonResponse({'error': 'Todas as opções precisam ter texto.'}, status=400)

        formulario = {
            'titulo': titulo,
            'descricao': body.get('descricao', ''),
            'perguntas': perguntas,
        }
        request.session['formulario'] = formulario
        request.session['respostas'] = []
        request.session['analise'] = None
        return JsonResponse({'ok': True, 'mensagem': 'Formulário salvo com sucesso!'})

    return JsonResponse({'error': 'Método não suportado.'}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def formulario_responder(request):
    formulario = request.session.get('formulario')
    if not formulario:
        return JsonResponse({'error': 'Nenhum formulário ativo.'}, status=404)

    try:
        body = json.loads(request.body)
        respostas = body.get('respostas', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    if not respostas:
        return JsonResponse({'error': 'Nenhuma resposta fornecida.'}, status=400)

    todas_respostas = request.session.get('respostas', [])
    todas_respostas.append(respostas)
    request.session['respostas'] = todas_respostas
    request.session.modified = True

    numericas = [p for p in formulario.get('perguntas', []) if p.get('tipo') == 'numerica']
    valores_num = []
    for resp in todas_respostas:
        for item in resp:
            if any(p['id'] == item.get('pergunta_id') for p in numericas):
                try:
                    valores_num.append(float(item['valor']))
                except (ValueError, TypeError):
                    pass

    analise = calcular_estatisticas(valores_num) if valores_num else None
    if analise:
        request.session['analise'] = analise

    return JsonResponse({
        'mensagem': 'Respostas registradas com sucesso!',
        'total_respostas': len(todas_respostas),
        'respostas_numericas': len(valores_num),
        'analise': analise,
    })


def formulario_dados(request):
    formulario = request.session.get('formulario')
    respostas = request.session.get('respostas', [])
    if not formulario:
        return JsonResponse({'error': 'Nenhum formulário ativo.'}, status=404)
    if not respostas:
        return JsonResponse({'error': 'Sem respostas ainda.'}, status=404)

    pergunta_id = request.GET.get('pergunta_id')
    perguntas = formulario.get('perguntas', [])
    pergunta_obj = next((p for p in perguntas if p['id'] == pergunta_id), None)

    if not pergunta_obj:
        return JsonResponse({'error': 'Pergunta não encontrada.'}, status=404)

    total_respostas = len(respostas)

    if pergunta_obj.get('tipo') == 'multipla_escolha':
        contagem = Counter()
        for resp in respostas:
            for item in resp:
                if item.get('pergunta_id') == pergunta_id:
                    val = item.get('valor', '').strip()
                    if val:
                        contagem[val] += 1
        opcoes = pergunta_obj.get('opcoes', [])
        dados_mc = [
            {'texto': op.get('texto', ''), 'count': contagem.get(op.get('texto', ''), 0)}
            for op in opcoes
        ]
        return JsonResponse({
            'pergunta': pergunta_obj,
            'tipo': 'multipla_escolha',
            'dados_mc': dados_mc,
            'total_respostas': total_respostas,
        })

    valores = []
    for resp in respostas:
        for item in resp:
            if item.get('pergunta_id') == pergunta_id:
                try:
                    valores.append(float(item['valor']))
                except (ValueError, TypeError):
                    pass

    stats = calcular_estatisticas(valores) if valores else None
    pct = round(len(valores) / total_respostas * 100) if total_respostas > 0 else 0

    return JsonResponse({
        'pergunta': pergunta_obj,
        'tipo': pergunta_obj.get('tipo', 'numerica'),
        'valores': valores,
        'stats': stats,
        'total_respostas': total_respostas,
        'respostas_validas': len(valores),
        'percentual_validas': pct,
    })


def formulario_analise(request):
    formulario = request.session.get('formulario')
    respostas = request.session.get('respostas', [])
    if not formulario:
        return JsonResponse({'error': 'Nenhum formulário ativo.'}, status=404)

    perguntas = formulario.get('perguntas', [])
    resultado = []

    for p in perguntas:
        pid = p['id']
        tipo = p.get('tipo')

        if tipo == 'numerica':
            valores = []
            for resp in respostas:
                for item in resp:
                    if item.get('pergunta_id') == pid:
                        try:
                            valores.append(float(item['valor']))
                        except (ValueError, TypeError):
                            pass
            stats = calcular_estatisticas(valores) if valores else None
            resultado.append({'pergunta': p, 'tipo': tipo, 'stats': stats, 'valores': valores})

        elif tipo == 'multipla_escolha':
            contagem = Counter()
            for resp in respostas:
                for item in resp:
                    if item.get('pergunta_id') == pid:
                        val = item.get('valor', '').strip()
                        if val:
                            contagem[val] += 1
            opcoes = p.get('opcoes', [])
            dados_mc = [
                {'texto': op.get('texto', ''), 'count': contagem.get(op.get('texto', ''), 0)}
                for op in opcoes
            ]
            resultado.append({'pergunta': p, 'tipo': tipo, 'dados_mc': dados_mc})

        elif tipo == 'texto':
            textos = []
            for resp in respostas:
                for item in resp:
                    if item.get('pergunta_id') == pid:
                        val = item.get('valor', '').strip()
                        if val:
                            textos.append(val)
            resultado.append({'pergunta': p, 'tipo': tipo, 'textos': textos})

    return JsonResponse({
        'formulario': formulario,
        'total_respostas': len(respostas),
        'perguntas': resultado,
    })


@csrf_exempt
@require_http_methods(["POST"])
def ia_api(request):
    try:
        body = json.loads(request.body)
        pergunta = body.get('pergunta', '').strip()
        dados = body.get('dados')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    if not pergunta:
        return JsonResponse({'error': 'Pergunta é obrigatória.'}, status=400)

    resposta, erro = _gerar_insight_ia(pergunta, dados)
    if erro and not resposta:
        analise = dados or {}
        cv = (analise.get('desvio_padrao', 0) / analise.get('media', 1)) if analise.get('media') else 0
        if cv < 0.1:
            resposta = "Os dados estão muito concentrados, indicando alta consistência nas respostas."
        elif cv < 0.3:
            resposta = f"Os dados apresentam dispersão moderada. A média de {analise.get('media')} com desvio padrão de {analise.get('desvio_padrao')} indica variação razoável."
        else:
            resposta = f"Os dados possuem alta variabilidade. A amplitude de {analise.get('max', 0) - analise.get('min', 0):.2f} sugere respostas bastante diversas."
        if not analise:
            resposta = "Forneça dados numéricos para que a IA possa realizar a análise estatística."

    return JsonResponse({'resposta': resposta})


@csrf_exempt
@require_http_methods(["POST"])
def ia_csv(request):
    arquivo = request.FILES.get('arquivo')
    if not arquivo:
        return JsonResponse({'error': 'Nenhum arquivo enviado.'}, status=400)

    try:
        content = arquivo.read().decode('utf-8-sig', errors='ignore')
        reader = csv.reader(io.StringIO(content))
        valores = []
        for row in reader:
            for cell in row:
                cell = cell.strip().replace(',', '.')
                try:
                    valores.append(float(cell))
                except ValueError:
                    pass
    except Exception as e:
        return JsonResponse({'error': f'Erro ao processar CSV: {e}'}, status=400)

    if not valores:
        return JsonResponse({'error': 'Nenhum valor numérico encontrado no CSV.'}, status=400)

    stats = calcular_estatisticas(valores)
    request.session['analise'] = stats

    pergunta_auto = (
        f"Analise estes dados do CSV: {stats.get('count')} valores com "
        f"média {stats.get('media')}, desvio padrão {stats.get('desvio_padrao')}, "
        f"mínimo {stats.get('min')} e máximo {stats.get('max')}. "
        f"Quais insights e tendências você observa? Responda em português."
    )

    insight_ia, _ = _gerar_insight_ia(pergunta_auto, stats)
    insight = insight_ia or stats.get('insight', 'Análise gerada com sucesso.')

    result = dict(stats)
    result['insight'] = insight
    result['valores'] = valores
    return JsonResponse(result)
