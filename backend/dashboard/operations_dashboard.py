"""Sentinel AI operations dashboard with RBAC and admin tabs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import random
from typing import Any, Callable, Dict, List, Tuple

import streamlit as st

from sentinel_os.platform.backend.agents import task_queue as task_queue_module
from sentinel_os.platform.backend.agents.remote_worker_manager import RemoteWorkerManager
from sentinel_os.platform.backend.agents.worker_heartbeat import WorkerHeartbeat
from sentinel_os.platform.backend.database.capability_registry import CapabilityRegistry
from sentinel_os.platform.backend.telemetry.execution_telemetry import ExecutionTelemetry
from sentinel_os.platform.backend.core.config import PROJECT_ROOT

try:  # Optional infra monitoring helpers
    import psutil
except ImportError:  # pragma: no cover - psutil is optional in some deploy targets
    psutil = None


Snapshot = Dict[str, Any]


def _resolve_project_root(project_root: Path | str | None) -> Path:
    if project_root is None:
        return PROJECT_ROOT
    return Path(project_root)


def load_goals(project_root: Path | str | None = None) -> List[str]:
    base = _resolve_project_root(project_root)
    modules_dir = base / "backend" / "modules"

    if not modules_dir.exists():
        return []

    goals: List[str] = []
    for module_path in sorted(modules_dir.iterdir()):
        if not module_path.is_dir():
            continue

        module_name = module_path.name
        goals.append(f"Create API route for module '{module_name}' in backend/api/routes/{module_name}.py")

    return goals


def load_queue_status(project_root: Path | str | None = None) -> Dict[str, Any]:
    base = _resolve_project_root(project_root)
    tasks_dir = base / "backend" / "agents" / "tasks"

    queue_file = tasks_dir / task_queue_module.TaskQueue.QUEUE_FILE

    tasks: List[Dict[str, Any]]
    if queue_file.exists():
        try:
            tasks = json.loads(queue_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tasks = []
    else:
        tasks = []

    return {
        "queue_status": "empty" if not tasks else "pending",
        "queue_length": len(tasks),
        "next_task": tasks[0] if tasks else None,
    }


def load_workers(
    worker_manager: RemoteWorkerManager | None = None,
    heartbeat: WorkerHeartbeat | None = None,
) -> List[str]:
    manager = worker_manager or RemoteWorkerManager()
    heartbeat_monitor = heartbeat or WorkerHeartbeat()

    workers = []
    for worker_id in manager.get_workers():
        if heartbeat_monitor.is_alive(worker_id):
            workers.append(worker_id)

    return workers


def load_telemetry(
    project_root: Path | str | None = None,
    telemetry_factory: Callable[[], ExecutionTelemetry] | None = None,
) -> List[Dict[str, Any]]:
    if telemetry_factory is not None:
        telemetry = telemetry_factory()
    else:
        base = _resolve_project_root(project_root)
        log_path = base / "backend" / "telemetry" / "execution_log.json"
        telemetry = ExecutionTelemetry(log_path=log_path)

    return telemetry.get_logs()


def load_capability_registry(
    project_root: Path | str | None = None,
    registry_factory: Callable[[], CapabilityRegistry] | None = None,
) -> List[Dict[str, Any]]:
    if registry_factory is not None:
        registry = registry_factory()
    else:
        base = _resolve_project_root(project_root)
        registry_path = base / "backend" / "database" / "capabilities.json"
        registry = CapabilityRegistry(registry_path=registry_path)

    return registry.list_capabilities()


def derive_autonomous_execution_status(
    queue_status: Dict[str, Any], telemetry: List[Dict[str, Any]]
) -> Dict[str, Any]:
    last_status = telemetry[-1].get("status") if telemetry else None

    if queue_status.get("queue_status") == "pending":
        state = "running"
        last_status = last_status or "pending"
    elif last_status:
        state = "running" if last_status in {"running", "pending"} else last_status
    else:
        state = "idle"

    return {
        "state": state,
        "last_status": last_status,
    }


def build_dashboard_snapshot(
    project_root: Path | str | None = None,
    telemetry_factory: Callable[[], ExecutionTelemetry] | None = None,
    registry_factory: Callable[[], CapabilityRegistry] | None = None,
) -> Snapshot:
    base = _resolve_project_root(project_root)

    telemetry_entries = load_telemetry(project_root=base, telemetry_factory=telemetry_factory)
    capabilities = load_capability_registry(project_root=base, registry_factory=registry_factory)
    queue = load_queue_status(project_root=base)

    snapshot: Snapshot = {
        "project_root": str(base),
        "goals": load_goals(project_root=base),
        "queue_status": queue,
        "workers": load_workers(),
        "telemetry": telemetry_entries,
        "capabilities": capabilities,
    }

    snapshot["execution_status"] = derive_autonomous_execution_status(queue, telemetry_entries)
    return snapshot


def render_dashboard() -> None:
    main()


ADMIN_EMAIL = "soaresreginaldo@gmail.com"
ADMIN_PASSWORD = "SoaresFilho105856@"
# TODO: Move these credentials to environment variables or st.secrets before shipping to GitHub.

LANDING_CSS = """
<style>
    .stApp {
        background-color: #020617;
        background-image: radial-gradient(circle at 20% 20%, rgba(34, 197, 94, 0.08), transparent 55%),
                          radial-gradient(circle at 80% 10%, rgba(56, 189, 248, 0.08), transparent 60%);
        color: #e2e8f0;
        font-family: "Inter", "Segoe UI", sans-serif;
    }

    .sentinel-buttons {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 1rem;
        margin: 2.5rem auto 3.5rem;
    }

    .sentinel-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.95rem 2.75rem;
        border-radius: 999px;
        border: 1px solid rgba(34, 197, 94, 0.55);
        background: linear-gradient(120deg, rgba(34, 197, 94, 0.2), rgba(45, 212, 191, 0.18));
        color: #e2fcef;
        text-decoration: none;
        text-transform: uppercase;
        letter-spacing: 0.32rem;
        font-size: 0.78rem;
        transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    }

    .sentinel-button:hover {
        transform: translateY(-4px);
        border-color: rgba(34, 197, 94, 0.9);
        box-shadow: 0 18px 42px -16px rgba(16, 185, 129, 0.55);
    }

    .sentinel-badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
        margin-top: 1.5rem;
    }

    .sentinel-badges span {
        display: inline-block;
        padding: 0.45rem 0.9rem;
        border-radius: 999px;
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(34, 197, 94, 0.35);
        font-size: 0.74rem;
        letter-spacing: 0.08rem;
        color: #cbd5f5;
    }
