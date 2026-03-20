import { useState } from "react";
import { ClipboardList, CheckCircle, AlertCircle } from "lucide-react";
import { useAnalisar } from "@workspace/api-client-react";
import type { AnalisarResult } from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { getIntensityColor } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

const formatNum = (num: number) =>
  Number.isInteger(num) ? num.toString() : num.toFixed(2);

function ResultCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="relative overflow-hidden bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
      <div className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: color }} />
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-800">{value}</p>
    </div>
  );
}

export default function Pesquisa() {
  const { toast } = useToast();
  const [titulo, setTitulo] = useState("");
  const [pergunta, setPergunta] = useState("");
  const [respostas, setRespostas] = useState("");
  const [result, setResult] = useState<AnalisarResult | null>(null);
  const [pesquisaInfo, setPesquisaInfo] = useState<{ titulo: string; pergunta: string } | null>(null);

  const analyzeMutation = useAnalisar({
    mutation: {
      onSuccess: (data) => {
        setResult(data);
        setPesquisaInfo({ titulo, pergunta });
        toast({ title: "Pesquisa Analisada!", description: "Os resultados estão prontos abaixo." });
      },
      onError: () => {
        toast({
          title: "Erro na Análise",
          description: "Verifique se as respostas contêm apenas números válidos.",
          variant: "destructive",
        });
      },
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!titulo.trim() || !pergunta.trim()) {
      toast({ title: "Campos obrigatórios", description: "Preencha o título e a pergunta.", variant: "destructive" });
      return;
    }

    const nums = respostas
      .split(',')
      .map(n => Number(n.trim()))
      .filter(n => !isNaN(n) && n.toString() !== '');

    if (nums.length === 0) {
      toast({ title: "Respostas inválidas", description: "Insira ao menos um número separado por vírgula.", variant: "destructive" });
      return;
    }

    analyzeMutation.mutate({ data: { numeros: nums } });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <ClipboardList className="w-8 h-8 text-emerald-600" />
          Nova Pesquisa
        </h1>
        <p className="text-slate-500 mt-2 text-lg">
          Crie uma pesquisa com respostas numéricas e analise os resultados instantaneamente.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-5">
        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Título da Pesquisa <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={titulo}
            onChange={e => setTitulo(e.target.value)}
            placeholder="Ex: Satisfação dos clientes em outubro"
            className="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Pergunta da Pesquisa <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={pergunta}
            onChange={e => setPergunta(e.target.value)}
            placeholder="Ex: De 0 a 10, como você avalia nosso atendimento?"
            className="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Respostas Numéricas <span className="text-red-500">*</span>
          </label>
          <textarea
            value={respostas}
            onChange={e => setRespostas(e.target.value)}
            placeholder="Ex: 8, 9, 7, 10, 6, 8, 9, 5, 10, 7"
            rows={4}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 transition-all resize-none"
          />
          <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Separe os números por vírgula
          </p>
        </div>

        <button
          type="submit"
          disabled={analyzeMutation.isPending}
          className="w-full py-3.5 bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold rounded-xl shadow-md shadow-emerald-500/25 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-70 disabled:cursor-not-allowed transition-all"
        >
          {analyzeMutation.isPending ? 'Analisando...' : 'Analisar Pesquisa'}
        </button>
      </form>

      <AnimatePresence>
        {result && pesquisaInfo && (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-6"
          >
            <div className="flex items-center gap-2 text-emerald-700 font-semibold">
              <CheckCircle className="w-5 h-5" />
              Resultados da Pesquisa
            </div>

            <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-5">
              <h2 className="text-lg font-bold text-slate-900">{pesquisaInfo.titulo}</h2>
              <p className="text-slate-600 mt-1">{pesquisaInfo.pergunta}</p>
              <p className="text-sm text-emerald-700 font-medium mt-2">
                {result.count} {result.count === 1 ? 'resposta coletada' : 'respostas coletadas'}
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {[
                { label: 'Média', value: formatNum(result.media), color: getIntensityColor(result.media, result.min, result.max) },
                { label: 'Mediana', value: formatNum(result.mediana), color: getIntensityColor(result.mediana, result.min, result.max) },
                { label: 'Moda', value: result.moda.length > 0 ? result.moda.map(formatNum).join(', ') : 'N/A', color: result.moda.length > 0 ? getIntensityColor(result.moda[0], result.min, result.max) : '#cbd5e1' },
                { label: 'Total', value: formatNum(result.total), color: '#6366f1' },
                { label: 'Desvio Padrão', value: formatNum(result.desvio_padrao), color: getIntensityColor(result.desvio_padrao, 0, result.max) },
                { label: 'Mínimo', value: formatNum(result.min), color: '#16a34a' },
                { label: 'Máximo', value: formatNum(result.max), color: '#dc2626' },
              ].map(card => (
                <ResultCard key={card.label} {...card} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
