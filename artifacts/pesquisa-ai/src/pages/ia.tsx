import { useState } from "react";
import { Sparkles, ArrowRight, Bot, Database, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useIaAnalise, useAnalisar } from "@workspace/api-client-react";
import type { AnalisarResult } from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { useAnalysisContext } from "@/contexts/AnalysisContext";

export default function IA() {
  const { toast } = useToast();
  const { lastResult, sourceLabel } = useAnalysisContext();

  const [pergunta, setPergunta] = useState("");
  const [numerosStr, setNumerosStr] = useState("");
  const [resposta, setResposta] = useState("");
  const [localDados, setLocalDados] = useState<AnalisarResult | null>(null);

  // Use context result if available, otherwise use locally loaded data
  const dadosParaIA = lastResult ?? localDados;

  const analyzeMutation = useAnalisar({
    mutation: {
      onSuccess: (data) => {
        setLocalDados(data);
        toast({ title: "Dados carregados", description: `${data.count} valores analisados.` });
      },
      onError: () => toast({ title: "Erro ao carregar dados", variant: "destructive" }),
    },
  });

  const iaMutation = useIaAnalise({
    mutation: {
      onSuccess: (data) => setResposta(data.resposta),
      onError: (err: unknown) => {
        const msg = err && typeof err === "object" && "message" in err ? String((err as { message: string }).message) : "Erro ao conectar com a IA.";
        setResposta(`⚠️ ${msg}`);
        toast({ title: "Erro na IA", description: msg, variant: "destructive" });
      },
    },
  });

  const handleLoadData = () => {
    const nums = numerosStr.split(",").map(n => Number(n.trim())).filter(n => !isNaN(n) && n.toString() !== "");
    if (nums.length === 0) { toast({ title: "Dados inválidos", description: "Insira números separados por vírgula.", variant: "destructive" }); return; }
    analyzeMutation.mutate({ data: { numeros: nums } });
  };

  const handleAnalyze = () => {
    if (!pergunta.trim()) { toast({ title: "Digite uma pergunta", variant: "destructive" }); return; }
    setResposta("");
    iaMutation.mutate({ data: { pergunta, dados: dadosParaIA ?? undefined } });
  };

  return (
    <div className="max-w-3xl mx-auto pt-4 pb-24 space-y-8">
      <div className="text-center">
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
          className="inline-flex items-center justify-center p-3 bg-indigo-100/80 text-indigo-600 rounded-2xl mb-5 shadow-sm border border-indigo-200">
          <Sparkles className="w-8 h-8" />
        </motion.div>
        <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-3">
          Análise com Inteligência Artificial
        </h1>
        <p className="text-lg text-slate-600">
          Use os dados analisados e faça perguntas — a IA responde em português.
        </p>
      </div>

      {/* Context data badge */}
      <AnimatePresence>
        {lastResult && sourceLabel && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-4 py-3">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>Dados carregados automaticamente de: <strong>{sourceLabel}</strong> ({lastResult.count} valores, média: {lastResult.media.toFixed(2)})</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Optional manual data input */}
      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
        className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-600">
          <Database className="w-4 h-4 text-blue-500" />
          {lastResult ? "Ou inserir novos dados manualmente" : "Carregar dados numéricos (opcional)"}
        </div>
        <div className="flex gap-2">
          <input type="text" value={numerosStr} onChange={e => setNumerosStr(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleLoadData()}
            placeholder="Ex: 10, 25, 50, 30, 75, 20, 60"
            className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 text-sm transition-all" />
          <button onClick={handleLoadData} disabled={analyzeMutation.isPending}
            className="px-4 py-2.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-60 transition-all text-sm">
            {analyzeMutation.isPending ? "..." : "Carregar"}
          </button>
        </div>
        {localDados && !lastResult && (
          <p className="text-xs text-emerald-600 font-medium">
            ✓ {localDados.count} valores — média: {localDados.media.toFixed(2)}, desvio: {localDados.desvio_padrao.toFixed(2)}
          </p>
        )}
      </motion.div>

      {/* Question input */}
      <motion.div initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }}
        className="bg-white rounded-3xl p-2 shadow-xl shadow-indigo-100/40 border border-slate-200/60 transition-shadow focus-within:shadow-indigo-200/50">
        <textarea
          className="w-full h-40 p-5 bg-transparent border-none resize-none focus:ring-0 text-slate-700 placeholder:text-slate-400 font-medium text-lg outline-none"
          placeholder="Ex: O que os dados indicam? O desvio padrão é preocupante? Quais tendências você observa?"
          value={pergunta}
          onChange={e => setPergunta(e.target.value)}
        />
        <div className="flex flex-col sm:flex-row justify-between items-center p-3 bg-slate-50/80 rounded-2xl gap-3 border border-slate-100">
          <span className="text-sm text-slate-500 font-semibold pl-2 flex items-center gap-2">
            <Bot className="w-4 h-4 text-indigo-400" />
            Powered by Groq · Llama 3.1
          </span>
          <button onClick={handleAnalyze} disabled={iaMutation.isPending || !pergunta.trim()}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl shadow-md hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none transition-all">
            {iaMutation.isPending ? "Gerando análise..." : "Gerar Análise"}
            {!iaMutation.isPending && <ArrowRight className="w-5 h-5" />}
          </button>
        </div>
      </motion.div>

      <AnimatePresence>
        {resposta && (
          <motion.div key="resposta" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100/60 rounded-3xl p-8 shadow-sm">
            <div className="flex items-start gap-4">
              <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-sm mt-1 shrink-0">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-indigo-950 mb-3">Análise da Pesquisa AI</h3>
                <p className="text-indigo-900/80 font-medium leading-relaxed whitespace-pre-line">{resposta}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
