#!/usr/bin/env python3
"""Generate the public stars repo from data/classifications.json.

Outputs: README.md (index) + lists/<bucket>.md (one awesome-list per bucket).
Runs a denylist scrub over all generated text; fails loudly on any hit.
Private repos never reach this stage (filtered in classify.py).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TITLES = {
    "skills-plugins": "Skills & Plugins",
    "mcp-servers": "MCP Servers",
    "harness": "Agent Harnesses & Orchestration",
    "memory": "Agent Memory & Knowledge",
    "models": "AI Models & Inference",
    "devtools": "Devtools & CLI",
    "automation": "Automation & Workflows",
    "selfhost": "Self-Hosted & Infra",
    "design": "Design & Frontend",
    "writing": "Writing & Content",
    "voice": "Voice & Audio",
    "mobile-desktop": "Mobile & Desktop",
    "privacy": "Privacy & Security",
    "learning": "Learning & Guides",
    "finance": "Finance & Ops",
    "fde": "FDE",
    "collections": "Collections",
}

DENY = [
    "prefacecontent", "preface-ai", "preface.ai", "ynf", "dorsett",
    "tailf8a0db", "ts.net", "magbrain", "/home/", "100.115.148",
    "100.82.198", "100.95.46", "gho_", "ghp_", "sk-ant-", "xoxb-",
    "xoxp-", "AKIA", "-----BEGIN",
]

BROAD_ORDER = list(TITLES)


def scrub(text, where):
    low = text.lower()
    hits = [d for d in DENY if d.lower() in low]
    if hits:
        print(f"SCRUB FAIL in {where}: {hits}")
        sys.exit(1)


def main():
    c = json.loads((ROOT / "data/classifications.json").read_text())
    stars = json.loads((ROOT / "data/stars-export.json").read_text())
    if any(s.get('private') is not False for s in stars):
        raise ValueError('Export must contain only explicitly public repos')
    if {s['full_name']: s['node_id'] for s in stars} != {n: v['node_id'] for n, v in c.items()}:
        raise ValueError('Export and classifications disagree; run refresh.py')
    scrub(json.dumps(stars), 'export')
    scrub(json.dumps(c), 'classifications')
    by_bucket = {b: [] for b in BROAD_ORDER}
    for name in sorted(c):
        v = c[name]
        for b in v["lists"]:
            by_bucket[b].append((name, v))

    for b in BROAD_ORDER:
        lines = [f"# {TITLES[b]}", "",
                 f"{len(by_bucket[b])} starred repos. File a PR to fix a miscategorisation.", ""]
        for name, v in by_bucket[b]:
            meta = " · ".join(x for x in [
                f"★{v['stars']}" if v.get("stars") else None,
                v.get("language") or None,
            ] if x)
            lines.append(f"- [{name}](https://github.com/{name}) ({meta}) — {v['why']}")
            if v["narrow"]:
                lines[-1] += f" [`{'` `'.join(v['narrow'])}`]"
        lines += ["", "_Generated from star export — see data/. Regenerate, don't hand-edit._", ""]
        text = "\n".join(line.rstrip() for line in lines)
        scrub(text, f"lists/{b}.md")
        (ROOT / f"lists/{b}.md").write_text(text)

    idx = ["# stars", "",
           "My GitHub stars, filed into lists. One repo can live in several — broad buckets plus narrow tags.",
           "", "## Buckets", ""]
    for b in BROAD_ORDER:
        idx.append(f"- [{TITLES[b]}](lists/{b}.md) ({len(by_bucket[b])})")
    idx += ["", "## Narrow tags",
            "Cross-cutting: `openclaw` `codex` `opencode` `obsidian` `hermes` `shadcn` `local-first` `context-engineering` `fde`.",
            "", "## Maintenance", "See [MAINTENANCE.md](MAINTENANCE.md) for the public-only refresh and review workflow.",
            "", "_Generated — see scripts/. Private starred repos are excluded by policy._", ""]
    readme = "\n".join(idx)
    scrub(readme, "README.md")
    (ROOT / "README.md").write_text(readme)
    print("WROTE README +", len(BROAD_ORDER), "lists. Scrub clean.")


if __name__ == "__main__":
    main()
