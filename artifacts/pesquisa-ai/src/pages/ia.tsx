import { useState } from "react";
import { Sparkles, ArrowRight, Bot } from "lucide-react";
import { motion } from "framer-motion";

export default function IA() {
  const [query, setQuery] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [response, setResponse] = useState("");

  const handleAnalyze = () => {
    setIsAnalyzing(true);
    setResponse("");
    
    // Simulate AI thinking delay
    setTimeout(() => {
      setResponse("Funcionalidade em desenvolvimento. Em breve a Pesquisa AI oferecerá insights profundos, detecção de anomalias e projeções avançadas baseadas nos seus conjuntos de dados.");
      setIsAnalyzing(false);
    }, 1800);
  };

  return (
    <div className="max-w-3xl mx-auto pt-8 md:pt-12 pb-24">
      <div className="text-center mb-12">
        <motion.div 
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="inline-flex items-center justify-center p-3 bg-indigo-100/80 text-indigo-600 rounded-2xl mb-6 shadow-sm border border-indigo-200"
        >
          <Sparkles className="w-8 h-8" />
        </motion.div>
        <h1 className="text-4xl md:text-5xl font-display font-bold text-slate-900 tracking-tight mb-4">
          Análise com Inteligência Artificial
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
          Descreva seus dados ou faça uma pergunta específica para obter insights avançados e estatísticos gerados por IA.
        </p>
      </div>

      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="bg-white rounded-3xl p-2 shadow-xl shadow-indigo-100/40 border border-slate-200/60 mb-8 transition-shadow focus-within:shadow-indigo-200/50"
      >
        <textarea
          className="w-full h-44 p-5 bg-transparent border-none resize-none focus:ring-0 text-slate-700 placeholder:text-slate-400 font-medium text-lg outline-none"
          placeholder="Ex: Quais são as tendências ocultas e anomalias nestes dados de vendas trimestrais? O que posso projetar para o próximo mês?"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <div className="flex flex-col sm:flex-row justify-between items-center p-3 bg-slate-50/80 rounded-2xl gap-4 border border-slate-100">
          <span className="text-sm text-slate-500 font-semibold pl-3 flex items-center gap-2">
            <Bot className="w-4 h-4 text-indigo-400" />
            Alimentado por Modelos Avançados
          </span>
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || !query.trim()}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white font-semibold rounded-xl shadow-md hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5 disabled:opacity-50 disabled:transform-none transition-all"
          >
            {isAnalyzing ? "Processando a requisição..." : "Analisar com IA"}
            {!isAnalyzing && <ArrowRight className="w-5 h-5" />}
          </button>
        </div>
      </motion.div>

      {response && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100/60 rounded-3xl p-8 shadow-sm"
        >
          <div className="flex items-start gap-4">
            <div className="p-2.5 bg-indigo-600 text-white rounded-xl shadow-sm mt-1 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold font-display text-lg text-indigo-950 mb-2">
                Resposta da Pesquisa AI
              </h3>
              <p className="text-indigo-900/80 font-medium leading-relaxed text-lg">
                {response}
              </p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
