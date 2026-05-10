import os
import sys

import anthropic
import questionary

MODEL = "claude-opus-4-7"

SYSTEM_PROMPT = """\
You are an expert video prompt engineer specializing in prompts for AI video \
generation models, particularly ByteDance's Seedance 2.0.

You will receive a set of structured inputs describing a desired video. \
Synthesize them into a single, polished, highly detailed prompt suitable for \
Seedance 2.0.

Guidelines:
- Write as natural cinematic prose, not a bulleted list.
- Lead with the subject and action, then build out the scene with \
cinematographic detail.
- Weave in: camera shot, camera movement, lens character, lighting, color \
palette, atmospheric details, and overall style.
- Be specific and sensory. Favor concrete imagery over abstract descriptors.
- Aim for 2-5 sentences. Seedance favors concise but rich prompts; do not pad.
- Avoid contradictions, hedging language, or meta-commentary.

Output ONLY the final prompt text. No preamble, no labels, no explanations."""


def ask_questions() -> dict[str, str]:
    answers: dict[str, str] = {}

    answers["mode"] = questionary.select(
        "Mode:",
        choices=["text-to-video", "image-to-video"],
    ).unsafe_ask()

    answers["duration"] = questionary.select(
        "Duration:",
        choices=["5 seconds", "10 seconds"],
    ).unsafe_ask()

    answers["resolution"] = questionary.select(
        "Resolution:",
        choices=["480p", "720p", "1080p"],
    ).unsafe_ask()

    answers["aspect_ratio"] = questionary.select(
        "Aspect ratio:",
        choices=["16:9 (widescreen)", "9:16 (vertical)", "1:1 (square)", "4:3"],
    ).unsafe_ask()

    answers["subject"] = questionary.text(
        "Subject (who or what is the focus?):",
    ).unsafe_ask()

    answers["action"] = questionary.text(
        "Action (what is happening?):",
    ).unsafe_ask()

    answers["setting"] = questionary.text(
        "Setting / environment:",
    ).unsafe_ask()

    answers["mood"] = questionary.text(
        "Mood / atmosphere (e.g. tense, dreamy, melancholic):",
    ).unsafe_ask()

    answers["camera_shot"] = questionary.select(
        "Camera shot:",
        choices=[
            "extreme wide",
            "wide",
            "medium",
            "medium close-up",
            "close-up",
            "extreme close-up",
            "over-the-shoulder",
            "point-of-view",
        ],
    ).unsafe_ask()

    answers["camera_movement"] = questionary.select(
        "Camera movement:",
        choices=[
            "static (locked-off)",
            "slow pan",
            "tilt",
            "dolly in",
            "dolly out",
            "tracking shot",
            "handheld",
            "crane / boom",
            "zoom in",
            "zoom out",
            "orbit",
        ],
    ).unsafe_ask()

    answers["lighting"] = questionary.select(
        "Lighting:",
        choices=[
            "golden hour",
            "blue hour",
            "harsh midday sun",
            "overcast soft light",
            "neon / practical lights",
            "low-key chiaroscuro",
            "high-key bright",
            "candlelight / firelight",
            "moonlight",
            "studio softbox",
            "other (describe in style)",
        ],
    ).unsafe_ask()

    answers["style"] = questionary.text(
        "Style / aesthetic (e.g. 'cinematic 35mm film, Roger Deakins look', "
        "'anime', 'Wes Anderson symmetry'):",
    ).unsafe_ask()

    return answers


def format_inputs(answers: dict[str, str]) -> str:
    return "\n".join(
        f"- {k.replace('_', ' ').title()}: {v}" for k, v in answers.items()
    )


def generate_prompt(answers: dict[str, str]) -> str:
    client = anthropic.Anthropic()

    user_message = (
        "Generate a Seedance 2.0 video prompt from these inputs:\n\n"
        + format_inputs(answers)
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Error: ANTHROPIC_API_KEY environment variable is not set.",
            file=sys.stderr,
        )
        print(
            "Get a key at https://console.anthropic.com/ then run:",
            file=sys.stderr,
        )
        print("  export ANTHROPIC_API_KEY=sk-ant-...", file=sys.stderr)
        sys.exit(1)

    print("video-prompt-gen — Seedance 2.0 prompt builder\n")

    try:
        answers = ask_questions()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)

    print("\nGenerating prompt...\n")

    try:
        prompt = generate_prompt(answers)
    except anthropic.APIError as e:
        print(f"\nAPI error: {e}", file=sys.stderr)
        sys.exit(1)

    bar = "─" * 60
    print(bar)
    print(prompt)
    print(bar)


if __name__ == "__main__":
    main()
