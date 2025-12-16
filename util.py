from typing import Any, Dict


def parse_task_description(task_description_text: str) -> Dict[str, Any]:
    result = {}

    lines = task_description_text.strip().split("\n")

    is_yaml_format = False
    if lines and lines[0].strip().startswith("task_description:"):
        is_yaml_format = True

    if is_yaml_format:
        in_task_description = False
        task_content_lines = []
        remaining_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped.startswith("task_description:"):
                in_task_description = True
                continue
            elif in_task_description:
                if line.startswith("  ") or not stripped:
                    task_content_lines.append(line[2:] if line.startswith("  ") else "")
                else:
                    remaining_lines = lines[i:]
                    break

        task_content = "\n".join(task_content_lines).strip()
        task_lines = task_content.split("\n")

        objective_lines = []
        in_objective = False

        for task_line in task_lines:
            task_line = task_line.strip()
            if not task_line:
                continue

            if ":" in task_line and not in_objective:
                key, value = task_line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if key == "objective" or key == "instructions":
                    in_objective = True
                    if value:
                        objective_lines.append(value)
                else:
                    result[key] = value
            elif in_objective:
                objective_lines.append(task_line)

        if objective_lines:
            result["instructions"] = "\n".join(objective_lines).strip()

        for line in remaining_lines:
            line = line.strip()
            if not line:
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if key == "parser_name" and value.startswith("<"):
                    result[key] = value.strip("<>")
                else:
                    result[key] = value

        result.setdefault("author_name", "System")
        result.setdefault("author_email", "system@example.com")
        result.setdefault("difficulty", "medium")
        result.setdefault("category", "Backend")
        result.setdefault("tags", ["mern"])
        result.setdefault("parser_name", "jest")

        return result

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()

            if key == "tags" and value.startswith("<"):
                result[key] = [tag.strip("<>") for tag in value.split()]
            elif key == "parser_name" and value.startswith("<"):
                result[key] = value.strip("<>")
            else:
                result[key] = value

    instructions_lines = []
    in_instructions = False

    for line in lines:
        line = line.strip()
        if line.startswith("Instructions:"):
            in_instructions = True
            instructions_lines.append(line.split(":", 1)[1].strip())
        elif (
            in_instructions
            and line
            and not line.startswith(
                ("author_", "difficulty:", "category:", "tags:", "parser_name:")
            )
        ):
            instructions_lines.append(line)

    if instructions_lines:
        result["instructions"] = "\n".join(instructions_lines).strip()

    return result


def test_task_description_parser():
    sample_content = """task_description |
  Task: add is_odd
  Task ID: 001

  Instructions: add is_odd and have main.py print out whether or not the random
  number is odd.

author_name: Author Name
author_email: <you@example.com>
difficulty: easy
category: Feature
tags: <python>
parser_name: <pytest>"""

    parsed = parse_task_description(sample_content)

    print("Parsed task description:")
    print(f"Task: {parsed.get('task')}")
    print(f"Task ID: {parsed.get('task_id')}")
    print(f"Instructions: {parsed.get('instructions')}")
    print(f"Author: {parsed.get('author_name')}")
    print(f"Difficulty: {parsed.get('difficulty')}")
    print(f"Tags: {parsed.get('tags')}")
    print(f"Parser: {parsed.get('parser_name')}")

    return parsed


if __name__ == "__main__":
    test_task_description_parser()
