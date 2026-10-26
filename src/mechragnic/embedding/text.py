def text_for_embedding(
    symptoms: list[str], causes: list[str], solutions: list[str], include_solutions: bool = False, prefix: str = ""
) -> str:
    lines = [
        f"Symptoms: {'\n- '.join(symptoms)}",
        f"Causes: {'\n- '.join(causes)}",
    ]
    if include_solutions:
        lines.append(f"Solution: {'\n- '.join(solutions)}")

    return prefix + "\n".join(lines)
