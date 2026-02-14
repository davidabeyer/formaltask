#!/usr/bin/env python3
"""
Prompt Architect Hook - Transforms rough ideas into fully-fleshed prompts.
Activates on #h in user message. Uses Opus 4.5 via OpenRouter.
Sends the optimizing-prompts skill content with user's question as input.
"""

import json
import os
import sys

import httpx

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPUS_MODEL = "anthropic/claude-opus-4.5"

ARCHITECT_PROMPT = """# Prompt Optimizer

You are an expert prompt engineer. Your job is to take a rough question or idea and transform it into a fully-fleshed, optimized prompt that will produce an excellent response.

## Input

<user_question>
{user_prompt}
</user_question>

<conversation_context>
{context}
</conversation_context>

## Your Task

Transform the user's rough question into a COMPLETE, OPTIMIZED PROMPT that will elicit the best possible response. This prompt will be used to answer their actual question.

## Prompt Structure Requirements

Every prompt you produce MUST have:

1. **`<role>`** — 2-4 word expert persona that fits THIS task (not "helpful assistant")
2. **`<purpose>`** — One sentence: what they NEED delivered. Starts with "Your job is..."
3. **`FLOW:`** — Phase sequence (2-4 phases, match depth to stakes)
4. **`<phase>` blocks** — Each with name + style:

| Style | USE FOR |
|-------|---------|
| `divergent` | Brainstorming, generating options, exploring alternatives |
| `sequential` | Building reasoning where each thought depends on prior |
| `adversarial` | Pre-mortems, stress-testing, finding failures |
| `checkpoint` | Final decisions, verification, commitments |

Phase format:
```xml
<phase name="[Name]" style="[style]">
  <instruction>[What to do. Imperative voice.]</instruction>
  <output>[Exact format expected]</output>
</phase>
```

5. **`CONSTRAINTS:`** — Hard rules at the end. Bulleted. Imperative voice.

## Optimization Techniques

Apply these based on the question type:

| Question Type | Technique |
|---------------|-----------|
| Decision/tradeoff | Add adversarial phase to stress-test the answer |
| Research/exploration | Use divergent phase first, then sequential analysis |
| Implementation/how-to | Sequential phases with clear checkpoints |
| Opinion/evaluation | Require explicit criteria before judgment |

## Voice Rules

| Wrong | Right |
|-------|-------|
| "You might want to consider..." | "Analyze X." |
| "It would be helpful to..." | "List the top 3." |
| "Please try to include..." | "Include X. No exceptions." |
| Vague: "think through this" | Specific: "Compare options on cost, speed, risk" |

## Output

Return ONLY the optimized prompt in a code block. No commentary before or after.

The prompt should be ready to copy-paste and will be used to answer the user's original question.

```
<role>[Expert persona for THIS question]</role>

<purpose>Your job is [what they need answered/delivered].</purpose>

FLOW: [PHASE1] → [PHASE2] → ...

<phase name="[Name]" style="[style]">
  [Full instructions and output format]
</phase>

[Additional phases...]

CONSTRAINTS:
- [Hard rule 1]
- [Hard rule 2]
```"""


def extract_recent_context(n_turns: int = 5) -> str:
    """Extract last N turns from transcript as readable context."""
    from formaltask.utils.skill_output import get_current_transcript_path

    transcript_path = get_current_transcript_path()
    if not transcript_path or not os.path.exists(transcript_path):
        return "(No prior conversation)"

    turns = []
    current_turn = {"user": "", "assistant": ""}

    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry.get("type") == "user":
                    if current_turn["user"]:
                        turns.append(current_turn)
                        current_turn = {"user": "", "assistant": ""}
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        current_turn["user"] = content.strip()
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                current_turn["user"] += item.get("text", "")

                elif entry.get("type") == "assistant":
                    content = entry.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                current_turn["assistant"] += item.get("text", "")
                    elif isinstance(content, str):
                        current_turn["assistant"] = content

        if current_turn["user"]:
            turns.append(current_turn)

    except OSError:
        return "(No prior conversation)"

    if not turns:
        return "(No prior conversation)"

    recent = turns[-(n_turns + 1) : -1] if len(turns) > 1 else []

    if not recent:
        return "(No prior conversation)"

    lines = []
    for t in recent:
        if t["user"]:
            lines.append(f"> **User:** {t['user']}")
        if t["assistant"]:
            assistant_text = t["assistant"]
            if len(assistant_text) > 2000:
                assistant_text = assistant_text[:2000] + "..."
            lines.append(f"> **Claude:** {assistant_text}")
        lines.append("")

    return "\n".join(lines).strip() if lines else "(No prior conversation)"


def extract_prompt_block(content: str) -> str | None:
    """Extract the prompt from a code block in the response."""
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            block = parts[1]
            if block.startswith(("markdown", "xml", "\n")):
                block = block.split("\n", 1)[-1] if "\n" in block else block
            return block.strip()

    return content.strip()


def call_opus(user_prompt: str) -> dict:
    """Call Opus 4.5 via OpenRouter to architect the prompt."""
    if not OPENROUTER_API_KEY:
        return {"error": "OPENROUTER_API_KEY not set"}

    context = extract_recent_context(n_turns=5)
    clean_prompt = user_prompt.replace("#h", "").strip()

    prompt = ARCHITECT_PROMPT.format(user_prompt=clean_prompt, context=context)

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPUS_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 16000,
                "temperature": 0.3,
            },
            timeout=120.0,
        )
        response.raise_for_status()

        content = response.json()["choices"][0]["message"]["content"]
        return {"content": content}

    except httpx.TimeoutException:
        return {"error": "Opus request timed out"}
    except Exception as e:
        return {"error": str(e)}


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    user_prompt = input_data.get("prompt", "")

    if "#h" not in user_prompt:
        sys.exit(0)

    result = call_opus(user_prompt)

    if "error" in result:
        print(f"Prompt architect error: {result['error']}", file=sys.stderr)
        sys.exit(0)

    content = result.get("content", "")
    if not content:
        print("Prompt architect: No response", file=sys.stderr)
        sys.exit(0)

    fleshed_prompt = extract_prompt_block(content)

    scaffold = f"""# Optimized Prompt

Use this prompt to answer your question:

---

{fleshed_prompt}

---

Now execute this prompt to answer the original question."""

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": scaffold,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
