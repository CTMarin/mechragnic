from mechragnic.clients.ollama import chat_with_format
from mechragnic.models.mechanic_case import SynthesizedCase
from mechragnic.models.stack_exchange import ApiAnswer, QuestionWithAnswers

SYSTEM_PROMPT = """You are an expert vehicle mechanic. You receive a question from a \
mechanics forum and its answers, and extract a structured diagnostic case from them.

- symptoms: what the owner observes, written the way a driver would describe it, \
followed by the technical term when there is one.
- causes: the causes the answers identify.
- solution: the fixes or checks the answers recommend.

Give more weight to the accepted answer and to higher-scored answers. Use only what \
the thread says; do not add causes or fixes from your own knowledge.

First decide is_fault_diagnosis. It is true when the thread describes a problem with a \
vehicle or any engine-powered machine, and the answers suggest what causes it or how to \
fix it. Typical problems are a noise, a leak, a smell, a warning light or trouble code, \
poor performance, or a part that fails or behaves wrongly, but any problem counts.
Judge by what the owner describes, not by how the question is phrased: "Debugging tips \
for a high pitched noise" and "Is this uneven tire wear normal?" both describe problems.
It is false when there is no problem to diagnose: how-to procedures, part \
compatibility, tools, buying advice and theory questions.
When in doubt, choose true.
When it is false, return empty lists for symptoms, causes and solution."""


def build_messages(question: QuestionWithAnswers) -> list[dict]:
    message_parts: list[str] = [f"Title: {question.title}", f"Question: {question.body}"]
    ranked_answers: list[ApiAnswer] = sorted(
        question.answers, key=lambda answer: (answer.is_accepted, answer.score), reverse=True
    )

    for answer in ranked_answers:
        label: str = f"accepted, score: {answer.score}" if answer.is_accepted else f"score: {answer.score}"
        message_parts.append(f"Answer ({label}): {answer.body}")

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(message_parts)},
    ]


async def synthesize(question: QuestionWithAnswers) -> SynthesizedCase:
    llm_synthesized_response = await chat_with_format(build_messages(question), SynthesizedCase.model_json_schema())
    synthesized_case: SynthesizedCase = SynthesizedCase.model_validate_json(llm_synthesized_response)

    return synthesized_case
