import { useState, useMemo, useRef } from "react";
import { Activity, Calculator, BarChart2, Upload, FileText, X } from "lucide-react";
import { useAnalisar } from "@workspace/api-client-react";
import type { AnalisarResult } from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { useAnalysisContext } from "@/contexts/AnalysisContext";
import { getIntensityColor } from "@/lib/utils";
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  Title, Tooltip as ChartTooltip, Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import { motion, AnimatePresence } from "framer-motion";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, ChartTooltip, Legend);

const fmt = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(2));

function StatCard({ title, value, color, subtitle, delay = 0 }: {
  title: string; value: string | number; color: string; subtitle?: string; delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="relative overflow-hidden bg-white rounded-2xl p-5 shadow-sm border border-slate-200 hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
    >
      <div className="absolute left-0 top-0 bottom-0 w-1.5" style={{ backgroundColor: color }} />
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{title}</p>
      <div className="flex items-baseline gap-1.5">
        <span className="text-3xl font-bold text-slate-800">{value}</span>
        {subtitle && <span className="text-sm text-slate-400 font-medium">{subtitle}</span>}
      </div>
    </motion.div>
  );
}

const DEFAULT_NUMBERS = [10, 25, 50, 30, 75, 20, 60];
const DEFAULT_RESULT: AnalisarResult = {
  media: 38.57, mediana: 30, moda: [], total: 270,
  count: 7, min: 10, max: 75, desvio_padrao: 21.82,
};

