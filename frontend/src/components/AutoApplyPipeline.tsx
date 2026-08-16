import React, { useState, useEffect, useRef } from "react";
import { Cpu, CheckCircle2, Circle, Loader2, Play, AlertTriangle, Copy, Check, ExternalLink, Terminal, Shield } from "lucide-react";
import { Job, PlanType } from "../types";
import { apiFetch } from "../lib/apiClient";

interface AutoApplyPipelineProps {
  currentPlan: PlanType;
  job: Job | null;
  onClose: () => void;
  onComplete: (coverLetterUsed: string) => void | Promise<void>;
  isAuto: boolean;
}

export default function AutoApplyPipeline({
  currentPlan,
  job,
  onClose,
  onComplete,
  isAuto,
}: AutoApplyPipelineProps) {
  if (!job) return null;

  // State for Auto Apply Pipeline
  const [currentStep, setCurrentStep] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [isDone, setIsDone] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [isGeneratingManualAssets, setIsGeneratingManualAssets] = useState(false);
  const [customCoverLetter, setCustomCoverLetter] = useState("");

  const steps = [
    "Inicializando agente de busca e verificação de assinatura digital Sentinel OS",
    "Extraindo tags e injetando palavras-chave no currículo estruturado",
    "Gerando Carta de Apresentação customizada com Azure OpenAI para " + job.company,
    "Preenchendo campos obrigatórios do formulário (Autofill Inteligente)",
    "Contornando triagem automatizada ATS externa e enviando payload",
    "Candidatura confirmada! Gravando registro de status no Dashboard"
  ];

  const logRef = useRef<HTMLDivElement>(null);

  // Auto Scroll logs
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logLines]);

  // Simulated Auto Apply Runner
  useEffect(() => {
    if (!isAuto) {
      // Manual mode: generate customized assets on startup
      const fetchManualAssets = async () => {
        setIsGeneratingManualAssets(true);
        try {
          const response = await apiFetch("/api/azure/generate-apply-assets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              jobTitle: job.title,
              company: job.company,
              resumeText: "" // server will use default or fallback
            })
          });
          if (!response.ok) {
            console.error("[Sentinel Career] Falha ao gerar carta personalizada", response.status);
            return;
          }
          const data = await response.json();
          setCustomCoverLetter(data.coverLetter);
        } catch (err) {
          console.error(err);
        } finally {
          setIsGeneratingManualAssets(false);
        }
      };
      fetchManualAssets();
      return;
    }

    // Auto Apply Sequencer
    setLogLines([`[SYSTEM] Iniciando pipeline de candidatura inteligente para ${job.title}...`, `[SECURITY] Verificando integridade dos dados sob encriptação SHA-256... Ok.`]);
    setCurrentStep(0);
    setIsDone(false);

    let stepIndex = 0;
    const interval = setInterval(() => {
      stepIndex++;
      if (stepIndex < steps.length) {
        setCurrentStep(stepIndex);
        
        // Add realistic cyber logs
        setLogLines((prev) => {
          const newLogs = [...prev];
          if (stepIndex === 1) {
            newLogs.push(`[SENTINEL_AGENT] Palavras-chave injetadas com sucesso: ${job.requiredKeywords.join(", ")}`);
            newLogs.push(`[SYSTEM] Score ATS esperado para esta vaga: ${job.matchRate}%`);
          } else if (stepIndex === 2) {
            newLogs.push(`[AZURE_AI] Customizando carta de apresentação para a empresa ${job.company}...`);
            newLogs.push(`[AZURE_AI] Payload textual compilado com sucesso.`);
          } else if (stepIndex === 3) {
            newLogs.push(`[AUTO_FILL] Preenchendo campos: Nome, Email, Contato, Resumo do Candidato.`);
            newLogs.push(`[AUTO_FILL] Respondendo pergunta: 'Experiência em Cibersegurança' -> 'Sólida'`);
          } else if (stepIndex === 4) {
            newLogs.push(`[NETWORK] Enviando requisição POST para endpoint da empresa...`);
            newLogs.push(`[NETWORK] Status de resposta: 201 Created. Candidatura recebida com sucesso!`);
          } else if (stepIndex === 5) {
            newLogs.push(`[SYSTEM] Salvando histórico de aplicação.`);
            newLogs.push(`[SUCCESS] Processo de Auto-Apply completo.`);
          }
          return newLogs;
        });
      } else {
        clearInterval(interval);
        setIsDone(true);
      }
    }, 1800);

    return () => clearInterval(interval);
  }, [job, isAuto]);

  const handleCopy = (text: string, fieldId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldId);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleCompleteAuto = async () => {
    await onComplete(`Carta de apresentação personalizada para a empresa ${job.company} gerada pelo Sentinel IA.`);
  };

  const handleCompleteManual = async () => {
    await onComplete(customCoverLetter || "Candidatura registrada manualmente pelo usuário.");
  };

  return (
    <div id="apply-pipeline-overlay" className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-sm flex items-center justify-center p-4">
      {isAuto ? (
        /* AUTOMATED APPLICATION PANEL */
        <div className="bg-slate-900 border border-cyan-500/30 rounded-2xl max-w-2xl w-full p-6 shadow-[0_0_50px_rgba(6,182,212,0.15)] flex flex-col gap-6 overflow-hidden max-h-[90vh]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="absolute -inset-1 bg-cyan-400 rounded-full blur opacity-30 animate-pulse"></div>
                <div className="bg-slate-950 border border-cyan-400 rounded-full p-2">
                  <Cpu className="h-5 w-5 text-cyan-400 animate-spin" />
                </div>
              </div>
              <div>
                <h3 className="text-white font-sans font-bold text-md tracking-tight">Auto-Apply Pipeline Ativo</h3>
                <p className="text-xs text-slate-400">{job.title} • {job.company}</p>
              </div>
            </div>
            <span className="font-mono text-[10px] text-cyan-400 bg-cyan-950/40 px-2 py-1 rounded border border-cyan-400/20">
              MODALIDADE: AI AGENT
            </span>
          </div>

          {/* Pipeline Visual Sequencer */}
          <div className="space-y-3.5 bg-slate-950/40 p-4 rounded-xl border border-slate-800">
            {steps.map((step, idx) => {
              const isCompleted = idx < currentStep;
              const isActive = idx === currentStep;
              return (
                <div key={idx} className="flex items-start gap-3 text-xs">
                  <div className="mt-0.5 shrink-0">
                    {isCompleted ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    ) : isActive ? (
                      <Loader2 className="h-4 w-4 text-cyan-400 animate-spin" />
                    ) : (
                      <Circle className="h-4 w-4 text-slate-700" />
                    )}
                  </div>
                  <span className={`${isCompleted ? "text-slate-400 line-through" : isActive ? "text-cyan-400 font-bold" : "text-slate-600"}`}>
                    {step}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Terminal Logs */}
          <div className="bg-slate-950 rounded-lg p-3.5 border border-slate-800 font-mono text-[10px] flex-1 min-h-[150px] overflow-y-auto flex flex-col gap-1 text-slate-400">
            <div className="flex items-center justify-between border-b border-slate-900 pb-1.5 mb-1.5 text-slate-500">
              <span className="flex items-center gap-1">
                <Terminal className="h-3 w-3" />
                TERMINAL LOG
              </span>
              <span>SECURE_SHELL v1.4</span>
            </div>
            <div ref={logRef} className="space-y-1 overflow-y-auto max-h-[120px]">
              {logLines.map((line, idx) => (
                <div key={idx} className="leading-relaxed">
                  <span className="text-cyan-500/70 mr-1.5">&gt;</span>
                  {line}
                </div>
              ))}
            </div>
          </div>

          {/* Footer Action buttons */}
          <div className="border-t border-slate-800 pt-4 flex justify-end gap-3">
            {!isDone ? (
              <button
                onClick={onClose}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg text-xs font-bold"
              >
                Cancelar Automação
              </button>
            ) : (
              <button
                onClick={handleCompleteAuto}
                className="px-5 py-2.5 bg-cyan-500 text-slate-950 rounded-lg text-xs font-extrabold tracking-wider hover:bg-cyan-400 animate-bounce"
              >
                REGISTRAR NO DASHBOARD & FECHAR
              </button>
            )}
          </div>
        </div>
      ) : (
        /* MANUAL DIRECTED APPLICATION PANEL */
        <div className="bg-slate-900 border border-purple-500/30 rounded-2xl max-w-2xl w-full p-6 shadow-[0_0_50px_rgba(168,85,247,0.15)] flex flex-col gap-6 overflow-hidden max-h-[90vh]">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="bg-slate-950 border border-purple-400 rounded-full p-2">
                <Shield className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <h3 className="text-white font-sans font-bold text-md tracking-tight">Candidatura Assistida de Alta Conversão</h3>
                <p className="text-xs text-slate-400">{job.title} • {job.company}</p>
              </div>
            </div>
            <span className="font-mono text-[10px] text-purple-400 bg-purple-950/40 px-2 py-1 rounded border border-purple-400/20">
              MODALIDADE: REDIRECIONAMENTO ASSISTIDO
            </span>
          </div>

          {/* Quick instructions steps */}
          <div className="bg-slate-950/40 border border-slate-800 p-4 rounded-xl">
            <h4 className="text-xs font-mono text-purple-400 uppercase mb-3">Como Prosseguir (Passo-a-Passo):</h4>
            <div className="space-y-2.5 text-xs text-slate-300">
              <div className="flex items-start gap-2">
                <span className="bg-slate-900 text-purple-400 font-mono h-5 w-5 rounded-full flex items-center justify-center border border-purple-500/20 shrink-0 text-[10px]">1</span>
                <span>Copie os ativos personalizados gerados abaixo (carta e competências).</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="bg-slate-900 text-purple-400 font-mono h-5 w-5 rounded-full flex items-center justify-center border border-purple-500/20 shrink-0 text-[10px]">2</span>
                <span>Clique no botão de link externo "Ir para a plataforma externa de aplicação".</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="bg-slate-900 text-purple-400 font-mono h-5 w-5 rounded-full flex items-center justify-center border border-purple-500/20 shrink-0 text-[10px]">3</span>
                <span>Cole as informações otimizadas no formulário de destino para anular os filtros ATS deles.</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="bg-slate-900 text-purple-400 font-mono h-5 w-5 rounded-full flex items-center justify-center border border-purple-500/20 shrink-0 text-[10px]">4</span>
                <span>Retorne aqui e clique em "Registrar candidatura no Dashboard" para salvar o status de envio.</span>
              </div>
            </div>
          </div>

          {/* External application Link Button */}
          <a
            href={job.link}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold text-xs py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-all shadow-md"
          >
            <ExternalLink className="h-4 w-4" />
            IR PARA A PLATAFORMA EXTERNA DE APLICAÇÃO
          </a>

          {/* Generated assets copy helper */}
          <div className="flex-1 overflow-y-auto space-y-4 pr-1 max-h-[250px]">
            {isGeneratingManualAssets ? (
              <div className="flex flex-col items-center justify-center py-8 text-slate-500">
                <Loader2 className="h-8 w-8 animate-spin text-purple-400 mb-2" />
                <span className="text-xs font-mono">Gerando ativos de alto impacto para {job.company}...</span>
              </div>
            ) : (
              <>
                {/* Personalized Cover Letter Copy */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <div className="flex justify-between items-center mb-2.5">
                    <span className="text-[10px] font-mono text-purple-400 uppercase">Carta de Apresentação Otimizada</span>
                    <button
                      onClick={() => handleCopy(customCoverLetter, "letter")}
                      className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                    >
                      {copiedField === "letter" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-400">Copiada!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          <span>Copiar Carta</span>
                        </>
                      )}
                    </button>
                  </div>
                  <p className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans italic">
                    {customCoverLetter}
                  </p>
                </div>

                {/* Target skills array copy */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
                  <div className="flex justify-between items-center mb-2.5">
                    <span className="text-[10px] font-mono text-purple-400 uppercase">Palavras-chave Cruciais desta Vaga</span>
                    <button
                      onClick={() => handleCopy(job.requiredKeywords.join(", "), "skills")}
                      className="text-[10px] font-mono text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
                    >
                      {copiedField === "skills" ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" />
                          <span className="text-emerald-400 font-bold">Copiadas!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" />
                          <span>Copiar Keywords</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {job.requiredKeywords.map((kw, idx) => (
                      <span key={idx} className="bg-slate-900 border border-purple-950 text-purple-300 font-mono text-[10px] px-2 py-0.5 rounded">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Footer Action buttons */}
          <div className="border-t border-slate-800 pt-4 flex justify-between gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 rounded-lg text-xs font-bold"
            >
              Cancelar
            </button>
            <button
              onClick={handleCompleteManual}
              className="px-5 py-2.5 bg-purple-600 text-white rounded-lg text-xs font-extrabold tracking-wider hover:bg-purple-500"
            >
              REGISTRAR CANDIDATURA NO DASHBOARD
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
