#!/usr/bin/env python3
"""Classify starred repos into broad buckets + narrow tags.

Input:  data/stars-export.json (public-only export via scripts/refresh.py)
Output: data/classifications.json {full_name: {lists:[broad...], narrow:[...], why, stars, language, pushed}}

Rules:
- Private repos are EXCLUDED entirely (never enter the public repo).
- why-lines come from upstream descriptions only (public text), truncated.
- Manual overrides cover repos the keyword rules miss.
"""
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BROAD_ORDER = [
    "skills-plugins", "mcp-servers", "harness", "memory", "models",
    "devtools", "automation", "selfhost", "design", "writing",
    "voice", "mobile-desktop", "privacy", "learning", "finance",
    "fde", "collections",
]

RULES = [
    ("skills-plugins", ["skill", "plugin", "slash-command", "slashcommand", "command-"]),
    ("mcp-servers", ["mcp"]),
    ("harness", ["harness", "orchestrat", "multi-agent", "multiagent", "swarm", "agent-loop", "agentic-workflow"]),
    ("memory", ["memory", "second-brain", "knowledge-graph", "knowledgegraph", "rag", "recall", "embed", "vector", "context-"]),
    ("models", ["deepseek", "qwen", "llama", "mistral", "inference", "gguf", "ollama", "vllm", "benchmark", "leaderboard", "-7b", "-70b", "moe"]),
    ("devtools", ["cli", "terminal", "tui", "shell", "neovim", "vim", "tmux", "lsp", "lint", "formatter", "git-", "github-", "diff", "editor", "ide", "debug"]),
    ("automation", ["automation", "workflow", "n8n", "cron", "schedul", "scrap", "crawl", "bot-", "-bot", "telegram", "whatsapp", "notification"]),
    ("selfhost", ["self-host", "selfhost", "homelab", "docker", "monitor", "observab", "uptime", "auth", "proxy", "tailscale", "ansible", "backup", "nas", "server", "deploy", "ci-", "cd-", "k8s", "kubernetes"]),
    ("design", ["shadcn", "design", "figma", "frontend", "react", "tailwind", "motion", "landing", "portfolio", "theme", "icon", "font", "css", "component-"]),
    ("writing", ["blog", "writing", "markdown", "notion", "cms", "docs-", "-docs", "newsletter", "essay", "book", "readwise", "rss", "read-it-later"]),
    ("voice", ["speech-to-text", "text-to-speech", "tts", "stt", "voice", "audio", "whisper", "podcast", "music", "sound", "transcri"]),
    ("mobile-desktop", ["macos", "mac-", "ios", "android", "tauri", "electron", "desktop", "windows", "linux-", "-linux", "ubuntu", "app-"]),
    ("privacy", ["privacy", "security", "audit", "vuln", "pentest", "encrypt", "password", "secur", "malware", "adblock", "firewall"]),
    ("collections", ["awesome-", "curated", "collection", "list-of", "list_of"]),
    ("learning", ["learn", "course", "tutorial", "academy", "guide", "handbook", "roadmap", "textbook", "cookbook"]),
    ("finance", ["finance", "budget", "wealth", "invoice", "trading", "crypto", "money", "accounting", "bank"]),
    ("fde", ["fde", "forward-deploy", "palantir", "engagement", "field-guide", "playbook"]),
]

NARROW = [
    ("openclaw", ["openclaw"]),
    ("codex", ["codex"]),
    ("opencode", ["opencode"]),
    ("obsidian", ["obsidian"]),
    ("hermes", ["hermes"]),
    ("shadcn", ["shadcn"]),
    ("local-first", ["local-first", "localfirst"]),
    ("context-engineering", ["context-engineering", "contextengineering"]),
]

