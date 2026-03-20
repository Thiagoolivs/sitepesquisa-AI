import { useState } from "react";
import { ClipboardList, Plus, Trash2, Save, Send, BarChart2, CheckCircle } from "lucide-react";
import {
  useSalvarFormulario, useGetFormulario, useResponderFormulario,
} from "@workspace/api-client-react";
import type { AnalisarResult, FormularioPergunta } from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { useAnalysisContext } from "@/contexts/AnalysisContext";
import { getIntensityColor } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

type Tab = "criar" | "responder" | "resultados";
type TipoPergunta = "texto" | "numerica" | "multipla";

interface PerguntaDraft {
  id: string;
  texto: string;
  tipo: TipoPergunta;
  opcoes: string[];
}

function StatCard({ title, value, color, subtitle }: { title: string; value: string; color: string; subtitle?: string }) {
  return (
    <div className="relative overflow-hidden bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: color }} />
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{title}</p>
      <div className="flex items-baseline gap-1"><span className="text-2xl font-bold text-slate-800">{value}</span>
        {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
      </div>
    </div>
  );
}

function newPergunta(): PerguntaDraft {
  return { id: crypto.randomUUID(), texto: "", tipo: "numerica", opcoes: [""] };
}

export default function Pesquisa() {
  const { toast } = useToast();
  const { setLastResult, setSourceLabel } = useAnalysisContext();

  const [tab, setTab] = useState<Tab>("criar");
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [perguntas, setPerguntas] = useState<PerguntaDraft[]>([newPergunta()]);
  const [respostas, setRespostas] = useState<Record<string, string>>({});
  const [analise, setAnalise] = useState<AnalisarResult | null>(null);
  const [totalEnvios, setTotalEnvios] = useState(0);

  const salvarMutation = useSalvarFormulario({
    mutation: {
      onSuccess: () => {
        toast({ title: "Formulário Salvo!", description: "Acesse a aba 'Responder' para coletar dados." });
        setTab("responder");
        getFormularioQuery.refetch();
      },
      onError: () => toast({ title: "Erro ao salvar", variant: "destructive" }),
    },
  });

  const getFormularioQuery = useGetFormulario({ query: { enabled: tab === "responder" || tab === "resultados" } });

  const responderMutation = useResponderFormulario({
    mutation: {
      onSuccess: (data) => {
        toast({ title: "Respostas Enviadas!", description: data.mensagem });
        setRespostas({});
        setTotalEnvios(prev => prev + 1);
        if (data.analise) {
          setAnalise(data.analise);
          setLastResult(data.analise);
          setSourceLabel("Formulário — Pesquisa");
          setTab("resultados");
        }
      },
      onError: () => toast({ title: "Erro ao enviar respostas", variant: "destructive" }),
    },
  });

  // ── Form Builder helpers ──────────────────────────────────────────────────
  const addPergunta = () => setPerguntas(p => [...p, newPergunta()]);

  const updatePergunta = (id: string, field: keyof PerguntaDraft, value: string) =>
    setPerguntas(p => p.map(q => q.id === id ? { ...q, [field]: value } : q));

  const removePergunta = (id: string) =>
    setPerguntas(p => p.filter(q => q.id !== id));

  const updateOpcao = (id: string, idx: number, value: string) =>
    setPerguntas(p => p.map(q => q.id === id
      ? { ...q, opcoes: q.opcoes.map((o, i) => i === idx ? value : o) }
      : q));

  const addOpcao = (id: string) =>
    setPerguntas(p => p.map(q => q.id === id ? { ...q, opcoes: [...q.opcoes, ""] } : q));

  const removeOpcao = (id: string, idx: number) =>
    setPerguntas(p => p.map(q => q.id === id
      ? { ...q, opcoes: q.opcoes.filter((_, i) => i !== idx) }
      : q));

  const handleSalvar = () => {
    if (!titulo.trim()) { toast({ title: "Título obrigatório", variant: "destructive" }); return; }
    if (perguntas.some(q => !q.texto.trim())) { toast({ title: "Preencha o texto de todas as perguntas", variant: "destructive" }); return; }
    salvarMutation.mutate({
      data: {
        titulo, descricao,
        perguntas: perguntas.map(q => ({
          id: q.id, texto: q.texto, tipo: q.tipo,
          ...(q.tipo === "multipla" ? { opcoes: q.opcoes.filter(Boolean) } : {}),
        })) as FormularioPergunta[],
      },
    });
  };

  const handleResponder = () => {
    const form = getFormularioQuery.data;
    if (!form) return;
    const payload = form.perguntas.map(q => ({ pergunta_id: q.id, valor: respostas[q.id] ?? "" }));
    responderMutation.mutate({ data: { respostas: payload } });
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "criar", label: "Criar Formulário" },
    { key: "responder", label: "Responder" },
    { key: "resultados", label: "Resultados" },
  ];

  const analiseCards = analise ? [
    { title: "Média", value: fmt(analise.media), color: getIntensityColor(analise.media, analise.min, analise.max), subtitle: "avg" },
    { title: "Mediana", value: fmt(analise.mediana), color: getIntensityColor(analise.mediana, analise.min, analise.max) },
    { title: "Moda", value: analise.moda.length > 0 ? analise.moda.map(fmt).join(", ") : "N/A", color: "#cbd5e1" },
    { title: "Total", value: fmt(analise.total), color: "#6366f1", subtitle: `${analise.count} resp.` },
    { title: "Desvio Padrão", value: fmt(analise.desvio_padrao), color: getIntensityColor(analise.desvio_padrao, 0, analise.max), subtitle: "σ" },
    { title: "Mínimo", value: fmt(analise.min), color: "#16a34a" },
    { title: "Máximo", value: fmt(analise.max), color: "#dc2626" },
  ] : [];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <ClipboardList className="w-8 h-8 text-emerald-600" />
          Formulário de Pesquisa
        </h1>
        <p className="text-slate-500 mt-1">Crie formulários, colete respostas e analise os dados estatisticamente.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-xl p-1">
        {tabs.map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); if (t.key !== "criar") getFormularioQuery.refetch(); }}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold transition-all ${tab === t.key ? "bg-white shadow-sm text-slate-900" : "text-slate-500 hover:text-slate-700"}`}>
            {t.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">

        {/* ── TAB: CRIAR ──────────────────────────────────────────────────── */}
        {tab === "criar" && (
          <motion.div key="criar" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Título <span className="text-red-500">*</span></label>
              <input value={titulo} onChange={e => setTitulo(e.target.value)}
                placeholder="Ex: Satisfação dos clientes — Outubro 2025"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 transition-all" />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1">Descrição</label>
              <textarea value={descricao} onChange={e => setDescricao(e.target.value)} rows={2}
                placeholder="Descrição opcional do formulário..."
                className="w-full px-4 py-2 rounded-xl border border-slate-200 text-slate-800 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-400 transition-all" />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-700">Perguntas</p>
                <span className="text-xs text-slate-400">{perguntas.length} pergunta(s)</span>
              </div>

              {perguntas.map((q, idx) => (
                <div key={q.id} className="border border-slate-200 rounded-xl p-4 space-y-3 bg-slate-50/50">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-400 w-5 shrink-0">{idx + 1}.</span>
                    <input value={q.texto} onChange={e => updatePergunta(q.id, "texto", e.target.value)}
                      placeholder="Texto da pergunta..."
                      className="flex-1 px-3 py-2 rounded-lg border border-slate-200 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 transition-all" />
                    <select value={q.tipo} onChange={e => updatePergunta(q.id, "tipo", e.target.value)}
                      className="px-3 py-2 rounded-lg border border-slate-200 text-sm text-slate-700 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20">
                      <option value="numerica">Numérica</option>
                      <option value="texto">Texto</option>
                      <option value="multipla">Múltipla escolha</option>
                    </select>
                    <button onClick={() => removePergunta(q.id)} disabled={perguntas.length === 1}
                      className="p-1.5 text-slate-400 hover:text-red-500 disabled:opacity-30 transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  {q.tipo === "multipla" && (
                    <div className="pl-7 space-y-1.5">
                      {q.opcoes.map((opt, oi) => (
                        <div key={oi} className="flex gap-2">
                          <input value={opt} onChange={e => updateOpcao(q.id, oi, e.target.value)}
                            placeholder={`Opção ${oi + 1}`}
                            className="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/20" />
                          <button onClick={() => removeOpcao(q.id, oi)} disabled={q.opcoes.length === 1}
                            className="text-slate-400 hover:text-red-400 disabled:opacity-30 transition-colors">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                      <button onClick={() => addOpcao(q.id)}
                        className="text-xs text-emerald-600 font-semibold hover:underline flex items-center gap-1 mt-1">
                        <Plus className="w-3 h-3" /> Adicionar opção
                      </button>
                    </div>
                  )}
                </div>
              ))}

              <button onClick={addPergunta}
                className="w-full py-2.5 border-2 border-dashed border-slate-200 rounded-xl text-sm font-semibold text-slate-500 hover:border-emerald-300 hover:text-emerald-600 flex items-center justify-center gap-2 transition-colors">
                <Plus className="w-4 h-4" /> Adicionar Pergunta
              </button>
            </div>

            <button onClick={handleSalvar} disabled={salvarMutation.isPending}
              className="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-xl shadow-md hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-70 transition-all flex items-center justify-center gap-2">
              <Save className="w-5 h-5" />
              {salvarMutation.isPending ? "Salvando..." : "Salvar Formulário"}
            </button>
          </motion.div>
        )}

        {/* ── TAB: RESPONDER ──────────────────────────────────────────────── */}
        {tab === "responder" && (
          <motion.div key="responder" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4">
            {getFormularioQuery.isLoading && (
              <div className="text-center py-12 text-slate-400">Carregando formulário...</div>
            )}
            {getFormularioQuery.isError && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6 text-center">
                <p className="text-amber-700 font-medium">Nenhum formulário salvo ainda.</p>
                <button onClick={() => setTab("criar")} className="mt-2 text-sm text-emerald-600 font-semibold hover:underline">
                  Criar um formulário →
                </button>
              </div>
            )}
            {getFormularioQuery.data && (
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-5">
                <div>
                  <h2 className="text-xl font-bold text-slate-900">{getFormularioQuery.data.titulo}</h2>
                  {getFormularioQuery.data.descricao && (
                    <p className="text-slate-500 text-sm mt-1">{getFormularioQuery.data.descricao}</p>
                  )}
                  <p className="text-xs text-emerald-600 font-medium mt-2">
                    {getFormularioQuery.data.total_respostas} envio(s) registrado(s)
                  </p>
                </div>

                {getFormularioQuery.data.perguntas.map((q, idx) => (
                  <div key={q.id} className="space-y-2">
                    <label className="block text-sm font-semibold text-slate-700">
                      {idx + 1}. {q.texto}
                      {q.tipo === "numerica" && <span className="ml-1 text-xs text-slate-400">(número)</span>}
                    </label>
                    {q.tipo === "texto" && (
                      <input value={respostas[q.id] ?? ""} onChange={e => setRespostas(r => ({ ...r, [q.id]: e.target.value }))}
                        placeholder="Sua resposta..."
                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition-all" />
                    )}
                    {q.tipo === "numerica" && (
                      <input type="number" value={respostas[q.id] ?? ""} onChange={e => setRespostas(r => ({ ...r, [q.id]: e.target.value }))}
                        placeholder="0"
                        className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/30 transition-all" />
                    )}
                    {q.tipo === "multipla" && q.opcoes && (
                      <div className="space-y-2">
                        {q.opcoes.map((opt, oi) => (
                          <label key={oi} className="flex items-center gap-3 cursor-pointer group">
                            <input type="radio" name={`q-${q.id}`} value={opt}
                              checked={respostas[q.id] === opt}
                              onChange={() => setRespostas(r => ({ ...r, [q.id]: opt }))}
                              className="w-4 h-4 accent-emerald-600" />
                            <span className="text-sm text-slate-700 group-hover:text-slate-900">{opt}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}

                <button onClick={handleResponder} disabled={responderMutation.isPending}
                  className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-md hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-70 transition-all flex items-center justify-center gap-2">
                  <Send className="w-5 h-5" />
                  {responderMutation.isPending ? "Enviando..." : "Enviar Respostas"}
                </button>
              </div>
            )}
          </motion.div>
        )}

        {/* ── TAB: RESULTADOS ─────────────────────────────────────────────── */}
        {tab === "resultados" && (
          <motion.div key="resultados" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-5">
            {!analise ? (
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center space-y-3">
                <BarChart2 className="w-10 h-10 text-slate-300 mx-auto" />
                <p className="text-slate-500 font-medium">Nenhum resultado ainda.</p>
                <p className="text-sm text-slate-400">Envie respostas numéricas no formulário para ver a análise aqui.</p>
                <button onClick={() => setTab("responder")} className="text-sm text-blue-600 font-semibold hover:underline">
                  Ir para Responder →
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 text-emerald-700 font-semibold">
                  <CheckCircle className="w-5 h-5" />
                  Análise de {totalEnvios} envio(s) · {analise.count} respostas numéricas
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                  {analiseCards.map(c => <StatCard key={c.title} {...c} />)}
                </div>
                <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-4 text-sm text-indigo-700 font-medium flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 shrink-0" />
                  Dados do formulário enviados para o Dashboard e disponíveis na página de IA.
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Fix missing import
function X({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}
