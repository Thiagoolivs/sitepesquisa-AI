export interface EstatisticasResult {
  media: number;
  mediana: number;
  moda: number[];
  total: number;
  count: number;
  min: number;
  max: number;
  desvio_padrao: number;
}

export function calcularEstatisticas(nums: number[]): EstatisticasResult {
  const total = nums.reduce((a, b) => a + b, 0);
  const count = nums.length;
  const media = total / count;
  const min = Math.min(...nums);
  const max = Math.max(...nums);

  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const mediana =
    sorted.length % 2 === 0
      ? (sorted[mid - 1] + sorted[mid]) / 2
      : sorted[mid];

  const freq: Record<number, number> = {};
  for (const n of nums) freq[n] = (freq[n] ?? 0) + 1;
  const maxFreq = Math.max(...Object.values(freq));
  const moda =
    maxFreq === 1
      ? []
      : Object.entries(freq)
          .filter(([, c]) => c === maxFreq)
          .map(([v]) => Number(v));

  const variance =
    nums.reduce((acc, val) => acc + Math.pow(val - media, 2), 0) / count;
  const desvio_padrao = Math.sqrt(variance);

  return { media, mediana, moda, total, count, min, max, desvio_padrao };
}

export function parseCSVNumbers(content: string): number[] {
  const nums: number[] = [];
  const lines = content.split(/\r?\n/);
  for (const line of lines) {
    const cells = line.split(',');
    for (const cell of cells) {
      const n = parseFloat(cell.trim().replace(/[^0-9.\-]/g, ''));
      if (!isNaN(n)) nums.push(n);
    }
  }
  return nums;
}
