import React from "react";
import { FolderGit2, Briefcase, Calendar, CheckCircle, XCircle, ChevronRight, ChevronLeft, Trash2, ShieldCheck, Terminal } from "lucide-react";
import { Application, LogEntry } from "../types";

interface DashboardATSProps {
  applications: Application[];
  onUpdateStatus: (id: string, newStatus: Application["status"]) => void;
  onDeleteApplication: (id: string) => void;
  logs: LogEntry[];
}

export default function DashboardATS({
  applications,
  onUpdateStatus,
  onDeleteApplication,
  logs,
}: DashboardATSProps) {
  // Aggregate stats
  const totalApplications = applications.length;
  const appliedCount = applications.filter((a) => a.status === "applied").length;
  const interviewCount = applications.filter((a) => a.status === "interview" || a.status === "test").length;
  const offeredCount = applications.filter((a) => a.status === "offered").length;
  const rejectedCount = applications.filter((a) => a.status === "rejected").length;

  const columns: { id: Application["status"]; name: string; color: string; bg: string; border: string }[] = [
    { id: "applied", name: "Candidatado", color: "text-cyan-400", bg: "bg-cyan-950/10", border: "border-cyan-500/20" },
    { id: "test", name: "Teste Técnico", color: "text-purple-400", bg: "bg-purple-950/10", border: "border-purple-500/20" },
    { id: "interview", name: "Entrevistando", color: "text-amber-400", bg: "bg-amber-950/10", border: "border-amber-500/20" },
    { id: "offered", name: "Oferecido", color: "text-emerald-400", bg: "bg-emerald-950/15", border: "border-emerald-500/35" },
    { id: "rejected", name: "Recusado", color: "text-rose-400", bg: "bg-rose-950/10", border: "border-rose-500/20" }
  ];

  const handleMove = (id: string, current: Application["status"], direction: "left" | "right") => {
    const sequence: Application["status"][] = ["applied", "test", "interview", "offered", "rejected"];
    const currentIndex = sequence.indexOf(current);
    if (direction === "left" && currentIndex > 0) {
      onUpdateStatus(id, sequence[currentIndex - 1]);
    } else if (direction === "right" && currentIndex < sequence.length - 1) {
      onUpdateStatus(id, sequence[currentIndex + 1]);
    }
  };

  return (
    <div id="dashboard-panel" className="space-y-6">
      {/* Stats Counter Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex justify-between items-start text-slate-400">
            <span className="text-[10px] font-mono uppercase tracking-wider">Total de Envios</span>
            <Briefcase className="h-4 w-4 text-cyan-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-white mt-1.5">{totalApplications}</p>
          <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Registros de Carreira</span>
        </div>

        {/* Metric 2 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex justify-between items-start text-slate-400">
            <span className="text-[10px] font-mono uppercase tracking-wider">Candidaturas Ativas</span>
            <CheckCircle className="h-4 w-4 text-purple-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-white mt-1.5">{appliedCount}</p>
          <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Aguardando Retorno</span>
        </div>

        {/* Metric 3 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex justify-between items-start text-slate-400">
            <span className="text-[10px] font-mono uppercase tracking-wider">Fases de Entrevista</span>
            <Calendar className="h-4 w-4 text-amber-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-white mt-1.5">{interviewCount}</p>
          <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Sincronia Agendada</span>
        </div>

        {/* Metric 4 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur-sm">
          <div className="flex justify-between items-start text-slate-400">
            <span className="text-[10px] font-mono uppercase tracking-wider">Ofertas Recebidas</span>
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-mono font-bold text-white mt-1.5">{offeredCount}</p>
          <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest">Alta Conversão IA</span>
        </div>
      </div>

      {/* Kanban Board Container */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
        <h3 className="text-md font-sans font-bold text-white mb-4 flex items-center gap-2">
          <FolderGit2 className="h-5 w-5 text-cyan-400" />
          Painel ATS Kanban (Mapeamento em Tempo Real)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 overflow-x-auto pb-4">
          {columns.map((col) => {
            const colApps = applications.filter((a) => a.status === col.id);
            return (
              <div
                key={col.id}
                className={`rounded-xl border ${col.border} ${col.bg} p-3 min-h-[350px] flex flex-col`}
              >
                {/* Column title */}
                <div className="flex justify-between items-center pb-2.5 border-b border-slate-800 mb-3 shrink-0">
                  <span className={`text-xs font-mono font-extrabold uppercase ${col.color}`}>
                    {col.name}
                  </span>
                  <span className="bg-slate-950 border border-slate-800 font-mono text-[10px] text-slate-300 px-2 py-0.5 rounded-full">
                    {colApps.length}
                  </span>
                </div>

                {/* Column Items */}
                <div className="space-y-3.5 flex-1 overflow-y-auto max-h-[400px] pr-1">
                  {colApps.length === 0 ? (
                    <div className="h-full border border-dashed border-slate-800/40 rounded-lg flex items-center justify-center p-4 text-center text-slate-600 text-[10px] font-mono italic">
                      Nenhum envio
                    </div>
                  ) : (
                    colApps.map((app) => (
                      <div
                        key={app.id}
                        className="bg-slate-950 border border-slate-850 hover:border-slate-700 rounded-lg p-3 relative flex flex-col gap-2 shadow transition-all group"
                      >
                        {/* Title and company */}
                        <div>
                          <h5 className="font-sans font-bold text-xs text-white line-clamp-1 leading-tight">
                            {app.jobTitle}
                          </h5>
                          <span className="text-[9px] font-mono text-cyan-400 uppercase tracking-wider block mt-0.5">
                            {app.company}
                          </span>
                        </div>

                        {/* Metadata details */}
                        <div className="flex justify-between items-center text-[9px] font-mono text-slate-500 border-t border-slate-900 pt-2">
                          <span>SCORE ATS: <strong className="text-slate-300">{app.atsScore}%</strong></span>
                          <span>{app.appliedAt}</span>
                        </div>

                        {/* Kanban action controllers (arrow movers) */}
                        <div className="flex justify-between items-center border-t border-slate-900 pt-2 mt-1">
                          <div className="flex gap-1.5">
                            <button
                              onClick={() => handleMove(app.id, app.status, "left")}
                              disabled={col.id === "applied"}
                              className="p-1 bg-slate-900 border border-slate-800 hover:border-slate-600 rounded disabled:opacity-35 disabled:hover:border-slate-800 text-slate-400 transition-colors"
                              title="Recuar etapa"
                            >
                              <ChevronLeft className="h-3 w-3" />
                            </button>
                            <button
                              onClick={() => handleMove(app.id, app.status, "right")}
                              disabled={col.id === "rejected"}
                              className="p-1 bg-slate-900 border border-slate-800 hover:border-slate-600 rounded disabled:opacity-35 disabled:hover:border-slate-800 text-slate-400 transition-colors"
                              title="Avançar etapa"
                            >
                              <ChevronRight className="h-3 w-3" />
                            </button>
                          </div>

                          <button
                            onClick={() => onDeleteApplication(app.id)}
                            className="p-1 bg-slate-900 border border-slate-800 hover:border-rose-900/60 hover:bg-rose-950/20 text-slate-500 hover:text-rose-400 rounded transition-all"
                            title="Deletar registro"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Background AI Logs console */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm font-mono text-xs text-slate-400">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3.5">
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-mono text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
              <Terminal className="h-4 w-4" />
              Sentinel AI Agent - Logs de Atividade de Carreira
            </h4>
            <span className="text-[9px] bg-blue-950/40 border border-blue-500/35 text-blue-400 px-1.5 py-0.5 rounded uppercase font-bold tracking-widest hidden sm:inline-block">
              Azure VM Active
            </span>
          </div>
          <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" title="Agente Sentinel em monitoramento contínuo"></span>
        </div>

        <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
          {logs.map((log) => (
            <div key={log.id} className="flex items-start gap-2 leading-relaxed text-[11px]">
              <span className="text-slate-600 shrink-0 select-none">[{log.timestamp}]</span>
              <span className={`font-bold shrink-0 select-none ${
                log.type === "success"
                  ? "text-emerald-400"
                  : log.type === "warn"
                  ? "text-amber-400"
                  : log.type === "error"
                  ? "text-rose-400"
                  : "text-cyan-400/80"
              }`}>
                [{log.type.toUpperCase()}]
              </span>
              <span className="text-slate-300">{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