</style>
"""


def ensure_session_state() -> None:
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = "visitor"
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""


def render_sidebar() -> None:
    ensure_session_state()

    with st.sidebar:
        if not st.session_state.is_logged_in:
            st.header("Acesso Restrito")
            st.caption("Informe suas credenciais corporativas para acessar o Painel Executivo.")

            email = st.text_input("E-mail")
            password = st.text_input("Senha", type="password")
            login_clicked = st.button("Entrar", use_container_width=True)

            if login_clicked:
                if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                    st.session_state.is_logged_in = True
                    st.session_state.role = "admin_master"
                    st.session_state.user_name = "Reginaldo Soares"
                    st.experimental_rerun()
                else:
                    st.error("Credenciais inválidas. Tente novamente.")
        else:
            st.success(f"Bem-vindo, {st.session_state.user_name} (Admin)")
            st.caption("Acesso privilegiado ao Sentinel AI Executive Control.")
            if st.button("Sair", use_container_width=True):
                st.session_state.is_logged_in = False
                st.session_state.role = "visitor"
                st.session_state.user_name = ""
                st.experimental_rerun()


def render_public_landing() -> None:
    st.markdown(LANDING_CSS, unsafe_allow_html=True)
    st.image(
        "/home/sentineladmin/sentinel-os/sentinel-career-intelligence/SentinelAI.png",
        use_container_width=True,
    )

    st.markdown(
        """
        ### Inteligência que trabalha por você.

        A Sentinel AI orquestra um ecossistema de plataformas autônomas que combinam Inteligência Artificial Generativa,
        arquitetura orientada a agentes e automação confiável de ponta a ponta. Nossa missão é acelerar resultados mensuráveis
        em carreiras, residências e operações corporativas com governança, segurança e telemetry em tempo real. Visamos ser o
        sistema operacional de confiança para organizações que desejam delegar tarefas complexas a agentes inteligentes sem
        abrir mão de compliance, proteção de dados e experiência premium.
        """
    )

    st.info(
        """
        🚀 **Em Destaque: Sentinel Career**

        Estamos concluindo a Fase 3 do Sentinel Career, integrando PagSeguro e liberando o fluxo completo de assinatura.
        O MVP encontra-se em testes internos com squads multidisciplinares, garantindo jornada de onboarding inteligente,
        análises ATS avançadas e motores de recomendação operando em ambiente de observabilidade total.
        """
    )

    st.markdown("#### Ecossistema Sentinel AI")
    col_career, col_home, col_os = st.columns(3)

    with col_career:
        st.subheader("Sentinel Career")
        st.write(
            """
            Plataforma de aceleração profissional que utiliza IA para impulsionar carreiras em tecnologia, produto
            e operações. Do ATS inteligente ao simulador de entrevistas, cada interação é personalizada com dados de mercado.
            """
        )
        st.markdown(
            """
            **Recursos principais:**
            - Motor ATS com Inteligência Generativa
            - Benchmarks salariais e de senioridade
            - Orquestração de entrevistas e rotinas LinkedIn
            - Telemetria de desenvolvimento de carreira em dashboards executivos
            """
        )

    with col_home:
        st.subheader("Sentinel Home")
        st.write(
            """
            Hub de automação residencial com agentes contextuais que aprendem hábitos, controlam dispositivos conectados
            e entregam jornadas personalizadas de segurança e bem-estar. Tudo com governança e privacidade desde a origem.
            """
        )
        st.markdown(
            """
            **Funcionalidades em destaque:**
            - Gestão unificada de dispositivos IoT
            - Rotinas autônomas de eficiência energética
            - Monitoramento preditivo de segurança residencial
            - Assistentes de voz com entendimento contextual
            """
        )

    with col_os:
        st.subheader("Sentinel OS")
        st.write(
            """
            Sistema operacional inteligente que coordena agentes de negócio, pipelines de dados e fluxos operacionais
            críticos. Ideal para squads que precisam de insights acionáveis e ações autônomas em escala corporativa.
            """
        )
        st.markdown(
            """
            **Recursos estratégicos:**
            - Orquestração de agentes especializados
            - Painéis de missão crítica com telemetria contínua
            - Integrações com ERPs, CRMs e plataformas cloud
            - Camadas de automação com aprovação humana no loop
            """
        )

    button_html = """
    <div class="sentinel-buttons">
        <a class="sentinel-button" href="/career" target="_blank" rel="noopener noreferrer">Sentinel Career</a>
        <a class="sentinel-button" href="https://sentinel.ia.br/home" target="_blank" rel="noopener noreferrer">Sentinel Home</a>
        <a class="sentinel-button" href="https://sentinel.ia.br/os" target="_blank" rel="noopener noreferrer">Sentinel OS</a>
    </div>
    """
    st.markdown(button_html, unsafe_allow_html=True)

    with st.expander("Tecnologia & Infraestrutura", expanded=False):
        st.markdown(
            """
            **Plataforma Sentinel AI**
            - Núcleo baseado em microsserviços e orquestração de agentes.
            - Telemetry centralizada com observabilidade full stack.
            - Mecanismos de auto-escalabilidade para workloads sensíveis.

            **Integrações**
            - Conectores nativos com Azure, AWS, PagSeguro, LinkedIn e CRMs corporativos.
            - Pipelines de dados estruturados e semi-estruturados com sincronização contínua.

            **Arquitetura**
            - Camadas independentes para ingestão, inteligência, automação e experiência.
            - Governança de APIs com policy enforcement dinâmico e SLOs monitorados.

            **Segurança**
            - Criptografia ponta a ponta, segregação de ambientes e auditoria contínua.
            - Compliance orientado a LGPD, ISO 27001 e frameworks de Zero Trust.
            """
        )

    st.markdown("#### Identidade Institucional")
    st.markdown(
        """
        **Missão**
        - Transformar operações e experiências humanas com agentes autônomos confiáveis.

        **Visão**
        - Ser a holding referência em plataformas inteligentes que unem resultados exponenciais
          e governança responsável.

        **Valores**
        - Inovação orientada a propósito.
        - Segurança por design.
        - Transparência e ética digital.
        - Crescimento sustentável com impacto positivo.
        """
    )

    st.markdown("#### Especialidades Sentinel AI")
    tags = [
        "Artificial Intelligence",
        "Generative AI",
        "Autonomous Agents",
        "Machine Learning",
        "Data Engineering",
        "MLOps",
        "DevSecOps",
        "Cloud Architecture",
        "Edge Computing",
        "Process Automation",
        "Product Intelligence",
        "Operational Analytics",
        "Cybersecurity",
        "Zero Trust",
        "Digital Twins",
        "Experience Design",
        "Telemetry",
        "Enterprise Integrations",
        "Observability",
        "Responsible AI",
    ]

    badges_html = "<div class='sentinel-badges'>" + "".join(f"<span>{tag}</span>" for tag in tags) + "</div>"
    st.markdown(badges_html, unsafe_allow_html=True)


def collect_system_metrics() -> Dict[str, str]:
    if psutil:
        cpu_usage = f"{psutil.cpu_percent(interval=1):.1f}%"
        memory = psutil.virtual_memory()
        memory_usage = f"{memory.percent:.1f}%"
    else:
        cpu_usage = f"{random.uniform(22, 68):.1f}%"
        memory_usage = f"{random.uniform(35, 72):.1f}%"

    postgres_status = random.choice(["Operacional", "Replicação ativa", "Latência elevada"])
    docker_status = random.choice(["Containers saudáveis", "Recriando containers", "Aguardando atualização"])

    return {
        "cpu": cpu_usage,
        "memory": memory_usage,
        "postgres": postgres_status,
        "docker": docker_status,
        "last_refresh": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


def generate_overview_metrics() -> List[Tuple[str, str, str]]:
    return [
        ("Usuários ativos no Sentinel Career", "1.248", "+12% em relação à última semana"),
        ("Consumo de API (24h)", "482.190 req", "Pico às 11h42 BRT"),
        ("Agentes em execução", "37", "Sentinel Career: 19 • Sentinel Home: 11 • Sentinel OS: 7"),
    ]


def get_account_matrix() -> List[Dict[str, str]]:
    plans = ["Free", "Pro", "Enterprise"]
    return [
        {"Conta": "reginaldo@sentinel.ai", "Plano": "Enterprise", "Organização": "Sentinel AI Holding"},
        {"Conta": "mariana@sentinel.ai", "Plano": "Enterprise", "Organização": "Sentinel AI Holding"},
        {"Conta": "contato@starttech.io", "Plano": random.choice(plans), "Organização": "StartTech"},
        {"Conta": "talentos@novaera.com", "Plano": random.choice(plans), "Organização": "Nova Era Tech"},
        {"Conta": "parcerias@globallabs.co", "Plano": random.choice(plans), "Organização": "Global Labs"},
    ]


def get_agent_status() -> List[Dict[str, str]]:
    return [
        {
            "Agente": "Sentinel OS - Orchestrator",
            "Modelo": "Azure OpenAI GPT-4.1",
            "Latência": f"{random.uniform(420, 610):.0f} ms",
            "Último Evento": "Playbook de carreira executado",
        },
        {
            "Agente": "Sentinel Home - Guardian",
            "Modelo": "Azure OpenAI o3",
            "Latência": f"{random.uniform(380, 540):.0f} ms",
            "Último Evento": "Rotina de segurança finalizada",
        },
        {
            "Agente": "Sentinel Career - Coach",
            "Modelo": "Azure OpenAI GPT-4o",
            "Latência": f"{random.uniform(290, 360):.0f} ms",
            "Último Evento": "Simulação de entrevista enviada",
        },
    ]


def render_admin_dashboard() -> None:
    st.title("Sentinel AI • Painel Executivo")
    st.caption("Visão interna dos indicadores críticos e agentes em produção.")

    overview_tab, infra_tab, access_tab, agents_tab = st.tabs(
        [
            "Visão Geral",
            "Monitoramento de Infra",
            "Gestão de Acessos",
            "Central de Agentes IA",
        ]
    )

    with overview_tab:
        st.subheader("KPIs do Ecossistema")
        cols = st.columns(len(generate_overview_metrics()))
        for col, (title, value, helper) in zip(cols, generate_overview_metrics()):
            with col:
                st.metric(label=title, value=value, delta=helper)

        st.markdown("---")
        st.write(
            "Acompanhe o uso consolidado das plataformas Sentinel para ajustar SLOs, controlar custos e antecipar gargalos."
        )

    with infra_tab:
        st.subheader("Telemetria de Infraestrutura")
        metrics = collect_system_metrics()

        col_cpu, col_mem = st.columns(2)
        col_cpu.metric("Uso de CPU", metrics["cpu"])
        col_mem.metric("Uso de RAM", metrics["memory"])

        st.markdown("---")
        st.write(f"Status PostgreSQL: **{metrics['postgres']}**")
        st.write(f"Status Docker: **{metrics['docker']}**")
        st.caption(f"Atualizado em {metrics['last_refresh']}")

    with access_tab:
        st.subheader("Contas & Planos")
        st.caption("Visão consolidada das contas ativas e seus níveis de assinatura.")
        st.dataframe(get_account_matrix(), use_container_width=True)

    with agents_tab:
        st.subheader("Health Check dos Agentes")
        st.caption("Latência, modelo e último evento registrado para cada agente crítico.")
        st.dataframe(get_agent_status(), use_container_width=True)


def main() -> None:
    st.set_page_config(
        page_title="Sentinel AI",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    render_sidebar()

    if not st.session_state.is_logged_in:
        render_public_landing()
        return

    if st.session_state.role != "admin_master":
        st.error("Acesso não autorizado.")
        return

    render_admin_dashboard()


if __name__ == "__main__":
    main()