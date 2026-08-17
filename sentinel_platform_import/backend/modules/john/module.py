import os
import tempfile
import subprocess


def run_john_the_ripper(hash_text, executor, logger=None):
    """
    Módulo de Auditoria de Credenciais
    """

    if not hash_text:
        if logger:
            logger("Insira hashes válidos para quebra.")
        return

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False
    ) as temp_file:

        temp_file.write(hash_text + "\n")
        temp_file_path = temp_file.name

    try:

        wordlist_path = "/usr/share/wordlists/rockyou.txt"

        if os.path.exists(wordlist_path):

            cmd_john = [
                "john",
                f"--wordlist={wordlist_path}",
                "--rules",
                temp_file_path
            ]

        else:

            cmd_john = [
                "john",
                "--incremental",
                temp_file_path
            ]

            if logger:
                logger(
                    "[⚠️] RockYou não encontrada. "
                    "Executando modo incremental."
                )

        executor(
            cmd_john,
            "John-Cracker"
        )

        resultado_show = subprocess.run(
            [
                "john",
                "--show",
                temp_file_path
            ],
            capture_output=True,
            text=True
        )

        if resultado_show.stdout and logger:

            logger(
                "\n[=== EXTRACTED CRACKED CREDENTIALS ===]"
            )

            logger(
                resultado_show.stdout.strip()
            )

    except Exception as ex:

        if logger:
            logger(
                f"[-] Erro durante execução John: {ex}"
            )

    finally:

        try:
            os.unlink(temp_file_path)
        except Exception as ex:

            if logger:
                logger(
                    f"[-] Erro ao remover arquivo temporário: {ex}"
                )
