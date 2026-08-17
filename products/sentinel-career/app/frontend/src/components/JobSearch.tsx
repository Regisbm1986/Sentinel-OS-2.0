import React from "react";
import { Search, MapPin, DollarSign, RefreshCw, ExternalLink, Zap, ShieldOff } from "lucide-react";
import { Job, PlanType } from "../types";

interface JobSearchProps {
  currentPlan: PlanType;
  jobs: Job[];
  onSearch: () => Promise<void>;
  isSearching: boolean;
  onInitiateApply: (job: Job) => void | Promise<void>;
  appliedJobIds: string[];
  jobsAvailable: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export default function JobSearch({
  currentPlan,
  jobs,
  onSearch,
  isSearching,
  onInitiateApply,
  appliedJobIds,
  jobsAvailable,
  searchQuery,
  setSearchQuery,
}: JobSearchProps) {
  if (!jobsAvailable) {
    return (
      <div id="job-search-panel" className="bg-slate-900/40 border border-slate-800 rounded-xl p-10 text-center flex flex-col items-center justify-center min-h-[280px]">
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-full text-rose-500 mb-4">
          <ShieldOff className="h-8 w-8" />
        </div>
        <h4 className="text-white font-sans font-semibold text-md">Fonte de vagas não configurada</h4>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          Configure um conector oficial de vagas e credenciais legítimas no backend para habilitar a agregação. Enquanto isso, nenhuma vaga fictícia é exibida nesta seção.
        </p>
      </div>
    );
  }

  return (
    <div id="job-search-panel" className="space-y-6">
      {/* Search Header and Trigger */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
        <div className="flex flex-col sm:flex-row items-end gap-4">
          <div className="flex-1">
            <label className="block text-xs font-mono text-slate-400 uppercase mb-1.5">
              Definir Palavras-chave / Cargo de Busca de Vagas
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Defina termos reais para a busca de vagas quando a integração estiver ativa"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-lg pl-9 pr-4 py-2.5 text-xs text-white placeholder-slate-600 focus:outline-none"
              />
            </div>
          </div>
          <button
            onClick={onSearch}
            disabled={isSearching || !searchQuery.trim()}
            className={`w-full sm:w-auto px-6 py-2.5 rounded-lg font-bold text-xs tracking-wider transition-all flex items-center justify-center gap-2 shrink-0 ${
              isSearching || !searchQuery.trim()
                ? "bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed"
                : "bg-cyan-500 text-slate-950 hover:bg-cyan-400"
            }`}
          >
            <RefreshCw className={`h-4 w-4 ${isSearching ? "animate-spin" : ""}`} />
            {isSearching ? "ROSTREANDO VAGAS..." : "AGREGAR & CLASSIFICAR VAGAS"}
          </button>
        </div>
      </div>

      {/* Jobs Listing */}
      {jobs.length === 0 ? (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-10 text-center flex flex-col items-center justify-center min-h-[300px]">
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-full text-slate-600 mb-4 animate-pulse">
            <Search className="h-8 w-8" />
          </div>
          <h4 className="text-white font-sans font-semibold text-md">Nenhuma Vaga Agregada</h4>
          <p className="text-xs text-slate-400 max-w-sm mt-1">
            Aguardando execução do conector oficial ou acionamento manual via backend.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-center px-1">
            <span className="text-xs font-mono text-slate-400">
              VAGAS ENCONTRADAS: <span className="text-cyan-400 font-bold">{jobs.length}</span>
            </span>
            <span className="text-[10px] font-mono text-slate-500 italic">
              *Classificadas por inteligência artificial em tempo real
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {jobs.map((job) => {
              const isApplied = appliedJobIds.includes(job.id);
              return (
                <div
                  key={job.id}
                  className={`border rounded-xl p-5 backdrop-blur-sm transition-all relative overflow-hidden flex flex-col justify-between ${
                    isApplied
                      ? "border-emerald-500/20 bg-emerald-950/5 opacity-80"
                      : "border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60"
                  }`}
                >
                  {/* Match percentage circular or tag */}
                  <div className="absolute top-4 right-4 flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                      job.matchRate >= 85
                        ? "bg-emerald-950/30 text-emerald-400 border-emerald-500/20"
                        : job.matchRate >= 70
                        ? "bg-amber-950/30 text-amber-400 border-amber-500/20"
                        : "bg-slate-950 text-slate-400 border-slate-800"
                    }`}>
                      {job.matchRate}% Match ({job.atsVerdict})
                    </span>
                  </div>

                  <div className="space-y-4">
                    {/* Header: Title, company, location, salary */}
                    <div>
                      <h4 className="font-sans font-bold text-white text-md tracking-tight leading-tight max-w-[80%]">
                        {job.title}
                      </h4>
                      <p className="text-xs font-mono text-cyan-400 uppercase tracking-widest mt-1">
                        {job.company}
                      </p>
                      
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mt-3 text-xs text-slate-400 font-mono">
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3.5 w-3.5 text-slate-500" />
                          <span>{job.location}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <DollarSign className="h-3.5 w-3.5 text-slate-500" />
                          <span>{job.salary}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${job.applicationType === "auto" ? "bg-cyan-400" : "bg-purple-400"}`}></span>
                          <span className="capitalize">{job.applicationType === "auto" ? "Automação Disponível" : "Redirecionamento Assistido"}</span>
                        </div>
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-slate-300 leading-relaxed font-sans border-t border-slate-800/60 pt-3">
                      {job.description}
                    </p>

                    {/* Keywords & Gap Analysis */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 border-t border-slate-800/60 pt-3">
                      {/* Required keywords */}
                      <div>
                        <span className="block text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1.5">Keywords Procuradas</span>
                        <div className="flex flex-wrap gap-1.5">
                          {job.requiredKeywords.map((kw, i) => (
                            <span key={i} className="bg-slate-950 border border-slate-850 text-slate-400 text-[10px] px-2 py-0.5 rounded font-mono">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Skills Gap */}
                      <div>
                        <span className="block text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-1.5">Análise de Gaps (IA)</span>
                        <div className="flex flex-wrap gap-1.5">
                          {job.skillsGap.map((gap, i) => (
                            <span key={i} className="bg-rose-950/20 border border-rose-950/40 text-rose-300 text-[10px] px-2 py-0.5 rounded font-mono">
                              ⚠ Faltante: {gap}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions footer */}
                  <div className="border-t border-slate-800/60 pt-4 mt-4 flex items-center justify-between gap-4 flex-wrap">
                    <span className="text-[10px] font-mono text-slate-500 italic">
                      Registrada no Sentinel OS • ID {job.id}
                    </span>

                    <div className="flex items-center gap-2">
                      {isApplied ? (
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-emerald-500/20 bg-emerald-950/20 text-emerald-400 font-mono text-[11px] font-bold">
                          ✓ JÁ ENVIADO
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            void onInitiateApply(job);
                          }}
                          className={`px-4 py-2 rounded-lg font-bold text-xs tracking-wider transition-all flex items-center gap-1.5 shadow ${
                            job.applicationType === "auto"
                              ? "bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 hover:opacity-90"
                              : "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                          }`}
                        >
                          {job.applicationType === "auto" ? (
                            <>
                              <Zap className="h-3.5 w-3.5 text-slate-950 fill-slate-950" />
                              <span>Candidatura Automática (IA)</span>
                            </>
                          ) : (
                            <>
                              <ExternalLink className="h-3.5 w-3.5" />
                              <span>Levar para a vaga</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
