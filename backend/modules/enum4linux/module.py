def run_enum4linux(target, executor):

    if target:

        cmd_enum = [
            "enum4linux",
            "-a",
            target
        ]

        executor(
            cmd_enum,
            "Enum4Linux-Core"
        )

    else:
        print("Nenhum alvo especificado.")
