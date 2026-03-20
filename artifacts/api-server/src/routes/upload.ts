import { Router, type IRouter } from "express";
import multer from "multer";
import { AnalisarResponse } from "@workspace/api-zod";
import { calcularEstatisticas, parseCSVNumbers } from "../lib/stats.js";

const router: IRouter = Router();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

router.post("/upload_csv", upload.single("arquivo"), (req, res) => {
  if (!req.file) {
    res.status(400).json({ error: "Nenhum arquivo CSV enviado. Use o campo 'arquivo'." });
    return;
  }

  const content = req.file.buffer.toString("utf-8");
  const numeros = parseCSVNumbers(content);

  if (numeros.length === 0) {
    res.status(400).json({ error: "Nenhum valor numérico encontrado no arquivo CSV." });
    return;
  }

  const result = AnalisarResponse.parse(calcularEstatisticas(numeros));
  res.json(result);
});

export default router;
