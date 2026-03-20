import { Router, type IRouter } from "express";
import { IaAnaliseBody, IaAnaliseResponse } from "@workspace/api-zod";

const router: IRouter = Router();

router.post("/ia", async (req, res) => {
  const parseResult = IaAnaliseBody.safeParse(req.body);
  if (!parseResult.success) {
    res.status(400).json({ error: "Dados inválidos para análise IA." });
    return;
  }

  const { pergunta, dados } = parseResult.data;

  const groqApiKey = process.env["GROQ_API_KEY"];
  if (!groqApiKey) {
    res.status(503).json({ error: "Serviço de IA não configurado. Configure a variável de ambiente GROQ_API_KEY." });
    return;
  }

  const dadosStr = dados
    ? `Média: ${dados.media?.toFixed(2)}, Mediana: ${dados.mediana?.toFixed(2)}, ` +
      `Moda: ${dados.moda && dados.moda.length > 0 ? dados.moda.join(", ") : "N/A"}, ` +
      `Total: ${dados.total}, Contagem: ${dados.count}, ` +
      `Mínimo: ${dados.min}, Máximo: ${dados.max}, ` +
      `Desvio Padrão: ${dados.desvio_padrao?.toFixed(2)}`
    : "Nenhum dado estatístico fornecido.";

  const prompt = `Você é um especialista em análise de dados e estatística. Analise os seguintes dados estatísticos e responda à pergunta do usuário de forma clara, objetiva e em português.

Dados estatísticos: ${dadosStr}

Pergunta/Contexto do usuário: ${pergunta}

Forneça uma análise concisa (máximo 3 parágrafos), com insights relevantes baseados nos dados fornecidos.`;

  try {
    const groqResponse = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${groqApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "llama3-8b-8192",
        messages: [{ role: "user", content: prompt }],
        max_tokens: 600,
        temperature: 0.7,
      }),
    });

    if (!groqResponse.ok) {
      const errorText = await groqResponse.text();
      console.error("Groq API error:", errorText);
      res.status(503).json({ error: "Erro ao conectar com o serviço de IA. Tente novamente." });
      return;
    }

    const groqData = await groqResponse.json() as {
      choices: Array<{ message: { content: string } }>;
    };

    const resposta = groqData.choices?.[0]?.message?.content ?? "Não foi possível gerar uma análise.";
    const result = IaAnaliseResponse.parse({ resposta });
    res.json(result);
  } catch (err) {
    console.error("IA route error:", err);
    res.status(503).json({ error: "Erro inesperado ao processar análise com IA." });
  }
});

export default router;
