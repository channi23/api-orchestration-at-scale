"""Prompt construction. Identical wording for every representation; only {tools} differs."""
from __future__ import annotations

import hashlib

import render

SYSTEM_TEMPLATE = (
    "You are an assistant that completes a user's request by calling exactly one tool.\n"
    "Available tools:\n\n{tools}\n\n"
    "Respond with only a JSON object of the form {{\"tool\": \"<tool name>\", \"arguments\": {{...}}}}. "
    "The arguments must follow the selected tool's input parameters. Do not include any other text."
)
ARGGEN_SUFFIX = "\n\nUse the tool \"{tool_name}\"."


def system_prompt(arm: str, tool_ids: list[str]) -> str:
    return SYSTEM_TEMPLATE.format(tools=render.render_catalog(arm, tool_ids))


def messages_select(arm: str, presentation_order: list[str], task: dict) -> list[dict]:
    return [{"role": "system", "content": system_prompt(arm, presentation_order)},
            {"role": "user", "content": task["prompt"]}]


def messages_arggen(arm: str, task: dict) -> list[dict]:
    """Argument-generation family: the tool is fixed (only the gold tool is shown and named)."""
    return [{"role": "system", "content": system_prompt(arm, [task["tool_id"]])},
            {"role": "user", "content": task["prompt"] + ARGGEN_SUFFIX.format(tool_name=task["tool_name"])}]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
