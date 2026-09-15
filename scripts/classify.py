#!/usr/bin/env python3
"""Classify starred repos into broad buckets + narrow tags.

Input:  data/stars-export.json (gh api /user/starred, includes private flag)
Output: data/classifications.json {full_name: {lists:[broad...], narrow:[...], why, stars, language, pushed}}

Rules:
- Private repos are EXCLUDED entirely (never enter the public repo).
- why-lines come from upstream descriptions only (public text), truncated.
- Manual overrides cover repos the keyword rules miss.
"""
import json
import collections

BROAD_ORDER = [
    "skills-plugins", "mcp-servers", "harness", "memory", "models",
    "devtools", "automation", "selfhost", "design", "writing",
    "voice", "mobile-desktop", "privacy", "learning", "finance",
    "work-fde", "collections",
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
    ("work-fde", ["fde", "forward-deploy", "consult", "palantir", "engagement", "enterprise", "field-guide", "playbook"]),
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
    ("fde", ["fde", "forward-deploy", "forwarddeploy"]),
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
}


def blob(s):
    return " ".join([
        s.get("full_name") or "",
        s.get("description") or "",
        " ".join(s.get("topics") or []),
    ]).lower().replace("_", "-").replace(" ", "-")


def main():
    stars = json.load(open("data/stars-export.json"))
    out = {}
    unmatched = []
    for s in stars:
        if s.get("private"):
            continue  # excluded entirely, never enters the public repo
        name = s["full_name"]
        b = blob(s)
        if name in MANUAL:
            broad = MANUAL[name]
        else:
            broad = [n for n, ks in RULES if any(k in b for k in ks)]
            if not broad:
                unmatched.append(name)
                broad = ["devtools"]  # visible fallback, fixed at review
        narrow = [n for n, ks in NARROW if any(k in b for k in ks)]
        why = (s.get("description") or "").strip().split("\n")[0][:160] or "No upstream description."
        out[name] = {
            "lists": [x for x in BROAD_ORDER if x in broad],
            "narrow": narrow,
            "why": why,
            "stars": s.get("stars"),
            "language": s.get("language"),
            "pushed": s.get("pushed"),
        }
    json.dump(out, open("data/classifications.json", "w"), indent=1, sort_keys=True)
    cnt = collections.Counter()
    for v in out.values():
        for x in v["lists"]:
            cnt[x] += 1
    print("CLASSIFIED:", len(out))
    for k in BROAD_ORDER:
        print(f"  {cnt[k]:3d}  {k}")
    print("NARROW:", dict(sum((collections.Counter({n: 1 for n in v["narrow"]}) for v in out.values()), collections.Counter())))
    print("RULE-UNMATCHED (fallback, needs review):", len(unmatched))


if __name__ == "__main__":
    main()
