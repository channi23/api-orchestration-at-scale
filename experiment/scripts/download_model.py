"""Download the frozen GGUF and pin its revision + sha256 into config/model.json (first run only)."""
import hashlib, json, os
from huggingface_hub import HfApi, hf_hub_download

EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg_path = os.path.join(EXP, "config", "model.json")
cfg = json.load(open(cfg_path))
rev = cfg["hf_revision"]
if rev.startswith("TO_BE"):
    rev = HfApi().model_info(cfg["hf_repo"]).sha
path = hf_hub_download(cfg["hf_repo"], cfg["gguf_file"], revision=rev, local_dir=os.path.join(EXP, "models"))
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        h.update(chunk)
digest = h.hexdigest()
if cfg["gguf_sha256"].startswith("TO_BE"):
    cfg["hf_revision"], cfg["gguf_sha256"] = rev, digest
    json.dump(cfg, open(cfg_path, "w"), indent=2)
    print("pinned", rev, digest)
else:
    assert digest == cfg["gguf_sha256"], f"GGUF sha256 mismatch: {digest} != {cfg['gguf_sha256']}"
    print("verified", rev, digest)
print(path)
