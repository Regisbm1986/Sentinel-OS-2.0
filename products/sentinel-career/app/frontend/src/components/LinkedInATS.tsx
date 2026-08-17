import React, { useMemo, useState } from "react";
import { Linkedin, Sparkles, Cpu, Lock, Copy, Check, ChevronRight, ShieldOff, CheckCircle2, AlertTriangle } from "lucide-react";
import { LinkedInAnalysis, PlanType } from "../types";

// Reconhece URLs de perfil pessoal do LinkedIn em variações comuns
// (com/sem protocolo, com/sem www, subdomínios de país, barra final, query string).
const LINKEDIN_PROFILE_URL_RE = /^(?:https?:\/\/)?(?:[a-z]{2,3}\.)?linkedin\.com\/in\/([a-zA-Z0-9\-_%]{3,100})\/?(?:[?#].*)?$/i;

function extractLinkedInHandle(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const match = trimmed.match(LINKEDIN_PROFILE_URL_RE);
  return match ? match[1] : null;
}

interface LinkedInATSProps {
  currentPlan: PlanType;
  linkedinUrl: string;
  setLinkedinUrl: (url: string) => void;
  linkedinText: string;
  setLinkedinText: (text: string) => void;
  report: LinkedInAnalysis | null;
  onOptimize: () => Promise<void>;
  isOptimizing: boolean;
  linkedinAvailable: boolean;
}

export default function LinkedInATS({
  currentPlan,
  linkedinUrl,
  setLinkedinUrl,
  linkedinText,
  setLinkedinText,
  report,
  onOptimize,
  isOptimizing,
  linkedinAvailable,
}: LinkedInATSProps) {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const disableInputs = useMemo(() => !linkedinAvailable || currentPlan === "free", [linkedinAvailable, currentPlan]);

  const linkedinHandle = useMemo(() => extractLinkedInHandle(linkedinUrl), [linkedinUrl]);
  const linkedinUrlStatus: "empty" | "recognized" | "unrecognized" = useMemo(() => {
    if (!linkedinUrl.trim()) return "empty";
    return linkedinHandle ? "recognized" : "unrecognized";
  }, [linkedinUrl, linkedinHandle]);

  const handleCopy = (text: string, sectionId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(sectionId);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const isLocked = currentPlan === "free";

  return (
    <div id="linkedin-panel" className="relative">
      {isLocked && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-[4px] rounded-xl z-20 flex flex-col items-center justify-center text-center p-6 border border-slate-800">
          <div className="p-4 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-full mb-3">
            <Lock className="h-6 w-6" />
          </div>
          <span className="bg-purple-500/10 text-purple-400 border border-purple-500/30 text-[9px] font-mono px-2 py-0.5 rounded tracking-widest uppercase mb-3">
            Recurso Premium (PRO / Enterprise)
          </span>
          <h4 className="text-white font-sans font-bold text-lg">Módulo LinkedIn ATS Bloqueado</h4>
          <p className="text-xs text-slate-400 max-w-sm mt-1 leading-relaxed">
            A análise profunda de LinkedIn e a geração de Headlines/About Me de impacto estão restritas aos usuários pagantes da plataforma Sentinel OS. Atualize seu plano para liberar este módulo.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Input area */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
            <h3 className="text-md font-sans font-bold text-white mb-4 flex items-center gap-2">
              <Linkedin className="h-5 w-5 text-cyan-400" />
              Seu Perfil do LinkedIn
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-1.5">URL do Perfil</label>
                <div className="relative">
                  <Linkedin className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                  <input
                    type="url"
                    value={linkedinUrl}
                    onChange={(e) => setLinkedinUrl(e.target.value)}
                    placeholder="Cole o link do seu perfil do LinkedIn aqui..."
                    autoComplete="url"
                    inputMode="url"
                    disabled={disableInputs}
                    className={`w-full rounded-lg pl-9 pr-4 py-2 text-xs focus:outline-none ${
                      disableInputs
                        ? "bg-slate-900 border border-slate-800 text-slate-500 placeholder-slate-600"
                        : linkedinUrlStatus === "unrecognized"
                        ? "bg-slate-950 border border-rose-500/60 focus:border-rose-500 text-white placeholder-slate-600"
                        : "bg-slate-950 border border-slate-800 focus:border-cyan-500 text-white placeholder-slate-600"
                    }`}
                  />
                </div>
                {!disableInputs && linkedinUrlStatus === "recognized" && (
                  <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-emerald-400">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    Link do LinkedIn reconhecido{linkedinHandle ? `: /in/${linkedinHandle}` : ""}
                  </p>
                )}
                {!disableInputs && linkedinUrlStatus === "unrecognized" && (
                  <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-rose-400">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Não reconhecemos esse link. Use o formato linkedin.com/in/seu-usuario
                  </p>
                )}
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="block text-xs font-mono text-slate-400 uppercase">
                    Conteúdo do Perfil (Sobre / Bio atual)
                  </label>
                </div>
                <textarea
                  value={linkedinText}
                  onChange={(e) => setLinkedinText(e.target.value)}
                  placeholder="Cole aqui seu atual Título, Bio ou seção 'Sobre' do LinkedIn para que nossa IA possa analisar o posicionamento técnico..."
                  rows={10}
                  disabled={disableInputs}
                  className={`w-full rounded-lg p-3 text-xs font-sans resize-y focus:outline-none ${
                    disableInputs
                      ? "bg-slate-900 border border-slate-800 text-slate-500 placeholder-slate-600"
                      : "bg-slate-950 border border-slate-800 focus:border-cyan-500 text-slate-300 placeholder-slate-600"
                  }`}
                />
              </div>

              <button
                onClick={onOptimize}
                disabled={disableInputs || isOptimizing || !linkedinText.trim() || linkedinUrlStatus === "unrecognized"}
                className={`w-full py-3 rounded-lg font-bold text-xs tracking-wider transition-all flex items-center justify-center gap-2 ${
                  disableInputs || isOptimizing || !linkedinText.trim() || linkedinUrlStatus === "unrecognized"
                    ? "bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed"
                    : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-md shadow-cyan-500/10"
                }`}
              >
                <Cpu className={`h-4 w-4 ${isOptimizing ? "animate-spin text-slate-950" : "text-slate-950"}`} />
                {isOptimizing ? "SINCRO_AI EM EXECUÇÃO..." : "OTIMIZAR MEU LINKEDIN"}
              </button>
            </div>
          </div>
        </div>

        {/* Results area */}
        <div className="lg:col-span-7">
          {(!linkedinAvailable || currentPlan === "free") && (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 h-full flex flex-col items-center justify-center text-center min-h-[350px]">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-full text-rose-500 mb-4">
                <ShieldOff className="h-8 w-8" />
              </div>
              <h4 className="text-white font-sans font-semibold text-md">Integração LinkedIn não configurada</h4>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Nenhuma análise é executada sem credenciais válidas. Configure o backend com os tokens oficiais para liberar esta área. Enquanto isso, nenhum texto simulado será exibido.
              </p>
            </div>
          )}
          {!report && linkedinAvailable && currentPlan !== "free" ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 h-full flex flex-col items-center justify-center text-center min-h-[350px]">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-full text-slate-600 mb-4 animate-pulse">
                <Linkedin className="h-8 w-8" />
              </div>
              <h4 className="text-white font-sans font-semibold text-md">Aguardando Execução do Analisador de Perfil</h4>
              <p className="text-xs text-slate-400 max-w-sm mt-1">
                Coloque suas informações textuais de perfil ao lado e escanear. A IA irá reconfigurar seu posicionamento para maximizar visualizações de recrutadores.
              </p>
            </div>
          ) : null}
          {report && linkedinAvailable && currentPlan !== "free" ? (
            <div className="space-y-6">
              {/* Profile strength and headline */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-800 pb-4 mb-4">
                  <div>
                    <h4 className="font-sans font-bold text-white text-md">Análise de Posicionamento de Marca</h4>
                    <p className="text-xs text-slate-400">Medição de visibilidade de algoritmo e palavras-chave-chave de impacto.</p>
                  </div>
                  <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-400">FORÇA DO PERFIL</span>
                    <span className={`text-sm font-mono font-bold ${
                      report.score >= 80 ? "text-emerald-400" : report.score >= 60 ? "text-amber-400" : "text-rose-400"
                    }`}>
                      {report.score}/100
                    </span>
                  </div>
                </div>

                {/* Headline Section */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">Título de Impacto Sugerido (Headline)</span>
                    <button
                      onClick={() => handleCopy(report.headline, "headline")}
                      className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                    >
                      {copiedSection === "headline" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copiado!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          <span>Copiar Título</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800/80 text-xs font-mono text-cyan-400">
                    {report.headline}
                  </div>
                </div>
              </div>

              {/* About Me Section */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
                <div className="flex justify-between items-center mb-3">
                  <h4 className="text-xs font-mono text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="h-4 w-4" />
                    Seção "Sobre" Otimizada (About Me)
                  </h4>
                  <button
                    onClick={() => handleCopy(report.aboutMe, "aboutme")}
                    className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                  >
                    {copiedSection === "aboutme" ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copiado!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" />
                        <span>Copiar Sobre</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans italic">
                  {report.aboutMe}
                </div>
              </div>

              {/* Recommendations list */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
                <h4 className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-3">
                  Recomendações Técnicas de Perfil
                </h4>
                <div className="space-y-2.5 text-xs text-slate-300">
                  {report.recommendations.map((rec, i) => (
                    <div key={i} className="flex items-center gap-2 bg-slate-950/40 px-3 py-2.5 rounded-lg border border-slate-800/60">
                      <ChevronRight className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                      <span>{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
