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

from .models import Formulario, ItemResposta, OpcaoPergunta, Pergunta, RespostaFormulario
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


def _get_formulario(request):
    formulario_id = request.session.get('formulario_id')
    if not formulario_id:
        return None
    try:
        return Formulario.objects.prefetch_related('perguntas__opcoes').get(pk=formulario_id)
    except Formulario.DoesNotExist:
        request.session.pop('formulario_id', None)
        return None


def _perguntas_numericas_db(formulario):
    if not formulario:
        return [], None
    perguntas = list(formulario.perguntas.filter(tipo='numerica').order_by('ordem'))
    principal = next((p for p in perguntas if p.principal), None)
    principal_id = principal.pergunta_id if principal else (perguntas[0].pergunta_id if perguntas else None)
    perguntas_dict = [{'id': p.pergunta_id, 'texto': p.texto, 'tipo': p.tipo, 'principal': p.principal} for p in perguntas]
    return perguntas_dict, principal_id


def _get_valores_pergunta(formulario, pergunta_id):
    valores = []
    itens = ItemResposta.objects.filter(
        resposta__formulario=formulario,
        pergunta_id=pergunta_id,
    ).values_list('valor', flat=True)
    for v in itens:
        try:
            valores.append(float(v))
        except (ValueError, TypeError):
            pass
    return valores


def dashboard(request):
    formulario = _get_formulario(request)
    analise = request.session.get('analise')

    perguntas_num, pergunta_principal_id = _perguntas_numericas_db(formulario)

    if not analise and formulario and pergunta_principal_id:
        valores = _get_valores_pergunta(formulario, pergunta_principal_id)
        if valores:
            analise = calcular_estatisticas(valores)
            request.session['analise'] = analise

    return render(request, 'dashboard.html', {
        'active_page': 'dashboard',
        'analise': analise,
        'perguntas_numericas': perguntas_num,
        'pergunta_principal_id': pergunta_principal_id,
    })


def pesquisa(request):
    formulario = _get_formulario(request)
    formulario_dict = formulario.to_dict() if formulario else None
    return render(request, 'pesquisa.html', {
        'active_page': 'pesquisa',
        'formulario': formulario_dict,
    })


