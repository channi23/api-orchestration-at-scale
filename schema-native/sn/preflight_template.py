"""Check that training and inference feed the model the same text. Run this on the Mac BEFORE training.

MLX-LM's chat dataset renders ``messages`` with the tokenizer's chat template using default
arguments. Inference in this project disables Qwen3 thinking (``enable_thinking: false``). If the
two renderings differ before the answer starts, the adapter is trained on a prefix it never sees at
inference time and results are not interpretable.

The check: render (system, user, assistant) the way training does, render (system, user) + generation
prompt the way inference does, and require the inference prompt to be an exact prefix of the
training text. It also prints the tokens that carry loss under ``--mask-prompt``.

usage: python -m sn.preflight_template --model Qwen/Qwen3-1.7B
Needs: transformers (installed with mlx-lm). Downloads only the tokenizer files.
NOT RUN in the authoring environment (no access to the model hub there).
"""
from __future__ import annotations

import argparse
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-1.7B")
    a = ap.parse_args()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.model)
    msgs = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "USER"},
            {"role": "assistant", "content": '{"tool": "t", "arguments": {}}'}]
    train_text = tok.apply_chat_template(msgs, tokenize=False)
    mask_offset_text = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True)
    infer_text = tok.apply_chat_template(msgs[:-1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    print("--- training text (tail)\n" + repr(train_text[-140:]))
    print("--- loss starts after (tail)\n" + repr(mask_offset_text[-60:]))
    print("--- inference prompt (tail)\n" + repr(infer_text[-60:]))
    ok_prefix = train_text.startswith(infer_text)
    ok_mask = train_text.startswith(mask_offset_text)
    print(f"\ninference prompt is a prefix of the training text: {ok_prefix}")
    print(f"mask offset is a prefix of the training text:       {ok_mask}")
    if not (ok_prefix and ok_mask):
        print("\nMISMATCH. Do not train. Fix by rendering training rows yourself as {'text': ...} with the "
              "inference template (enable_thinking=False) and the answer appended, then train on the text dataset.")
        sys.exit(1)
    print("\nOK: the adapter will be trained on the same prefix it sees at inference time.")


if __name__ == "__main__":
    main()
