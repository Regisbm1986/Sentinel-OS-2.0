import React from "react";
import { Globe, CheckCircle2, Cpu, Cloud, AlertTriangle } from "lucide-react";
import { PlanType } from "../types";
import logoCareerIcon from "../assets/images/logo-career-icon.png";

interface HeaderProps {
  currentPlan: PlanType;
  azureConfigured: boolean;
  userEmail: string;
}

export default function Header({ currentPlan, azureConfigured, userEmail }: HeaderProps) {
  return (
    <header id="sentinel-header" className="border-b border-cyan-500/20 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="absolute -inset-1 bg-cyan-500 rounded-lg blur opacity-30 animate-pulse"></div>
              <div className="relative bg-slate-900 border border-cyan-400 p-1.5 rounded-lg">
                <img
                  src={logoCareerIcon}
                  alt="Sentinel Career"
                  className="h-7 w-7"
                  loading="lazy"
                />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-sans font-bold text-lg tracking-wider text-white">SENTINEL</span>
                <span className="bg-cyan-500/10 text-cyan-400 border border-cyan-400/30 text-[10px] font-mono px-1.5 py-0.5 rounded tracking-widest uppercase">Career</span>
              </div>
              <div className="flex items-center space-x-1.5 text-[10px] font-mono text-slate-400 mt-0.5">
                <Globe className="h-2.5 w-2.5 text-cyan-500/70" />
                <span>sentinel-os.ia.br/career</span>
                <span className="text-slate-600">•</span>
                <span className="text-cyan-400 flex items-center space-x-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping mr-1"></span>
                  Sessão Integrada
                </span>
              </div>
            </div>
          </div>

          {/* Quick Stats & API Status */}
          <div className="hidden lg:flex items-center space-x-5 text-xs border-x border-slate-800 px-6 py-2">
            <div className="flex items-center space-x-2">
              <Cpu className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-slate-400 font-mono text-[11px]">IA:</span>
              <span
                className={`flex items-center space-x-1 font-mono px-2 py-0.5 rounded border text-[10px] ${
                  azureConfigured
                    ? "text-cyan-400 bg-cyan-950/30 border-cyan-500/20"
                    : "text-amber-400 bg-amber-950/20 border-amber-500/20"
                }`}
              >
                {azureConfigured ? (
                  <CheckCircle2 className="h-3 w-3 text-cyan-400" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-amber-400" />
                )}
                <span>{azureConfigured ? "Azure OpenAI GPT-4o" : "Azure OpenAI Offline"}</span>
              </span>
            </div>
          </div>

          {/* User Profile */}
          <div className="flex items-center space-x-3">
            <div className="text-right">
              <p className="text-xs font-semibold text-slate-200 truncate max-w-[150px]">
                {userEmail || "contato@sentinel-os.ia.br"}
              </p>
              <p className="text-[10px] font-mono text-cyan-400 uppercase tracking-widest">
                PLANO {currentPlan}
              </p>
            </div>
            <div className="h-8 w-8 rounded-full border border-cyan-400/50 bg-slate-800 flex items-center justify-center overflow-hidden">
              <span className="font-mono text-cyan-400 text-xs font-bold uppercase">
                {(userEmail || "U").substring(0, 2)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
