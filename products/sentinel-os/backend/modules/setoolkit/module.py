import shutil
import subprocess


def run_setoolkit_daemon(logger=None):

    set_path = "/usr/bin/setoolkit"

    if not shutil.which("setoolkit") and not shutil.which(set_path):

        if logger:
            logger(
                "[-] SEToolkit não instalado no servidor."
            )

        return

    try:

        subprocess.Popen(
            [
                "nohup",
                "sudo",
                set_path
            ],
            stdout=open("/tmp/set.log", "a"),
            stderr=subprocess.STDOUT
        )

        if logger:
            logger(
                "[🎭] SEToolkit iniciado em background."
            )

    except Exception as ex:

        if logger:
            logger(
                f"[-] Erro ao iniciar SEToolkit: {ex}"
            )
