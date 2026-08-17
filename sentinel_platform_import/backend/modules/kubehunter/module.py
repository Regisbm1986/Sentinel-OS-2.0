import shlex


def run_kube_hunter(
    cluster_ip,
    executor,
    logger=None,
    flags_extras=""
):
    """
    Módulo de auditoria Kubernetes
    """

    if not cluster_ip:

        if logger:
            logger(
                "Especifique o IP/Domínio do Cluster Kubernetes."
            )

        return

    if logger:
        logger(
            f"[☸️] Preparando Kube-Hunter contra: {cluster_ip}"
        )

    comando = [
        "kube-hunter",
        "--remote",
        cluster_ip
    ]

    if flags_extras:
        comando.extend(
            shlex.split(flags_extras)
        )

    executor(
        comando,
        "KubeHunter-K8s"
    )