export default function Dashboard() {
  const { toast } = useToast();
  const { lastResult, sourceLabel } = useAnalysisContext();
  const [inputStr, setInputStr] = useState("10, 25, 50, 30, 75, 20, 60");
  const [parsedNumbers, setParsedNumbers] = useState<number[]>(DEFAULT_NUMBERS);
  const [result, setResult] = useState<AnalisarResult>(DEFAULT_RESULT);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvLoading, setCsvLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const displayResult = lastResult ?? result;

  const analyzeMutation = useAnalisar({
    mutation: {
      onSuccess: (data) => {
        setResult(data);
        toast({ title: "Análise Concluída", description: "Estatísticas calculadas com sucesso." });
      },
      onError: () => toast({ title: "Erro", description: "Verifique os dados inseridos.", variant: "destructive" }),
    },
  });

  const handleAnalyze = () => {
    const nums = inputStr.split(",").map(n => Number(n.trim())).filter(n => !isNaN(n) && n.toString() !== "");
    if (nums.length === 0) {
      toast({ title: "Entrada inválida", description: "Insira ao menos um número.", variant: "destructive" });
      return;
    }
    setParsedNumbers(nums);
    analyzeMutation.mutate({ data: { numeros: nums } });
  };

  const handleCSVUpload = async () => {
    if (!csvFile) return;
    setCsvLoading(true);
    try {
      const formData = new FormData();
      formData.append("arquivo", csvFile);
      const res = await fetch("/api/upload_csv", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Erro ao processar CSV");
      setResult(data);
      setParsedNumbers([]);
      toast({ title: "CSV Analisado!", description: `${data.count} valores numéricos encontrados.` });
      setCsvFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      toast({ title: "Erro no CSV", description: String(err), variant: "destructive" });
    } finally {
      setCsvLoading(false);
    }
  };

  const chartNumbers = parsedNumbers.length > 0 ? parsedNumbers : [];
  const chartData = useMemo(() => ({
    labels: chartNumbers.map((_, i) => `V${i + 1}`),
    datasets: [{
      label: "Valores",
      data: chartNumbers,
      backgroundColor: chartNumbers.map(v => getIntensityColor(v, displayResult.min, displayResult.max)),
      borderRadius: 6,
      borderSkipped: false,
    }],
  }), [chartNumbers, displayResult.min, displayResult.max]);

  const chartOptions = {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "rgba(15,23,42,.95)", padding: 12, cornerRadius: 8,
        displayColors: false, bodyFont: { family: "Inter", size: 14 },
      },
    },
    scales: {
      y: { beginAtZero: true, grid: { color: "rgba(226,232,240,.6)" }, border: { dash: [4, 4] }, ticks: { font: { family: "Inter", size: 11 } } },
      x: { grid: { display: false }, ticks: { font: { family: "Inter", size: 11 } } },
    },
  };

  const cards = [
    { title: "Média", value: fmt(displayResult.media), color: getIntensityColor(displayResult.media, displayResult.min, displayResult.max), subtitle: "avg" },
    { title: "Mediana", value: fmt(displayResult.mediana), color: getIntensityColor(displayResult.mediana, displayResult.min, displayResult.max), subtitle: "mid" },
    { title: "Moda", value: displayResult.moda.length > 0 ? displayResult.moda.map(fmt).join(", ") : "N/A", color: displayResult.moda.length > 0 ? getIntensityColor(displayResult.moda[0], displayResult.min, displayResult.max) : "#cbd5e1", subtitle: "freq." },
    { title: "Total", value: fmt(displayResult.total), color: "#6366f1", subtitle: `${displayResult.count} itens` },
    { title: "Desvio Padrão", value: fmt(displayResult.desvio_padrao), color: getIntensityColor(displayResult.desvio_padrao, 0, displayResult.max), subtitle: "σ" },
    { title: "Mínimo", value: fmt(displayResult.min), color: "#16a34a", subtitle: "menor" },
    { title: "Máximo", value: fmt(displayResult.max), color: "#dc2626", subtitle: "maior" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Calculator className="w-8 h-8 text-blue-600" />
          Dashboard de Análise
        </h1>
        <p className="text-slate-500 mt-1 text-base">
          Insira números, faça upload de CSV ou colete dados de formulários.
        </p>
      </div>

      {/* Source badge */}
      <AnimatePresence>
        {lastResult && sourceLabel && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex items-center gap-2 text-sm text-indigo-700 bg-indigo-50 border border-indigo-100 rounded-xl px-4 py-2 w-fit">
            <FileText className="w-4 h-4" />
            Exibindo dados de: <strong>{sourceLabel}</strong>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Number input */}
      <div className="bg-white p-2 pl-4 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col sm:flex-row gap-2 items-center focus-within:shadow-md focus-within:border-blue-300 transition-shadow">
        <div className="flex-1 flex items-center w-full">
          <Activity className="h-5 w-5 text-slate-400 shrink-0" />
          <input
            type="text"
            className="w-full bg-transparent border-none focus:ring-0 text-slate-700 font-medium placeholder:text-slate-400 px-4 py-3 text-lg outline-none"
            placeholder="Ex: 10, 25, 50, 30..."
            value={inputStr}
            onChange={e => setInputStr(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleAnalyze()}
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzeMutation.isPending}
          className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-md shadow-blue-500/25 hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-70 transition-all"
        >
          {analyzeMutation.isPending ? "Processando..." : "Analisar"}
        </button>
      </div>

      {/* CSV Upload */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-3">
          <Upload className="w-4 h-4 text-emerald-500" />
          Upload de CSV
        </div>
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <label className="flex-1 flex items-center gap-3 cursor-pointer border-2 border-dashed border-slate-200 hover:border-emerald-300 rounded-xl px-4 py-3 transition-colors">
            <Upload className="w-5 h-5 text-slate-400 shrink-0" />
            <span className="text-slate-500 text-sm truncate">
              {csvFile ? csvFile.name : "Clique para selecionar um arquivo .csv"}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={e => setCsvFile(e.target.files?.[0] ?? null)}
            />
          </label>
          {csvFile && (
            <button onClick={() => { setCsvFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
              className="p-2 text-slate-400 hover:text-red-500 transition-colors">
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleCSVUpload}
            disabled={!csvFile || csvLoading}
            className="px-6 py-3 bg-emerald-500 text-white font-semibold rounded-xl shadow-sm hover:bg-emerald-600 hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {csvLoading ? "Analisando..." : "Analisar CSV"}
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2">Valores numéricos são extraídos automaticamente de qualquer coluna.</p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {cards.map((c, i) => (
          <StatCard key={c.title} title={c.title} value={c.value} color={c.color} subtitle={c.subtitle} delay={i * 0.04} />
        ))}
      </div>

      {/* Chart */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
        className="bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-slate-200/80">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-indigo-500" />
            Distribuição dos Valores
          </h3>
          <div className="flex items-center gap-3 text-xs font-medium text-slate-500 bg-slate-50 px-3 py-2 rounded-lg">
            <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-[#16a34a]" /> Baixo</div>
            <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-[#eab308]" /> Médio</div>
            <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-[#dc2626]" /> Alto</div>
          </div>
        </div>
        <div className="h-[300px] w-full">
          {chartNumbers.length > 0
            ? <Bar data={chartData} options={chartOptions} />
            : <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                Insira números acima para ver o gráfico
              </div>
          }
        </div>
      </motion.div>
    </div>
  );
}
