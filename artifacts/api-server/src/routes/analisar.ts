import { Router, type IRouter } from "express";
import { AnalisarBody, AnalisarResponse } from "@workspace/api-zod";
import { calcularEstatisticas } from "../lib/stats.js";

const router: IRouter = Router();

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
  const result = AnalisarResponse.parse(calcularEstatisticas(numeros));
  res.json(result);
});

export default router;
