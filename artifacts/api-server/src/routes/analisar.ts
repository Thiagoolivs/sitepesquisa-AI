import { Router, type IRouter } from "express";
import { AnalisarBody, AnalisarResponse } from "@workspace/api-zod";

const router: IRouter = Router();

function calcularMedia(nums: number[]): number {
  return nums.reduce((a, b) => a + b, 0) / nums.length;
}

function calcularMediana(nums: number[]): number {
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) {
    return (sorted[mid - 1] + sorted[mid]) / 2;
  }
  return sorted[mid];
}

function calcularModa(nums: number[]): number[] {
  const freq: Record<number, number> = {};
  for (const n of nums) {
    freq[n] = (freq[n] ?? 0) + 1;
  }
  const maxFreq = Math.max(...Object.values(freq));
  if (maxFreq === 1) return [];
  return Object.entries(freq)
    .filter(([, count]) => count === maxFreq)
    .map(([val]) => Number(val));
}

function calcularDesvioPadrao(nums: number[], media: number): number {
  const variance = nums.reduce((acc, val) => acc + Math.pow(val - media, 2), 0) / nums.length;
  return Math.sqrt(variance);
}

router.post("/analisar", (req, res) => {
  const parseResult = AnalisarBody.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({ error: "Dados inválidos. Envie uma lista de números." });
    return;
  }

  const { numeros } = parseResult.data;

  if (!numeros || numeros.length === 0) {
    res.status(400).json({ error: "A lista de números não pode estar vazia." });
    return;
  }

  const media = calcularMedia(numeros);
  const mediana = calcularMediana(numeros);
  const moda = calcularModa(numeros);
  const total = numeros.reduce((a, b) => a + b, 0);
  const count = numeros.length;
  const min = Math.min(...numeros);
  const max = Math.max(...numeros);
  const desvio_padrao = calcularDesvioPadrao(numeros, media);

  const result = AnalisarResponse.parse({ media, mediana, moda, total, count, min, max, desvio_padrao });
  res.json(result);
});

export default router;
