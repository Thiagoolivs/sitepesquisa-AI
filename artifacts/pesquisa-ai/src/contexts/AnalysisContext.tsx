import { createContext, useContext, useState } from "react";
import type { AnalisarResult } from "@workspace/api-client-react";

interface AnalysisContextValue {
  lastResult: AnalisarResult | null;
  setLastResult: (result: AnalisarResult) => void;
  sourceLabel: string;
  setSourceLabel: (label: string) => void;
}

const AnalysisContext = createContext<AnalysisContextValue>({
  lastResult: null,
  setLastResult: () => {},
  sourceLabel: "",
  setSourceLabel: () => {},
});

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [lastResult, setLastResult] = useState<AnalisarResult | null>(null);
  const [sourceLabel, setSourceLabel] = useState<string>("");

  return (
    <AnalysisContext.Provider value={{ lastResult, setLastResult, sourceLabel, setSourceLabel }}>
      {children}
    </AnalysisContext.Provider>
  );
}

export function useAnalysisContext() {
  return useContext(AnalysisContext);
}
