def run_command_in_container(container, command: list, stream: bool = False, detach: bool = False, timeout: int = 120) -> dict:
    try:
        if detach:
            bg_command = ["sh", "-c", f"nohup {' '.join(command[2:])} > /tmp/bg_process.log 2>&1 &"]
            exec_result = container.exec_run(cmd=bg_command, detach=True)

            return {
                "success": True,
                "exit_code": 0,
                "output": f"Background process started (exec_id: {exec_result})",
                "command": command,
            }

        if len(command) >= 3 and command[0] == "sh" and command[1] == "-c":
            actual_command = command[2]
            timeout_command = ["sh", "-c", f"timeout {timeout}s sh -c {repr(actual_command)}"]
        else:
            timeout_command = ["timeout", str(timeout)] + command

        exit_code, output = container.exec_run(cmd=timeout_command, stream=stream)

        # Handle streaming output
        if stream:
            output_lines = []
            for chunk in output:
                if chunk:
                    line = chunk.decode("utf-8").strip()
                    output_lines.append(line)
            output = "\n".join(output_lines)
        else:
            output = output.decode("utf-8") if output else ""

        if exit_code == 124:
            return {
                "success": False,
                "exit_code": 124,
                "output": f"Command timed out after {timeout} seconds. This may be a long-running process (web server, dev server, etc.). Consider using is_background=true for such commands.\n\nPartial output:\n{output}",
                "command": command,
            }

        return {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "output": output,
            "command": command,
        }

    except Exception as e:
        return {"success": False, "exit_code": -1, "output": str(e), "command": command}
