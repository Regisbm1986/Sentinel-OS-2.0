import React, { useState } from "react";
import { Zap, ShieldCheck, Check, Sparkles, AlertCircle } from "lucide-react";
import { PlanType } from "../types";
import { apiFetch } from "../lib/apiClient";

interface PlanSelectorProps {
  currentPlan: PlanType;
  setPlan: (plan: PlanType) => void;
  autoAppliesUsed: number;
  autoApplyLimit: number | null;
  autoApplyRemaining: number | null;
}

export default function PlanSelector({ currentPlan, setPlan, autoAppliesUsed, autoApplyLimit, autoApplyRemaining }: PlanSelectorProps) {
  const [processingPlan, setProcessingPlan] = useState<PlanType | null>(null);

  const handlePlanSelection = async (planId: PlanType) => {
    if (processingPlan) {
      return;
    }

    if (planId === "free") {
      setPlan(planId);
      return;
    }

    try {
      setProcessingPlan(planId);
      const response = await apiFetch("/api/payments/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_id: planId }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const detail = data && typeof data === "object" && "detail" in data ? (data as Record<string, unknown>).detail : null;
        throw new Error((typeof detail === "string" && detail.trim()) || "Falha ao iniciar o checkout do plano.");
      }

      if (data && typeof data === "object" && typeof (data as Record<string, unknown>).url === "string") {
        const checkoutUrl = (data as Record<string, unknown>).url as string;
        if (checkoutUrl.trim().length > 0) {
          window.location.href = checkoutUrl;
          return;
        }
      }

      if (data && typeof data === "object" && typeof (data as Record<string, unknown>).init_point === "string") {
        window.location.href = (data as Record<string, unknown>).init_point as string;
        return;
      }

      throw new Error("Checkout do Mercado Pago não retornou um link válido.");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Não foi possível gerar o checkout do plano.";
      alert(message);
      console.error("[PlanSelector] Falha ao criar checkout do plano", err);
    } finally {
      setProcessingPlan(null);
    }
  };

  const getLimitLabel = (planId: PlanType, fallbackLimit: number | null) => {
    if (planId === currentPlan) {
      if (autoApplyLimit === null) {
        return "Aplicações ilimitadas";
      }
      const remainingLabel =
        autoApplyRemaining !== null && autoApplyRemaining >= 0
          ? ` • Restantes: ${autoApplyRemaining}`
          : "";
      return `${autoAppliesUsed}/${autoApplyLimit} aplicações usadas${remainingLabel}`;
    }

    if (fallbackLimit === null) {
      return "Aplicações ilimitadas";
    }
    return `Até ${fallbackLimit} Auto-Applications/mês`;
  };

  const getUsagePercentage = (planId: PlanType, fallbackLimit: number | null) => {
    if (planId === currentPlan) {
      if (autoApplyLimit === null) {
        return autoAppliesUsed > 0 ? 15 : 0;
      }
      if (autoApplyLimit <= 0) {
        return 0;
      }
      return Math.min((autoAppliesUsed / autoApplyLimit) * 100, 100);
    }

    if (!fallbackLimit) {
      return autoAppliesUsed > 0 ? 15 : 0;
    }
    return Math.min((autoAppliesUsed / fallbackLimit) * 100, 100);
  };

  const plans = [
    {
      id: "free" as PlanType,
      name: "Sentinel Free",
      price: "R$ 0",
      description: "Experimente a inteligência de busca básica.",
      features: [
        "Score de compatibilidade ATS de currículo",
        "Busca manual de vagas (Scout)",
        "Limite de 3 Auto-Applications por mês",
        "Suporte padrão Sentinel"
      ],
      fallbackLimit: 3,
      badgeColor: "bg-slate-700 text-slate-200 border-slate-600",
      buttonStyle: "border-slate-700 text-slate-300 hover:bg-slate-800"
    },
    {
      id: "pro" as PlanType,
      name: "Sentinel Career Pro",
      price: "R$ 39/mês",
      description: "Ideal para profissionais em transição de carreira ativa.",
      features: [
        "Score completo de currículo com sugestões de reescrita por IA",
        "Otimizador de Perfil do LinkedIn completo por IA",
        "Gerador de Cartas de Apresentação customizadas",
        "Limite de 100 Auto-Applications por mês",
        "Filtro avançado de matching por salário"
      ],
      fallbackLimit: 100,
      badgeColor: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
      buttonStyle: "bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400"
    },
    {
      id: "enterprise" as PlanType,
      name: "Sentinel Enterprise",
      price: "R$ 79/mês",
      description: "Automação e auditoria cibernética completa de ponta a ponta.",
      features: [
        "Aplicações automáticas ilimitadas de alta conversão",
        "Agente de Busca autônomo (trabalha 24/7 em background)",
        "Proteção cibernética de dados de currículo (anomalia de dados)",
        "Atalho 'Levar para a vaga' com preenchimento assistido semi-automático",
        "Suporte prioritário via WhatsApp e e-mail da Sentinel IA"
      ],
      fallbackLimit: null,
      badgeColor: "bg-purple-500/10 text-purple-400 border-purple-500/30",
      buttonStyle: "bg-purple-600 text-white font-bold hover:bg-purple-500"
    }
  ];

  return (
    <div id="plan-panel" className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 backdrop-blur-sm relative overflow-hidden">
      {/* Cyber ambient decoration */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/5 rounded-full blur-2xl"></div>

      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
        <div>
          <h2 className="text-xl font-sans font-bold text-white tracking-tight flex items-center gap-2">
            <Zap className="h-5 w-5 text-cyan-400" />
            Planos de Automação & Análise
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Cada modalidade possui limites específicos para o agente de IA otimizar e candidatar você.
          </p>
        </div>

        {/* Current active plan display indicator */}
        <div className="flex items-center gap-3 bg-slate-950/60 border border-slate-800 px-4 py-2.5 rounded-lg">
          <div className="p-2 bg-cyan-500/10 rounded-full border border-cyan-500/20">
            <ShieldCheck className="h-4 w-4 text-cyan-400" />
          </div>
          <div>
            <div className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Plano Ativo no Sentinel OS</div>
            <div className="text-sm font-bold text-white capitalize">{currentPlan}</div>
          </div>
        </div>
      </div>

      {/* Plans list */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {plans.map((plan) => {
          const isCurrent = currentPlan === plan.id;
          const usageLabel = getLimitLabel(plan.id, plan.fallbackLimit);
          const usagePercent = getUsagePercentage(plan.id, plan.fallbackLimit);
          return (
            <div
              key={plan.id}
              className={`border rounded-xl p-5 relative flex flex-col justify-between transition-all duration-300 ${
                isCurrent
                  ? "border-cyan-400/60 bg-cyan-950/5 shadow-[0_0_20px_rgba(6,182,212,0.05)]"
                  : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
              }`}
            >
              {isCurrent && (
                <span className="absolute -top-3 right-4 bg-cyan-500 text-slate-950 font-mono text-[9px] font-bold px-2 py-0.5 rounded-full tracking-wider uppercase border border-cyan-400">
                  ATIVO
                </span>
              )}

              <div>
                <div className="flex justify-between items-start">
                  <h3 className="font-sans font-bold text-white text-md">{plan.name}</h3>
                  <span className="font-mono text-cyan-400 text-sm font-bold">{plan.price}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1 line-clamp-2 min-h-[32px]">
                  {plan.description}
                </p>

                {/* Automation limits meter */}
                <div className="mt-4 bg-slate-950/80 p-3 rounded-lg border border-slate-800/80">
                  <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1.5">
                    <span>CONSUMO DE AUTO-APPLIES</span>
                    <span className="font-bold text-slate-200">{usageLabel}</span>
                  </div>
                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        plan.id === "enterprise"
                          ? "bg-purple-500"
                          : usagePercent > 80
                          ? "bg-rose-500"
                          : "bg-cyan-400"
                      }`}
                      style={{
                        width: `${
                          plan.id === "enterprise" && plan.fallbackLimit === null ? 100 : usagePercent
                        }%`,
                      }}
                    ></div>
                  </div>
                </div>

                {/* Features checklist */}
                <ul className="space-y-2 mt-5 text-xs text-slate-300">
                  {plan.features.map((feat, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <Check className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mt-6">
                <button
                  onClick={() => handlePlanSelection(plan.id)}
                  className={`w-full py-2 px-3 rounded-lg text-xs tracking-wide transition-all border ${
                    isCurrent
                      ? "bg-slate-950 border-cyan-500/30 text-cyan-400 hover:bg-slate-900 cursor-default"
                      : plan.buttonStyle
                  }`}
                  disabled={isCurrent || Boolean(processingPlan)}
                >
                  {isCurrent
                    ? "Plano Selecionado"
                    : processingPlan === plan.id
                    ? "Gerando checkout..."
                    : `Migrar para o ${plan.id.toUpperCase()}`}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Plan limits warnings */}
      {currentPlan === "free" && (
        <div className="mt-5 flex items-center gap-3 bg-amber-950/20 border border-amber-500/20 rounded-lg p-3 text-xs text-amber-300">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <p>
            Você está no <strong>Plano Free</strong>. A otimização do LinkedIn e geração de cartas de apresentação estão bloqueadas. Seu limite de candidaturas está restrito a 3 envios. Considere migrar para o <strong>Pro</strong> ou <strong>Enterprise</strong> para experimentar todos os serviços de IA avançada.
          </p>
        </div>
      )}

      {/* Microsoft Azure trust and infrastructure credibility badge */}
      <div className="mt-5 border border-blue-500/20 bg-blue-950/5 rounded-lg p-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-blue-300">
        <div className="flex items-center gap-3">
          <div className="flex space-x-0.5 shrink-0">
            {/* Minimalist 4-box Microsoft logo vibe */}
            <div className="grid grid-cols-2 gap-0.5">
              <div className="h-2 w-2 bg-[#f25022]"></div>
              <div className="h-2 w-2 bg-[#7fba00]"></div>
              <div className="h-2 w-2 bg-[#00a4ef]"></div>
              <div className="h-2 w-2 bg-[#ffb900]"></div>
            </div>
          </div>
          <div>
            <p className="font-semibold text-slate-200">Plataforma Homologada e Hospedada no Microsoft Azure</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Desenvolvido sobre Máquinas Virtuais (VM) seguras na Azure e impulsionado pelo motor cognitivo do <strong>Azure OpenAI Services</strong>. Garantia de estabilidade de 99.9% SLA corporativo.
            </p>
          </div>
        </div>
        <div className="text-[9px] font-mono border border-blue-500/30 bg-blue-950/30 px-2 py-1 rounded text-blue-400 font-bold uppercase tracking-widest shrink-0">
          Azure VM Verified
        </div>
      </div>
    </div>
  );
}
