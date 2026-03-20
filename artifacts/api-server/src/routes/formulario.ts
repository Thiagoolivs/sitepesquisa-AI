import { Router, type IRouter } from "express";
import {
  SalvarFormularioBody,
  SalvarFormularioResponse,
  GetFormularioResponse,
  ResponderFormularioBody,
  ResponderFormularioResponse,
  GetFormularioAnaliseResponse,
} from "@workspace/api-zod";
import { calcularEstatisticas } from "../lib/stats.js";

const router: IRouter = Router();

interface PerguntaData {
  id: string;
  texto: string;
  tipo: "texto" | "numerica" | "multipla";
  opcoes?: string[];
}

interface FormularioData {
  titulo: string;
  descricao?: string;
  perguntas: PerguntaData[];
}

interface RespostaData {
  pergunta_id: string;
  valor: string;
}

// In-memory storage
let formularioSalvo: FormularioData | null = null;
let respostasArmazenadas: RespostaData[][] = [];

router.post("/formulario", (req, res) => {
  const parsed = SalvarFormularioBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Dados do formulário inválidos." });
    return;
  }
  formularioSalvo = parsed.data as FormularioData;
  respostasArmazenadas = [];

  const result = SalvarFormularioResponse.parse({
    titulo: formularioSalvo.titulo,
    descricao: formularioSalvo.descricao,
    perguntas: formularioSalvo.perguntas,
    total_respostas: 0,
  });
  res.json(result);
});

router.get("/formulario", (_req, res) => {
  if (!formularioSalvo) {
    res.status(404).json({ error: "Nenhum formulário salvo ainda." });
    return;
  }
  const result = GetFormularioResponse.parse({
    titulo: formularioSalvo.titulo,
    descricao: formularioSalvo.descricao,
    perguntas: formularioSalvo.perguntas,
    total_respostas: respostasArmazenadas.length,
  });
  res.json(result);
});

router.post("/formulario/responder", (req, res) => {
  const parsed = ResponderFormularioBody.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Respostas inválidas." });
    return;
  }

  const { respostas } = parsed.data;
  respostasArmazenadas.push(respostas as RespostaData[]);

  // Filter numeric answers across all submissions
  const numerosColetados: number[] = [];
  for (const submissao of respostasArmazenadas) {
    for (const r of submissao) {
      const n = parseFloat(r.valor);
      if (!isNaN(n)) numerosColetados.push(n);
    }
  }

  const analise =
    numerosColetados.length > 0
      ? calcularEstatisticas(numerosColetados)
      : undefined;

  const result = ResponderFormularioResponse.parse({
    mensagem: `Resposta registrada! Total: ${respostasArmazenadas.length} envio(s).`,
    respostas_numericas: numerosColetados.length,
    analise,
  });
  res.json(result);
});

router.get("/formulario/analise", (_req, res) => {
  const numerosColetados: number[] = [];
  for (const submissao of respostasArmazenadas) {
    for (const r of submissao) {
      const n = parseFloat(r.valor);
      if (!isNaN(n)) numerosColetados.push(n);
    }
  }

  if (numerosColetados.length === 0) {
    res.status(404).json({ error: "Nenhuma resposta numérica disponível para análise." });
    return;
  }

  const result = GetFormularioAnaliseResponse.parse(calcularEstatisticas(numerosColetados));
  res.json(result);
});

export default router;
