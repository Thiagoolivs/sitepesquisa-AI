import { useState, useMemo } from "react";
import { Activity, Calculator, BarChart2 } from "lucide-react";
import { useAnalisar } from "@workspace/api-client-react";
import type { AnalisarResult } from "@workspace/api-client-react";
import { useToast } from "@/hooks/use-toast";
import { getIntensityColor } from "@/lib/utils";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { motion } from "framer-motion";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  ChartTooltip,
  Legend
);

// Format numbers nicely to avoid long decimals
const formatNum = (num: number) => Number.isInteger(num) ? num.toString() : num.toFixed(2);

function StatCard({ 
  title, 
  value, 
  colorIndicator, 
  subtitle 
}: { 
  title: string, 
  value: string | number, 
  colorIndicator: string, 
  subtitle?: string 
}) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden bg-white rounded-2xl p-6 shadow-sm shadow-slate-200/50 border border-slate-200 hover:shadow-lg hover:-translate-y-1 transition-all duration-300 group"
    >
      <div 
        className="absolute left-0 top-0 bottom-0 w-1.5 transition-colors duration-500" 
        style={{ backgroundColor: colorIndicator }} 
      />
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-2">
        {title}
      </h3>
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-display font-bold text-slate-800 tracking-tight">
          {value}
        </span>
        {subtitle && <span className="text-sm font-medium text-slate-400">{subtitle}</span>}
      </div>
    </motion.div>
  );
}

export default function Dashboard() {
  const { toast } = useToast();
  const [inputStr, setInputStr] = useState("10, 25, 50, 30, 75, 20, 60");
  
  // Initialize with the mock data matching the default input string so the UI is immediately populated
  const [parsedNumbers, setParsedNumbers] = useState<number[]>([10, 25, 50, 30, 75, 20, 60]);
  const [result, setResult] = useState<AnalisarResult>({
    media: 38.57,
    mediana: 30,
    moda: [],
    total: 270,
    count: 7,
    min: 10,
    max: 75
  });

  const analyzeMutation = useAnalisar({
    mutation: {
      onSuccess: (data) => {
        setResult(data);
        toast({
          title: "Análise Concluída",
          description: "Os dados foram processados com sucesso.",
        });
      },
      onError: (err) => {
        toast({
          title: "Erro na Análise",
          description: "Não foi possível processar os dados. Verifique a formatação.",
          variant: "destructive"
        });
      }
    }
  });

  const handleAnalyze = () => {
    const nums = inputStr
      .split(',')
      .map(n => Number(n.trim()))
      .filter(n => !isNaN(n));

    if (nums.length === 0) {
      toast({
        title: "Entrada Inválida",
        description: "Por favor, insira pelo menos um número válido.",
        variant: "destructive"
      });
      return;
    }

    setParsedNumbers(nums);
    analyzeMutation.mutate({ data: { numeros: nums } });
  };

  const chartData = useMemo(() => {
    const bgColors = parsedNumbers.map(val => getIntensityColor(val, result.min, result.max));
    
    return {
      labels: parsedNumbers.map((_, i) => `Valor ${i + 1}`),
      datasets: [
        {
          label: 'Valores',
          data: parsedNumbers,
          backgroundColor: bgColors,
          borderRadius: 6,
          borderSkipped: false,
        }
      ]
    };
  }, [parsedNumbers, result.min, result.max]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        titleFont: { family: 'Inter', size: 13 },
        bodyFont: { family: 'Inter', size: 14, weight: 'bold' },
        padding: 12,
        cornerRadius: 8,
        displayColors: false,
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(226, 232, 240, 0.6)' },
        border: { dash: [4, 4] },
        ticks: { font: { family: 'Inter' } }
      },
      x: {
        grid: { display: false },
        ticks: { font: { family: 'Inter' } }
      }
    }
  };

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div>
        <h1 className="text-3xl font-display font-bold text-slate-900 flex items-center gap-3">
          <Calculator className="w-8 h-8 text-blue-600" />
          Dashboard de Análise
        </h1>
        <p className="text-slate-500 mt-2 text-lg">
          Insira uma lista de números para extrair métricas estatísticas automaticamente.
        </p>
      </div>

      {/* Input Section */}
      <div className="bg-white p-2 pl-4 rounded-2xl shadow-sm border border-slate-200/80 flex flex-col sm:flex-row gap-2 items-center relative z-10 transition-shadow focus-within:shadow-md focus-within:border-blue-300">
        <div className="flex-1 flex items-center w-full">
          <Activity className="h-5 w-5 text-slate-400 shrink-0" />
          <input
            type="text"
            className="w-full bg-transparent border-none focus:ring-0 text-slate-700 font-medium placeholder:text-slate-400 px-4 py-3 text-lg outline-none"
            placeholder="Ex: 10, 25, 50, 30..."
            value={inputStr}
            onChange={e => setInputStr(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAnalyze()}
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={analyzeMutation.isPending}
          className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl shadow-md shadow-blue-500/25 hover:shadow-lg hover:shadow-blue-500/40 hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-70 disabled:cursor-not-allowed transition-all"
        >
          {analyzeMutation.isPending ? "Processando..." : "Analisar"}
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard 
          title="Média" 
          value={formatNum(result.media)} 
          colorIndicator={getIntensityColor(result.media, result.min, result.max)} 
          subtitle="avg"
        />
        <StatCard 
          title="Mediana" 
          value={formatNum(result.mediana)} 
          colorIndicator={getIntensityColor(result.mediana, result.min, result.max)} 
          subtitle="mid"
        />
        <StatCard 
          title="Moda" 
          value={result.moda && result.moda.length > 0 ? result.moda.map(formatNum).join(', ') : "N/A"} 
          colorIndicator={result.moda && result.moda.length > 0 ? getIntensityColor(result.moda[0], result.min, result.max) : "#cbd5e1"} 
          subtitle={result.moda && result.moda.length > 1 ? "freq. (múltiplas)" : "freq."}
        />
        <StatCard 
          title="Total" 
          value={formatNum(result.total)} 
          colorIndicator={getIntensityColor(result.total, result.min, Math.max(result.max, result.total))} 
          subtitle={`de ${result.count} unid.`}
        />
      </div>

      {/* Chart Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-slate-200/80"
      >
        <div className="flex items-center justify-between mb-8">
          <h3 className="text-xl font-bold font-display text-slate-800 flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-indigo-500" />
            Distribuição dos Valores
          </h3>
          <div className="flex items-center gap-4 text-sm font-medium text-slate-500 bg-slate-50 px-4 py-2 rounded-lg">
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#16a34a]" /> Baixo</div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#eab308]" /> Médio</div>
            <div className="flex items-center gap-1.5"><div className="w-3 h-3 rounded-full bg-[#dc2626]" /> Alto</div>
          </div>
        </div>
        <div className="h-[350px] w-full">
          <Bar data={chartData} options={chartOptions} />
        </div>
      </motion.div>
    </div>
  );
}