def ia_page(request):
    analise = request.session.get('analise')
    return render(request, 'ia.html', {
        'active_page': 'ia',
        'analise': analise,
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
        formulario = _get_formulario(request)
        if not formulario:
            return JsonResponse({'error': 'Nenhum formulário salvo.'}, status=404)
        resp = formulario.to_dict()
        resp['total_respostas'] = formulario.respostas.count()
        return JsonResponse(resp)

    elif request.method == 'POST':
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido.'}, status=400)

        titulo = body.get('titulo', '').strip()
        if not titulo:
            return JsonResponse({'error': 'Título é obrigatório.'}, status=400)
        perguntas_data = body.get('perguntas', [])
        if not perguntas_data:
            return JsonResponse({'error': 'Adicione ao menos uma pergunta.'}, status=400)
        for p in perguntas_data:
            if not p.get('texto', '').strip():
                return JsonResponse({'error': 'Todas as perguntas precisam de texto.'}, status=400)
            if p.get('tipo') == 'multipla_escolha':
                opcoes = p.get('opcoes', [])
                if len(opcoes) < 2:
                    return JsonResponse({'error': 'Pergunta de múltipla escolha precisa de ao menos 2 opções.'}, status=400)
                for op in opcoes:
                    if not op.get('texto', '').strip():
                        return JsonResponse({'error': 'Todas as opções precisam ter texto.'}, status=400)

        formulario = Formulario.objects.create(
            titulo=titulo,
            descricao=body.get('descricao', ''),
        )

        for i, p_data in enumerate(perguntas_data):
            pergunta = Pergunta.objects.create(
                formulario=formulario,
                pergunta_id=p_data.get('id', f'p{i}'),
                texto=p_data['texto'],
                tipo=p_data.get('tipo', 'numerica'),
                principal=p_data.get('principal', False),
                ordem=i,
            )
            if p_data.get('tipo') == 'multipla_escolha':
                for op in p_data.get('opcoes', []):
                    OpcaoPergunta.objects.create(pergunta=pergunta, texto=op['texto'])

        request.session['formulario_id'] = formulario.pk
        request.session['analise'] = None
        return JsonResponse({'ok': True, 'mensagem': 'Formulário salvo com sucesso!', 'id': formulario.pk})

    return JsonResponse({'error': 'Método não suportado.'}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def formulario_responder(request):
    formulario = _get_formulario(request)
    if not formulario:
        return JsonResponse({'error': 'Nenhum formulário ativo.'}, status=404)

    try:
        body = json.loads(request.body)
        respostas_data = body.get('respostas', [])
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    if not respostas_data:
        return JsonResponse({'error': 'Nenhuma resposta fornecida.'}, status=400)

    resposta = RespostaFormulario.objects.create(formulario=formulario)
    for item in respostas_data:
        ItemResposta.objects.create(
            resposta=resposta,
            pergunta_id=item.get('pergunta_id', ''),
            valor=str(item.get('valor', '')),
        )

    perguntas_num = list(formulario.perguntas.filter(tipo='numerica').values_list('pergunta_id', flat=True))
    valores_num = []
    for pid in perguntas_num:
        valores_num.extend(_get_valores_pergunta(formulario, pid))

    analise = calcular_estatisticas(valores_num) if valores_num else None
    if analise:
        request.session['analise'] = analise

    total_respostas = formulario.respostas.count()
    return JsonResponse({
        'mensagem': 'Respostas registradas com sucesso!',
        'total_respostas': total_respostas,
        'respostas_numericas': len(valores_num),
        'analise': analise,
    })


def formulario_dados(request):
    formulario = _get_formulario(request)
    if not formulario:
        return JsonResponse({'error': 'Nenhum formulário ativo.'}, status=404)

    total_respostas = formulario.respostas.count()
    if total_respostas == 0:
        return JsonResponse({'error': 'Sem respostas ainda.'}, status=404)

    pergunta_id = request.GET.get('pergunta_id')
    try:
        pergunta_obj = formulario.perguntas.get(pergunta_id=pergunta_id)
    except Pergunta.DoesNotExist:
        return JsonResponse({'error': 'Pergunta não encontrada.'}, status=404)

    pergunta_dict = {
        'id': pergunta_obj.pergunta_id,
        'texto': pergunta_obj.texto,
        'tipo': pergunta_obj.tipo,
        'principal': pergunta_obj.principal,
    }

    if pergunta_obj.tipo == 'multipla_escolha':
        itens = ItemResposta.objects.filter(
            resposta__formulario=formulario,
            pergunta_id=pergunta_id,
        ).values_list('valor', flat=True)
        contagem = Counter(itens)
        opcoes = pergunta_obj.opcoes.all()
        dados_mc = [{'texto': op.texto, 'count': contagem.get(op.texto, 0)} for op in opcoes]
        return JsonResponse({
            'pergunta': pergunta_dict,
            'tipo': 'multipla_escolha',
            'dados_mc': dados_mc,
            'total_respostas': total_respostas,
        })

    valores = _get_valores_pergunta(formulario, pergunta_id)
    stats = calcular_estatisticas(valores) if valores else None
    pct = round(len(valores) / total_respostas * 100) if total_respostas > 0 else 0

    return JsonResponse({
        'pergunta': pergunta_dict,
        'tipo': pergunta_obj.tipo,
        'valores': valores,
        'stats': stats,
        'total_respostas': total_respostas,
        'respostas_validas': len(valores),
        'percentual_validas': pct,
    })


def formulario_analise(request):
    formulario = _get_formulario(request)
    if not formulario:
        return JsonResponse({'error': 'Nenhum formulário ativo.'}, status=404)

    formulario_dict = formulario.to_dict()
    total_respostas = formulario.respostas.count()
    resultado = []

    for p in formulario.perguntas.order_by('ordem'):
        pid = p.pergunta_id
        tipo = p.tipo
        p_dict = {'id': pid, 'texto': p.texto, 'tipo': tipo, 'principal': p.principal}

        if tipo == 'numerica':
            valores = _get_valores_pergunta(formulario, pid)
            stats = calcular_estatisticas(valores) if valores else None
            resultado.append({'pergunta': p_dict, 'tipo': tipo, 'stats': stats, 'valores': valores})

        elif tipo == 'multipla_escolha':
            itens = ItemResposta.objects.filter(
                resposta__formulario=formulario,
                pergunta_id=pid,
            ).values_list('valor', flat=True)
            contagem = Counter(itens)
            opcoes = p.opcoes.all()
            dados_mc = [{'texto': op.texto, 'count': contagem.get(op.texto, 0)} for op in opcoes]
            resultado.append({'pergunta': p_dict, 'tipo': tipo, 'dados_mc': dados_mc})

        elif tipo == 'texto':
            textos = list(
                ItemResposta.objects.filter(
                    resposta__formulario=formulario,
                    pergunta_id=pid,
                ).exclude(valor='').values_list('valor', flat=True)
            )
            resultado.append({'pergunta': p_dict, 'tipo': tipo, 'textos': textos})

    return JsonResponse({
        'formulario': formulario_dict,
        'total_respostas': total_respostas,
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
