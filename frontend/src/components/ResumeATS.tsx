import React, { useMemo, useRef, useState } from "react";
import { FileText, Cpu, AlertCircle, CheckCircle, Copy, Check, Sparkles, ShieldOff } from "lucide-react";
import { OptimizationReport, PlanType } from "../types";
import { apiFetch } from "../lib/apiClient";

const MAX_UPLOAD_SIZE_BYTES = 2_000_000;

const cleanExtractedText = (value: string): string =>
  value
    .replace(/\r/g, "")
    .replace(/\u0000/g, "")
    .replace(/\t/g, " ")
    .replace(/\u2028|\u2029/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \u00a0]{2,}/g, " ")
    .trim();

async function requestResumeParsing(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch("/api/resume/parse", {
    method: "POST",
    body: formData,
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? (data as Record<string, unknown>).detail : null;
    const message = typeof detail === "string" && detail.trim().length > 0 ? detail : "Falha ao processar o currículo no servidor.";
    throw new Error(message);
  }

  const text = data && typeof data === "object" ? (data as Record<string, unknown>).text : null;
  if (typeof text !== "string" || !text.trim()) {
    throw new Error("Resposta inválida ao extrair o currículo.");
  }

  return cleanExtractedText(text);
}

interface ResumeATSProps {
  currentPlan: PlanType;
  resumeText: string;
  setResumeText: (text: string) => void;
  report: OptimizationReport | null;
  setReport: (report: OptimizationReport | null) => void;
  onOptimize: () => Promise<void>;
  isOptimizing: boolean;
  atsAvailable: boolean;
}

export default function ResumeATS({
  currentPlan,
  resumeText,
  setResumeText,
  report,
  setReport,
  onOptimize,
  isOptimizing,
  atsAvailable,
}: ResumeATSProps) {
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "info" | "success" | "error">("idle");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const disableInputs = useMemo(() => !atsAvailable || currentPlan === "free", [atsAvailable, currentPlan]);

  const handleCopy = (text: string, sectionId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSection(sectionId);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const resetUploadFeedback = () => {
    setUploadMessage(null);
    setUploadStatus("idle");
    setUploadedFileName(null);
  };

  const handleFileSelected = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    try {
      if (file.size > MAX_UPLOAD_SIZE_BYTES) {
        resetUploadFeedback();
        setUploadStatus("error");
        setUploadMessage("Arquivo excede 2 MB. Exporte em texto ou reduza o tamanho antes de enviar.");
        event.target.value = "";
        return;
      }

      setUploadStatus("info");
      setUploadMessage("Processando arquivo enviado com o motor ATS...");

      const extractedText = await requestResumeParsing(file);

      setResumeText(extractedText);
      setReport(null);
      setUploadedFileName(file.name);
      setUploadStatus("success");
      setUploadMessage("Currículo carregado com sucesso. Revise o texto antes de otimizar.");
    } catch (error) {
      console.error("[ResumeATS] Falha ao interpretar arquivo", error);
      resetUploadFeedback();
      setUploadStatus("error");
      const message = error instanceof Error ? error.message : "Erro ao interpretar o arquivo. Tente novamente.";
      setUploadMessage(message);
    } finally {
      event.target.value = "";
    }

  };

  const renderUploadMessage = () => {
    if (!uploadMessage) {
      return null;
    }
    const toneClass = uploadStatus === "error" ? "text-rose-400" : uploadStatus === "success" ? "text-emerald-400" : "text-slate-400";
    return <p className={`text-[10px] font-mono ${toneClass}`}>{uploadMessage}</p>;
  };

  return (
    <div id="resume-ats-panel" className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Input Side (40% width on large screens) */}
      <div className="lg:col-span-5 flex flex-col gap-5">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
          <h3 className="text-md font-sans font-bold text-white mb-4 flex items-center gap-2">
            <FileText className="h-5 w-5 text-cyan-400" />
            Currículo para Análise ATS
          </h3>

          <div className="space-y-4">
            {/* Resume Text Area */}
            <div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-1.5">
                <label className="block text-xs font-mono text-slate-400 uppercase">
                  Texto do Currículo (CV)
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.pdf,.docx,.md,.rtf"
                    className="hidden"
                    onChange={handleFileSelected}
                  />
                  <button
                    type="button"
                    onClick={handleUploadClick}
                    disabled={disableInputs}
                    className={`text-[10px] font-mono hover:underline ${disableInputs ? "text-slate-600 cursor-not-allowed" : "text-cyan-400"}`}
                  >
                    Fazer upload do currículo
                  </button>
                </div>
              </div>
              {uploadedFileName && (
                <p className="text-[10px] font-mono text-emerald-400">Arquivo importado: {uploadedFileName}</p>
              )}
              {renderUploadMessage()}
              <textarea
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                placeholder="Cole as informações textuais do seu currículo aqui para análise do sistema ATS..."
                rows={12}
                disabled={disableInputs}
                className={`w-full border rounded-lg p-3 text-xs font-mono resize-y focus:outline-none ${
                  disableInputs
                    ? "bg-slate-900 border-slate-800 text-slate-500 placeholder-slate-600"
                    : "bg-slate-950 border border-slate-800 focus:border-cyan-500 text-slate-300 placeholder-slate-600"
                }`}
              />
            </div>

            {/* Trigger Button */}
            <button
              onClick={onOptimize}
              disabled={disableInputs || isOptimizing || !resumeText.trim()}
              className={`w-full py-3 rounded-lg font-bold text-xs tracking-wider transition-all flex items-center justify-center gap-2 ${
                disableInputs || isOptimizing || !resumeText.trim()
                  ? "bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed"
                  : "bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 hover:opacity-90 shadow-md shadow-cyan-500/10"
              }`}
            >
              <Cpu className={`h-4 w-4 ${isOptimizing ? "animate-spin text-slate-950" : "text-slate-950"}`} />
              {isOptimizing ? "PROCESSANDO VIA SENTINEL AI..." : "ESCANEAR & OTIMIZAR CV"}
            </button>
          </div>
        </div>
      </div>

      {/* Output Side - ATS analysis details (70% width on large screens) */}
      <div className="lg:col-span-7">
        {(!atsAvailable || currentPlan === "free") && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 h-full flex flex-col items-center justify-center text-center min-h-[400px]">
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-full text-rose-500 mb-4">
              <ShieldOff className="h-8 w-8" />
            </div>
            <h4 className="text-white font-sans font-semibold text-md">Motor ATS indisponível</h4>
            <p className="text-xs text-slate-400 max-w-sm mt-1">
              Configure as credenciais obrigatórias no backend para liberar a análise real. Enquanto isso, nenhuma métrica será exibida e nenhuma simulação é apresentada.
            </p>
          </div>
        )}
        {!report && atsAvailable && currentPlan !== "free" && (
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 h-full flex flex-col items-center justify-center text-center min-h-[400px]">
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-full text-slate-600 mb-4 animate-pulse">
              <Cpu className="h-8 w-8" />
            </div>
            <h4 className="text-white font-sans font-semibold text-md">Aguardando Execução do Diagnóstico ATS</h4>
            <p className="text-xs text-slate-400 max-w-sm mt-1">
              Forneça seu currículo e o cargo desejado no painel ao lado e clique em escanear. A inteligência Sentinel analisará os padrões contra as melhores práticas do setor.
            </p>
          </div>
        )}
        {report && atsAvailable && currentPlan !== "free" && (
          <div className="space-y-6">
            {/* ATS Score Header Card */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl"></div>

              <div className="flex flex-col sm:flex-row items-center gap-6">
                {/* Score Circular visualization */}
                <div className="relative h-28 w-28 shrink-0">
                  {/* Outer glowing border */}
                  <div className="absolute inset-0 bg-cyan-500/10 rounded-full blur-md"></div>
                  <svg className="w-full h-full transform -rotate-90">
                    <circle
                      cx="56"
                      cy="56"
                      r="46"
                      className="stroke-slate-800"
                      strokeWidth="8"
                      fill="transparent"
                    />
                    <circle
                      cx="56"
                      cy="56"
                      r="46"
                      className="stroke-cyan-400 transition-all duration-1000 ease-out"
                      strokeWidth="8"
                      fill="transparent"
                      strokeDasharray={2 * Math.PI * 46}
                      strokeDashoffset={2 * Math.PI * 46 * (1 - report.score / 100)}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="font-mono text-3xl font-bold text-white">{report.score}%</span>
                    <span className="text-[9px] font-mono text-slate-400 uppercase tracking-widest">ATS Score</span>
                  </div>
                </div>

                {/* Score text details */}
                <div className="text-center sm:text-left">
                  <div className="flex items-center justify-center sm:justify-start gap-2">
                    <span className="font-sans font-bold text-lg text-white">Score de Compatibilidade</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                      report.score >= 80
                        ? "bg-emerald-950/30 text-emerald-400 border-emerald-500/20"
                        : report.score >= 60
                        ? "bg-amber-950/30 text-amber-400 border-amber-500/20"
                        : "bg-rose-950/30 text-rose-400 border-rose-500/20"
                    }`}>
                      {report.score >= 80 ? "Excelente" : report.score >= 60 ? "Bom" : "Fraco"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1.5 max-w-md">
                    Sua pontuação indica o grau de alinhamento sintático do seu currículo com os algoritmos de triagem mais modernos do mercado de cibersegurança e TI.
                  </p>
                </div>
              </div>
            </div>

            {/* Strengths & Missing Skills Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Strengths */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
                <h4 className="text-xs font-mono text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <CheckCircle className="h-4 w-4" />
                  Pontos Fortes Identificados
                </h4>
                <ul className="space-y-2 text-xs text-slate-300">
                  {report.strengths.map((str, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-emerald-500 mt-0.5 shrink-0">✓</span>
                      <span>{str}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Missing Skills */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
                <h4 className="text-xs font-mono text-rose-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <AlertCircle className="h-4 w-4" />
                  Gaps de Competência (Faltantes)
                </h4>
                <ul className="space-y-2 text-xs text-slate-300">
                  {report.missingSkills.map((sk, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-rose-500 mt-0.5 shrink-0">⚠</span>
                      <span>{sk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Keywords recommendation tags */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
              <h4 className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-3">
                Palavras-chave Recomendadas para Inserir (SEO de Carreira)
              </h4>
              <div className="flex flex-wrap gap-2">
                {report.keywords.map((kw, i) => (
                  <span
                    key={i}
                    className="bg-slate-950 hover:bg-slate-900 text-slate-300 border border-slate-800 text-xs px-2.5 py-1 rounded font-mono transition-colors"
                  >
                    + {kw}
                  </span>
                ))}
              </div>
            </div>

            {/* Suggestions list */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
              <h4 className="text-xs font-mono text-cyan-400 uppercase tracking-wider mb-3">
                Ações Práticas de Otimização (Passo-a-Passo)
              </h4>
              <div className="space-y-3.5 text-xs text-slate-300">
                {report.suggestions.map((sug, i) => (
                  <div key={i} className="flex items-start gap-2.5 bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                    <span className="bg-cyan-500/10 text-cyan-400 h-5 w-5 rounded-full flex items-center justify-center font-mono text-[10px] shrink-0 border border-cyan-400/20">
                      {i + 1}
                    </span>
                    <p className="leading-relaxed">{sug}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* AI-Optimized professional summary section */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-xs font-mono text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-cyan-400" />
                  Resumo Profissional Otimizado por IA
                </h4>
                <button
                  onClick={() => handleCopy(report.optimizedSummary, "summary")}
                  className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                >
                  {copiedSection === "summary" ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-400" />
                      <span className="text-emerald-400">Copiado!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span>Copiar Resumo</span>
                    </>
                  )}
                </button>
              </div>
              <p className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 text-xs text-slate-300 leading-relaxed font-sans italic">
                "{report.optimizedSummary}"
              </p>
            </div>

            {/* Cover Letter Section (Pro block / Enterprise block) */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm relative overflow-hidden">
              {currentPlan === "free" && (
                <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-[2px] z-10 flex flex-col items-center justify-center text-center p-4">
                  <span className="bg-purple-500/10 text-purple-400 border border-purple-500/30 text-[9px] font-mono px-2 py-0.5 rounded tracking-widest uppercase mb-2">
                    Recurso Premium (PRO / Enterprise)
                  </span>
                  <h5 className="text-sm font-sans font-bold text-white">Carta de Apresentação Otimizada Bloqueada</h5>
                  <p className="text-xs text-slate-400 max-w-xs mt-1">
                    Migre seu plano do Sentinel Career para acessar a carta de apresentação sob medida gerada dinamicamente pela IA para a vaga pretendida.
                  </p>
                </div>
              )}
              <div className="flex justify-between items-center mb-3">
                <h4 className="text-xs font-mono text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4" />
                  Carta de Apresentação de Alta Conversão
                </h4>
                {currentPlan !== "free" && (
                  <button
                    onClick={() => handleCopy(report.mockCoverLetter, "letter")}
                    className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                  >
                    {copiedSection === "letter" ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copiada!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" />
                        <span>Copiar Carta</span>
                      </>
                    )}
                  </button>
                )}
              </div>
              <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800/80 text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                {report.mockCoverLetter}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
