import React, { useState, useEffect, useCallback } from "react";
import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Briefcase, FileText, Linkedin, FolderGit2, Cpu, Sparkles, ChevronRight, AlertTriangle, ExternalLink } from "lucide-react";
import Header from "./components/Header";
import PlanSelector from "./components/PlanSelector";
import ResumeATS from "./components/ResumeATS";
import LinkedInATS from "./components/LinkedInATS";
import JobSearch from "./components/JobSearch";
import AutoApplyPipeline from "./components/AutoApplyPipeline";
import DashboardATS from "./components/DashboardATS";
import { Job, OptimizationReport, LinkedInAnalysis, Application, PlanType, LogEntry } from "./types";
import LoginPage from "./components/LoginPage";
import { apiFetch } from "./lib/apiClient";

const sentinelBanner = "/static/images/SentinelAI.png";

const normalizePlanFromServer = (value: unknown): PlanType | null => {
  if (typeof value !== "string") return null;
  const upper = value.toUpperCase();
  if (upper === "FREE") return "free";
  if (upper === "PRO" || upper === "PREMIUM") return "pro";
  if (upper === "ENTERPRISE" || upper === "MASTER" || upper === "ADMIN") return "enterprise";
  return null;
};

function DashboardApp() {
  // --- Persistent State Hooks ---
  const [currentPlan, setPlanState] = useState<PlanType>(() => {
    const saved = localStorage.getItem("sentinel_plan");
    return (saved as PlanType) || "free";
  });

  const [resumeText, setResumeText] = useState(() => {
    return localStorage.getItem("sentinel_resume") || "";
  });

  const [targetRole, setTargetRole] = useState(() => {
    return localStorage.getItem("sentinel_target_role") || "Analista de Cibersegurança";
  });

  const [cvReport, setCvReport] = useState<OptimizationReport | null>(() => {
    const saved = localStorage.getItem("sentinel_cv_report");
    return saved ? JSON.parse(saved) : null;
  });

  const [linkedinText, setLinkedinText] = useState(() => {
    return localStorage.getItem("sentinel_linkedin") || "";
  });

  const [linkedinUrl, setLinkedinUrl] = useState(() => {
    return localStorage.getItem("sentinel_linkedin_url") || "";
  });

  const [linkedinReport, setLinkedinReport] = useState<LinkedInAnalysis | null>(() => {
    const saved = localStorage.getItem("sentinel_linkedin_report");
    return saved ? JSON.parse(saved) : null;
  });

  const [jobs, setJobs] = useState<Job[]>(() => {
    const saved = localStorage.getItem("sentinel_jobs");
    return saved ? JSON.parse(saved) : [];
  });

  const [applications, setApplications] = useState<Application[]>(() => {
    const saved = localStorage.getItem("sentinel_apps");
    if (saved) return JSON.parse(saved);
    
    // Seed initial applications to make the Kanban feel live and premium right away
    return [
      {
        id: "app-seed-1",
        jobId: "job-sentinel-1",
        jobTitle: "Analista de Cibersegurança Jr/Pl (Sentinel OS)",
        company: "Sentinel IA",
        location: "Remoto",
        status: "interview",
        appliedAt: "08/07/2026",
        atsScore: 94,
        notes: "Entrevista técnica marcada para o dia 12/07/2026 às 14:00."
      },
      {
        id: "app-seed-2",
        jobId: "job-2",
        jobTitle: "Cloud Engineer Security Specialist",
        company: "CyberGuard Solutions",
        location: "Híbrido",
        status: "applied",
        appliedAt: "07/07/2026",
        atsScore: 81
      }
    ];
  });

  const [logs, setLogs] = useState<LogEntry[]>(() => {
    const saved = localStorage.getItem("sentinel_logs");
    if (saved) return JSON.parse(saved);

    return [
      {
        id: "log-1",
        timestamp: "17:18:10",
        type: "info",
        message: "Inicializando plataforma Sentinel Career v2.5."
      },
      {
        id: "log-2",
        timestamp: "17:18:11",
        type: "success",
        message: "Conectado perfeitamente com a plataforma sentinel-os.ia.br."
      }
    ];
  });

  const [autoAppliesUsed, setAutoAppliesUsed] = useState(() => {
    const saved = localStorage.getItem("sentinel_applies_used");
    return saved ? parseInt(saved, 10) : 0;
  });

  const [autoApplyLimit, setAutoApplyLimit] = useState<number | null>(null);
  const [autoApplyRemaining, setAutoApplyRemaining] = useState<number | null>(null);

  const applyAutoApplyStatus = useCallback((status: any) => {
    if (!status || typeof status !== "object") {
      return;
    }

    if ("plan" in status) {
      const mapped = normalizePlanFromServer(status.plan);
      if (mapped) {
        setPlanState((prev) => (prev === mapped ? prev : mapped));
      }
    }

    if ("limit" in status) {
      const limitValue = status.limit;
      if (typeof limitValue === "number") {
        setAutoApplyLimit(limitValue);
      } else if (limitValue === null) {
        setAutoApplyLimit(null);
      }
    }

    if ("remaining" in status) {
      const remainingValue = status.remaining;
      if (typeof remainingValue === "number") {
        setAutoApplyRemaining(remainingValue);
      } else if (remainingValue === null) {
        setAutoApplyRemaining(null);
      }
    }

    if ("used" in status && typeof status.used === "number") {
      setAutoAppliesUsed(status.used);
    }
  }, []);

  const syncSession = useCallback(async () => {
    try {
      const response = await apiFetch("/api/auth/session");
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      const planFromServer = normalizePlanFromServer(data?.frontendPlan ?? data?.plan);
      if (planFromServer) {
        setPlanState((prev) => (prev === planFromServer ? prev : planFromServer));
      }
      if (data?.autoApply) {
        applyAutoApplyStatus({
          plan: data.plan ?? data.frontendPlan,
          limit: data.autoApply.limit,
          remaining: data.autoApply.remaining,
          used: data.autoApply.used,
        });
      }
    } catch (err) {
      console.error("[Sentinel Career] Falha ao sincronizar sessão", err);
    }
  }, [applyAutoApplyStatus]);

  // --- Session Status & Navigation State ---
  const [activeTab, setActiveTab] = useState<"dashboard" | "resume" | "linkedin" | "jobs">("dashboard");
  const [geminiConfigured, setGeminiConfigured] = useState(false);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isApplying, setIsApplying] = useState(false);

  // --- Loading / Processing States ---
  const [isOptimizingCV, setIsOptimizingCV] = useState(false);
  const [isOptimizingLinkedIn, setIsOptimizingLinkedIn] = useState(false);
  const [isSearchingJobs, setIsSearchingJobs] = useState(false);

  // --- Sync storage ---
  useEffect(() => {
    localStorage.setItem("sentinel_plan", currentPlan);
  }, [currentPlan]);

  useEffect(() => {
    localStorage.setItem("sentinel_resume", resumeText);
  }, [resumeText]);

  useEffect(() => {
    localStorage.setItem("sentinel_target_role", targetRole);
  }, [targetRole]);

  useEffect(() => {
    localStorage.setItem("sentinel_cv_report", cvReport ? JSON.stringify(cvReport) : "");
  }, [cvReport]);

  useEffect(() => {
    localStorage.setItem("sentinel_linkedin", linkedinText);
  }, [linkedinText]);

  useEffect(() => {
    localStorage.setItem("sentinel_linkedin_url", linkedinUrl);
  }, [linkedinUrl]);

  useEffect(() => {
    localStorage.setItem("sentinel_linkedin_report", linkedinReport ? JSON.stringify(linkedinReport) : "");
  }, [linkedinReport]);

  useEffect(() => {
    localStorage.setItem("sentinel_jobs", JSON.stringify(jobs));
  }, [jobs]);

  useEffect(() => {
    localStorage.setItem("sentinel_apps", JSON.stringify(applications));
  }, [applications]);

  useEffect(() => {
    localStorage.setItem("sentinel_logs", JSON.stringify(logs));
  }, [logs]);

  useEffect(() => {
    localStorage.setItem("sentinel_applies_used", autoAppliesUsed.toString());
  }, [autoAppliesUsed]);

  useEffect(() => {
    syncSession();
  }, [syncSession]);

  // Check Gemini Status
  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await apiFetch("/api/gemini/status");
        const data = await response.json();
        setGeminiConfigured(data.configured);
      } catch (err) {
        setGeminiConfigured(false);
      }
    };
    checkStatus();
  }, []);

  // --- Logging Helper ---
  const addLog = (type: LogEntry["type"], message: string) => {
    const time = new Date().toLocaleTimeString("pt-BR", { hour12: false });
    const newLog: LogEntry = {
      id: "log-" + Math.random().toString(36).substring(2, 9),
      timestamp: time,
      type,
      message,
    };
    setLogs((prev) => [newLog, ...prev]);
  };

  const setPlan = (plan: PlanType) => {
    setPlanState(plan);
    addLog("info", `Plano de acesso alterado para: ${plan.toUpperCase()}`);
  };

  // --- Core API Actions ---

  // 1. Optimize Resume (CV)
  const handleOptimizeCV = async () => {
    if (!resumeText.trim() || !targetRole.trim()) return;
    setIsOptimizingCV(true);
    addLog("info", `Iniciando análise profunda de currículo para vaga de: ${targetRole}`);

    try {
      const response = await apiFetch("/api/gemini/optimize-cv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resumeText, targetRole }),
      });
      const data: OptimizationReport = await response.json();
      setCvReport(data);
      addLog("success", `Relatório ATS completo para "${targetRole}". Score calculado: ${data.score}%`);
    } catch (err) {
      addLog("error", "Erro ao escanear currículo no servidor. Usando dados resilientes.");
    } finally {
      setIsOptimizingCV(false);
    }
  };

  // 2. Optimize LinkedIn
  const handleOptimizeLinkedIn = async () => {
    if (currentPlan === "free") {
      const message = "Atualize para o plano Pro para desbloquear a otimização de LinkedIn.";
      addLog("warn", message);
      alert(message);
      return;
    }
    if (!linkedinText.trim() || !targetRole.trim()) return;
    setIsOptimizingLinkedIn(true);
    addLog("info", "Iniciando otimizador de visibilidade de perfil do LinkedIn");

    try {
      const sanitizedUrl = linkedinUrl.trim();
      const response = await apiFetch("/api/gemini/analyze-linkedin", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          linkedinText,
          targetRole,
          ...(sanitizedUrl ? { linkedinUrl: sanitizedUrl } : {}),
        }),
      });
      const data: LinkedInAnalysis = await response.json();
      setLinkedinReport(data);
      addLog("success", `Otimização de LinkedIn concluída com sucesso. Força do perfil: ${data.score}/100.`);
    } catch (err) {
      addLog("error", "Falha de conexão com a análise de LinkedIn do servidor.");
    } finally {
      setIsOptimizingLinkedIn(false);
    }
  };

  // 3. Search and Score Jobs
  const handleSearchJobs = async () => {
    if (!targetRole.trim()) return;
    setIsSearchingJobs(true);
    addLog("info", `Buscador de vagas varrendo ecossistemas parceiros por: "${targetRole}"`);

    try {
      const response = await apiFetch("/api/gemini/search-jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ targetRole, resumeText }),
      });
      const data: Job[] = await response.json();
      setJobs(data);
      addLog("success", `Varredura de IA concluída. ${data.length} vagas catalogadas e classificadas com compatibilidade ATS.`);
    } catch (err) {
      addLog("error", "Erro ao resgatar vagas do servidor.");
    } finally {
      setIsSearchingJobs(false);
    }
  };

  // 4. Trigger apply overlay
  const handleInitiateApply = async (job: Job) => {
    if (job.applicationType === "auto") {
      if (autoApplyLimit !== null && autoApplyRemaining !== null && autoApplyRemaining <= 0) {
        const limitMessage = "Limite de Auto-Apply atingido para o plano atual. Considere fazer upgrade.";
        addLog("warn", limitMessage);
        alert(limitMessage);
        return;
      }

      try {
        const response = await apiFetch("/api/gemini/auto-apply/validate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jobId: job.id,
            jobTitle: job.title,
            applicationType: job.applicationType,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const detail = errorData.detail || "Não foi possível validar seu limite de Auto-Apply.";
          addLog("warn", detail);
          alert(detail);
          return;
        }

        const status = await response.json();
        applyAutoApplyStatus(status);

        if (typeof status.remaining === "number" && status.remaining <= 0) {
          const remainingMessage = "Sem saldo de Auto-Apply disponível. Faça upgrade para continuar usando automações.";
          addLog("warn", remainingMessage);
          alert(remainingMessage);
          return;
        }

        if (typeof status.remaining === "number") {
          addLog("info", `Validação aprovada. Auto-Apply restante: ${status.remaining}.`);
        }
      } catch (err) {
        console.error("[Sentinel Career] Falha ao validar auto-apply", err);
        const genericMessage = "Erro ao validar limite de Auto-Apply. Tente novamente em instantes.";
        addLog("error", genericMessage);
        alert(genericMessage);
        return;
      }
    }

    setSelectedJob(job);
    setIsApplying(true);
  };

  // 5. Complete application submission (triggers from overlay)
  const handleCompleteApply = async (coverLetterUsed: string) => {
    if (!selectedJob) return;

    let registerStatus: any = null;
    if (selectedJob.applicationType === "auto") {
      try {
        const response = await apiFetch("/api/gemini/auto-apply/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            jobId: selectedJob.id,
            jobTitle: selectedJob.title,
            applicationType: selectedJob.applicationType,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const detail = errorData.detail || "Falha ao registrar o Auto-Apply. Tente novamente.";
          addLog("error", detail);
          alert(detail);
          return;
        }

        registerStatus = await response.json();
        applyAutoApplyStatus(registerStatus);

        if (typeof registerStatus.remaining === "number") {
          addLog("info", `Auto-Apply registrado. Restantes: ${registerStatus.remaining}.`);
        }
      } catch (err) {
        console.error("[Sentinel Career] Falha ao registrar auto-apply", err);
        const genericMessage = "Erro ao confirmar a candidatura automática. Nenhum envio realizado.";
        addLog("error", genericMessage);
        alert(genericMessage);
        return;
      }
    }

    const newApp: Application = {
      id: "app-" + Math.random().toString(36).substring(2, 9),
      jobId: selectedJob.id,
      jobTitle: selectedJob.title,
      company: selectedJob.company,
      location: selectedJob.location,
      status: "applied",
      appliedAt: new Date().toLocaleDateString("pt-BR"),
      atsScore: selectedJob.matchRate,
      coverLetterGenerated: coverLetterUsed,
    };

    setApplications((prev) => [newApp, ...prev]);
    addLog(
      "success",
      `Candidatura para ${selectedJob.title} na ${selectedJob.company} gravada no Dashboard. Status: CANDIDATADO.`
    );

    if (registerStatus && registerStatus.limit === null) {
      addLog("success", "Plano com Auto-Apply ilimitado ativo.");
    }

    setIsApplying(false);
    setSelectedJob(null);
    setActiveTab("dashboard");
  };

  // --- Application management ---
  const handleUpdateStatus = (id: string, newStatus: Application["status"]) => {
    setApplications((prev) =>
      prev.map((app) => (app.id === id ? { ...app, status: newStatus } : app))
    );
    const target = applications.find((a) => a.id === id);
    if (target) {
      addLog("info", `Status alterado para [${newStatus.toUpperCase()}] em ${target.jobTitle} (${target.company}).`);
    }
  };

  const handleDeleteApplication = (id: string) => {
    const target = applications.find((a) => a.id === id);
    setApplications((prev) => prev.filter((app) => app.id !== id));
    if (target) {
      addLog("warn", `Registro de candidatura deletado: ${target.jobTitle} na ${target.company}.`);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans select-none antialiased text-slate-100">
      {/* Brand Header with active session breadcrumb */}
      <Header
        currentPlan={currentPlan}
        setPlan={setPlan}
        geminiConfigured={geminiConfigured}
        userEmail="soaresreginaldo@gmail.com"
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
        
        {/* Sentinel OS Microsoft Azure Widescreen Banner */}
        <div className="relative rounded-2xl overflow-hidden border border-blue-500/30 shadow-[0_0_30px_rgba(30,58,138,0.3)] bg-slate-950 group">
          {/* Top Status Badges */}
          <div className="absolute top-4 right-4 z-10 flex flex-wrap gap-2">
            <div className="flex items-center gap-1.5 bg-slate-950/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-blue-500/30 text-[10px] font-mono font-bold text-blue-400 uppercase tracking-widest shadow-lg">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Microsoft Azure VM: VM-SENTINEL-PROD (Active)
            </div>
            <div className="flex items-center gap-1.5 bg-slate-950/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-purple-500/30 text-[10px] font-mono font-bold text-purple-400 uppercase tracking-widest shadow-lg">
              Azure OpenAI Service
            </div>
          </div>
          
          {/* Main Banner Image Container */}
          <div className="relative h-48 sm:h-64 md:h-80 w-full overflow-hidden">
            <img
              src={sentinelBanner}
              alt="Sentinel OS AI-Native Cyber Operations Platform"
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
              referrerPolicy="no-referrer"
            />
            {/* Dark gradient overlay to blend perfectly into background */}
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent"></div>
            <div className="absolute inset-0 bg-gradient-to-r from-slate-950/60 via-transparent to-slate-950/60"></div>
          </div>

          {/* Bottom Caption & Information Panel */}
          <div className="bg-slate-900/60 border-t border-slate-800 p-4 sm:p-5 backdrop-blur-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <h1 className="text-base font-display font-bold text-white flex items-center gap-2">
                Sentinel OS Career Portal
                <span className="text-[10px] bg-blue-500/15 border border-blue-500/30 text-blue-400 font-mono px-2 py-0.5 rounded tracking-widest uppercase">
                  Azure Partner App
                </span>
              </h1>
              <p className="text-xs text-slate-400">
                Acelerador de candidaturas e otimizador de inteligência profissional operando sob infraestrutura Microsoft Cloud segura.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {/* Azure Badge Logo */}
              <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs font-mono">
                <div className="grid grid-cols-2 gap-0.5 w-4 h-4 shrink-0">
                  <div className="bg-[#f25022]"></div>
                  <div className="bg-[#7fba00]"></div>
                  <div className="bg-[#00a4ef]"></div>
                  <div className="bg-[#ffb900]"></div>
                </div>
                <div className="text-left leading-tight text-[10px]">
                  <p className="font-bold text-slate-300">Microsoft</p>
                  <p className="text-slate-500 uppercase text-[8px] tracking-wider font-mono">Azure VM Hosted</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Subpage Location Banner Context */}
        <div id="subpage-context-banner" className="bg-slate-900/40 border border-cyan-500/10 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-2 w-2 rounded-full bg-cyan-400 animate-ping"></div>
            <div className="text-xs">
              <span className="text-slate-400">Você está logado na plataforma integrada Sentinel OS.</span>{" "}
              <span className="text-slate-500 font-mono">sentinel-os.ia.br/career</span>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[10px] font-mono text-cyan-400/80 bg-cyan-950/20 px-2.5 py-1 rounded border border-cyan-500/20 uppercase tracking-widest">
            <span>SISTEMA DE GESTÃO DE TALENTOS & AUTO-ATS</span>
          </div>
        </div>

        {/* Access Plans Management (Free, Pro, Enterprise display limits) */}
        <PlanSelector
          currentPlan={currentPlan}
          setPlan={setPlan}
          autoAppliesUsed={autoAppliesUsed}
          autoApplyLimit={autoApplyLimit}
          autoApplyRemaining={autoApplyRemaining}
        />

        {/* Interactive Tabs navigation */}
        <div className="flex border-b border-slate-800">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center gap-2 py-3 px-5 border-b-2 font-display text-sm font-semibold tracking-wide transition-all ${
              activeTab === "dashboard"
                ? "border-cyan-400 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FolderGit2 className="h-4 w-4" />
            Dashboard Tracker
          </button>
          <button
            onClick={() => setActiveTab("resume")}
            className={`flex items-center gap-2 py-3 px-5 border-b-2 font-display text-sm font-semibold tracking-wide transition-all ${
              activeTab === "resume"
                ? "border-cyan-400 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <FileText className="h-4 w-4" />
            Currículo ATS
          </button>
          <button
            onClick={() => setActiveTab("linkedin")}
            className={`flex items-center gap-2 py-3 px-5 border-b-2 font-display text-sm font-semibold tracking-wide transition-all ${
              activeTab === "linkedin"
                ? "border-cyan-400 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Linkedin className="h-4 w-4" />
            LinkedIn ATS
          </button>
          <button
            onClick={() => setActiveTab("jobs")}
            className={`flex items-center gap-2 py-3 px-5 border-b-2 font-display text-sm font-semibold tracking-wide transition-all ${
              activeTab === "jobs"
                ? "border-cyan-400 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Briefcase className="h-4 w-4" />
            Buscar & Classificar Vagas
          </button>
        </div>

        {/* Tab content switcher */}
        <div className="min-h-[450px]">
          {activeTab === "dashboard" && (
            <DashboardATS
              applications={applications}
              onUpdateStatus={handleUpdateStatus}
              onDeleteApplication={handleDeleteApplication}
              logs={logs}
            />
          )}

          {activeTab === "resume" && (
            <ResumeATS
              currentPlan={currentPlan}
              resumeText={resumeText}
              setResumeText={setResumeText}
              targetRole={targetRole}
              setTargetRole={setTargetRole}
              report={cvReport}
              setReport={setCvReport}
              onOptimize={handleOptimizeCV}
              isOptimizing={isOptimizingCV}
            />
          )}

          {activeTab === "linkedin" && (
            <LinkedInATS
              currentPlan={currentPlan}
              linkedinUrl={linkedinUrl}
              setLinkedinUrl={setLinkedinUrl}
              linkedinText={linkedinText}
              setLinkedinText={setLinkedinText}
              targetRole={targetRole}
              report={linkedinReport}
              onOptimize={handleOptimizeLinkedIn}
              isOptimizing={isOptimizingLinkedIn}
            />
          )}

          {activeTab === "jobs" && (
            <JobSearch
              currentPlan={currentPlan}
              targetRole={targetRole}
              setTargetRole={setTargetRole}
              jobs={jobs}
              onSearch={handleSearchJobs}
              isSearching={isSearchingJobs}
              onInitiateApply={handleInitiateApply}
              appliedJobIds={applications.map((a) => a.jobId)}
            />
          )}
        </div>
      </main>

      {/* Auto Apply Cinematic Overlay Modal */}
      {isApplying && selectedJob && (
        <AutoApplyPipeline
          currentPlan={currentPlan}
          job={selectedJob}
          onClose={() => {
            setIsApplying(false);
            setSelectedJob(null);
          }}
          onComplete={handleCompleteApply}
          isAuto={selectedJob.applicationType === "auto"}
        />
      )}

      {/* Cyber Footer */}
      <footer className="border-t border-slate-800 bg-slate-950 py-6 mt-12 text-center text-xs text-slate-500 font-mono">
        <p>© 2026 Sentinel IA. Integrado perfeitamente com a plataforma de Cybersegurança e Atração de Talentos.</p>
        <p className="mt-1 text-slate-600 text-[10px]">Securely connected via sentinel-os.ia.br</p>
      </footer>
    </div>
  );
}

function ProtectedRoute({ children }: { children: ReactNode }): JSX.Element {
  const location = useLocation();
  const [status, setStatus] = useState<"loading" | "authenticated" | "unauthenticated">("loading");

  useEffect(() => {
    let cancelled = false;

    const verifySession = async () => {
      try {
        const response = await apiFetch("/api/auth/session", { credentials: "include" });
        if (cancelled) {
          return;
        }

        if (response.ok) {
          setStatus("authenticated");
          return;
        }

        if (response.status === 401 || response.status === 403) {
          setStatus("unauthenticated");
          return;
        }

        setStatus("unauthenticated");
      } catch (err) {
        if (!cancelled) {
          setStatus("unauthenticated");
        }
      }
    };

    verifySession();

    return () => {
      cancelled = true;
    };
  }, [location.pathname, location.search]);

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-200">
        <p className="text-sm tracking-wide text-slate-400">Validando credenciais seguras...</p>
      </div>
    );
  }

  if (status === "unauthenticated") {
    const target = `${location.pathname}${location.search || ""}${location.hash || ""}` || "/dashboard";
    const encodedTarget = encodeURIComponent(target);
    return <Navigate to={`/login?next=${encodedTarget}`} replace />;
  }

  return <>{children}</>;
}

function App(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardApp />
          </ProtectedRoute>
        }
      />
      <Route path="/dashboard/*" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default App;
