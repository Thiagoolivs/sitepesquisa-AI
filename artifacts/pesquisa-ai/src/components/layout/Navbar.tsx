import { Link, useLocation } from "wouter";
import { BarChart3, Sparkles, ClipboardList } from "lucide-react";
import { cn } from "@/lib/utils";

export function Navbar() {
  const [location] = useLocation();

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/50 bg-white/80 backdrop-blur-md shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-xl shadow-md shadow-blue-600/20">
              <BarChart3 className="h-5 w-5 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight text-slate-900">
              Pesquisa AI
            </span>
          </div>
          <nav className="flex items-center gap-1">
            <Link
              href="/"
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200",
                location === "/"
                  ? "bg-slate-100 text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              )}
            >
              Dashboard
            </Link>
            <Link
              href="/pesquisa"
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center gap-1.5",
                location === "/pesquisa"
                  ? "bg-emerald-50 text-emerald-700 shadow-sm border border-emerald-100/50"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              )}
            >
              <ClipboardList className="w-4 h-4" />
              Pesquisa
            </Link>
            <Link
              href="/ia"
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200 flex items-center gap-1.5",
                location === "/ia"
                  ? "bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100/50"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              )}
            >
              <Sparkles className="w-4 h-4" />
              IA
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