# full_name -> [broad buckets] for repos the rules miss or misfile
MANUAL = {
    "pingdotgg/t3code": ["devtools"],
    "kunchenguid/firstmate": ["harness"],
    "lalalune/outreachr": ["finance"],
    "anomalyco/opencode": ["harness"],
    "anthropics/claude-code-action": ["devtools"],
    "dexloom/vibe-kanban-indie": ["harness"],
    "BloopAI/vibe-kanban": ["harness"],
    "zbezj/HEU_KMS_Activator": ["devtools"],
    "api-evangelist/google-appsheet": ["devtools"],
    "excalidraw/excalidraw": ["design"],
    "vercel-labs/fx": ["harness"],
    "teralomaniac/clewd": ["models"],
    "h-a-s-k/clewd": ["models"],
    "block/buzz": ["harness"],
    "haierkeys/fast-note-sync-service": ["selfhost"],
    "blacksmithgu/datacore": ["memory"],
    "botiverse/agent-vault": ["privacy"],
    "Abloatai/ablo": ["harness"],
    "calibrain/shelfmark": ["selfhost"],
    "openchamber/openchamber": ["harness"],
    "mohankumarpaluru/oracle-freetier-instance-creation": ["selfhost"],
    "iiroak/Kindle-Filler-Disk": ["mobile-desktop"],
    "ccusage/ccusage": ["devtools"],
    "anomalyco/models.dev": ["models"],
    "garrytan/gbrain": ["memory"],
    "nesquena/hermes-webui": ["harness"],
    "NousResearch/hermes-agent": ["harness"],
    "borq168/radar-forge": ["automation"],
    "ericshwu/PolarQuant": ["models"],
    "chenglou/pretext": ["devtools"],
    "xrsl/nabcv": ["writing"],
    "rekordcloud/openkeyscan-analyzer": ["voice"],
    "techartdev/OpenClawHomeAssistantIntegration": ["automation"],
    "Rbillon59/home-assistant-addons": ["automation"],
    "dinoBOLT/Gemini-Watermark-Remover": ["privacy"],
    "bmad-code-org/BMAD-METHOD": ["harness"],
    "marchoag/Claude-Code-Setup-Wizard-MD": ["skills-plugins"],
    "o-gi/claude-code-commands": ["skills-plugins"],
    "eyaltoledano/claude-task-master": ["skills-plugins"],
    "OpenCut-app/OpenCut": ["design"],
    "browser-use/video-use": ["design"],
    "modelscope/3D-Speaker": ["voice"],
    "jgraph/drawio": ["design"],
    "GurYN/vibe-slides": ["design"],
    "pipipi-pikachu/PPTist": ["design"],
    "wuwentao/midea_ac_lan": ["automation"],
    "plastic-labs/paperclip-honcho": ["memory"],
    "NousResearch/hermes-paperclip-adapter": ["harness"],
    "y0usaf/jev-lm": ["models"],
    "Lakr233/vphone-cli": ["mobile-desktop"],
    "Gitlawb/openclaude": ["harness"],
    "MoonshotAI/kimi-cli": ["harness"],
    "stablyai/orca": ["harness", "mobile-desktop"],
    "postgres/postgres": ["selfhost"],
    "syncthing/syncthing": ["selfhost"],
    "vercel-labs/portless": ["selfhost"],
    "bitwarden/clients": ["privacy"],
}


def blob(s):
    return " ".join([
        s.get("full_name") or "",
        s.get("description") or "",
        " ".join(s.get("topics") or []),
    ]).lower().replace("_", "-").replace(" ", "-")


def reconcile(stars, previous, old_stars):
    """Keep curated fields by stable identity; refresh metadata and prune absent stars."""
    old_names = {s['node_id']: s['full_name'] for s in old_stars
                 if s.get('private') is False}
    previous_ids = {v['node_id']: name for name, v in previous.items() if v.get('node_id')}
    out = {}
    unmatched = []
    for s in stars:
        if s.get("private") is not False:
            continue  # excluded entirely, never enters the public repo
        name = s["full_name"]
        b = blob(s)
        if name in MANUAL:
            broad = MANUAL[name]
        else:
            broad = [n for n, ks in RULES if any(k in b for k in ks)]
            if not broad:
                if name not in previous and s["node_id"] not in previous_ids and s["node_id"] not in old_names:
                    unmatched.append(name)
                broad = ["devtools"]  # visible fallback, fixed at review
        narrow = [n for n, ks in NARROW if any(k in b for k in ks)]
        why = (s.get("description") or "").strip().split("\n")[0][:160] or "No upstream description."
        old_name = previous_ids.get(s['node_id'], old_names.get(s['node_id'], name))
        curated = previous.get(old_name)
        if curated and curated.get('node_id', s['node_id']) != s['node_id']:
            curated = None  # A reused repository name is not the same repository.
        out[name] = {
            "node_id": s['node_id'],
            "lists": curated['lists'] if curated else [x for x in BROAD_ORDER if x in broad],
            "narrow": curated['narrow'] if curated else narrow,
            "why": curated['why'] if curated else why,
            "stars": s.get("stars"),
            "language": s.get("language"),
            "pushed": s.get("pushed"),
        }

    cnt = collections.Counter()
    for v in out.values():
        for x in v["lists"]:
            cnt[x] += 1
    print("CLASSIFIED:", len(out))
    for k in BROAD_ORDER:
        print(f"  {cnt[k]:3d}  {k}")
    print("NARROW:", dict(sum((collections.Counter({n: 1 for n in v["narrow"]}) for v in out.values()), collections.Counter())))
    print("RULE-UNMATCHED (fallback, needs review):", len(unmatched))
    for name in unmatched:
        if name not in previous:
            print("  REVIEW:", name)
    return out


def main():
    stars = json.loads((ROOT / 'data/stars-export.json').read_text())
    path = ROOT / 'data/classifications.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    out = reconcile(stars, previous, stars)
    from generate import scrub
    text = json.dumps(out, indent=1, sort_keys=True) + '\n'
    scrub(text, str(path.relative_to(ROOT)))
    path.write_text(text)


if __name__ == "__main__":
    main()
