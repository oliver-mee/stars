#!/usr/bin/env python3
"""Create GitHub Star Lists and file all classified repos into them.

Usage:
  python3 scripts/apply.py --create-lists   # create missing lists, save data/list-ids.json
  python3 scripts/apply.py --file-all       # file every repo (resumable via data/applied.json)
  python3 scripts/apply.py --file-sample N  # file first N repos (dry-test)

Semantics: updateUserListsForItem REPLACES membership, so existing-list
memberships (Agent Memory, AI Essentials, My stack) are preserved.
"""
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

BROAD_TITLES = {
    "skills-plugins": "Skills & Plugins",
    "mcp-servers": "MCP Servers",
    "harness": "Agent Harnesses",
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
NARROW = ["openclaw", "codex", "opencode", "obsidian", "hermes",
          "shadcn", "local-first", "context-engineering"]

# repos already sitting in the 3 pre-existing lists -> keep those memberships
PRESERVE = {
    "mem0ai/mem0": ["UL_kwDOBh6rac4AhAON"],
    "vincentkoc/tokenjuice": ["UL_kwDOBh6rac4AgkPR", "UL_kwDOBh6rac4AgkPJ"],
}


def gql(query, **variables):
    payload = json.dumps({"query": query, "variables": variables})
    for attempt in range(4):
        p = subprocess.run(["gh", "api", "graphql", "--input", "-"],
                           input=payload, capture_output=True, text=True)
        try:
            body = json.loads(p.stdout or "{}")
        except json.JSONDecodeError:
            body = {}
        if not body.get("errors"):
            return body
        msg = json.dumps(body["errors"])[:200]
        if "rate limit" in msg.lower() or "secondary" in msg.lower():
            time.sleep(5 * (attempt + 1))
            continue
        raise RuntimeError(msg)
    raise RuntimeError("rate-limited repeatedly")


def create_lists():
    ids = {}
    if __name__ != "__main__":
        return ids
    try:
        ids = json.load(open("data/list-ids.json"))
        print("loaded", len(ids), "existing list ids")
    except FileNotFoundError:
        pass
    have = set(ids)
    for key, title in list(BROAD_TITLES.items()) + [(n, n) for n in NARROW]:
        if key in have:
            continue
        body = gql(
            "mutation($name:String!){createUserList(input:{name:$name}){list{id name}}}",
            name=title)
        lid = body["data"]["createUserList"]["list"]["id"]
        ids[key] = lid
        print("created", title, lid)
        time.sleep(0.3)
        json.dump(ids, open("data/list-ids.json", "w"), indent=1)
    return ids


def file_all(limit=None):
    ids = json.load(open("data/list-ids.json"))
    c = json.load(open("data/classifications.json"))
    try:
        done = set(json.load(open("data/applied.json")))
    except FileNotFoundError:
        done = set()
    names = [n for n in sorted(c) if n not in done]
    if limit:
        names = names[:limit]
    print("to file:", len(names))

    def one(name):
        v = c[name]
        lids = [ids[b] for b in v["lists"]] + [ids[n] for n in v["narrow"]]
        lids += PRESERVE.get(name, [])
        # node_id lookup from export
        gql("mutation($itemId:ID!,$listIds:[ID!]!){updateUserListsForItem(input:{itemId:$itemId,listIds:$listIds}){clientMutationId}}",
            itemId=NODE[name], listIds=lids)
        return name

    ok, fail = [], []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, name in enumerate(names):
            try:
                ex.submit(one, name).result()
                ok.append(name)
            except Exception as e:  # noqa: BLE001
                fail.append([name, str(e)[:150]])
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(names)} done, {len(fail)} failed")
                json.dump(sorted(done | set(ok)), open("data/applied.json", "w"))
                time.sleep(2)
    json.dump(sorted(done | set(ok)), open("data/applied.json", "w"))
    json.dump(fail, open("data/apply-failures.json", "w"), indent=1)
    print("OK:", len(ok), "FAIL:", len(fail))


NODE = {}


if __name__ == "__main__":
    NODE = {s["full_name"]: s["node_id"]
            for s in json.load(open("data/stars-export.json")) if not s.get("private")}
    if "--create-lists" in sys.argv:
        create_lists()
    elif "--file-sample" in sys.argv:
        n = int(sys.argv[sys.argv.index("--file-sample") + 1])
        file_all(limit=n)
    elif "--file-all" in sys.argv:
        file_all()
    else:
        print("pass --create-lists, --file-sample N, or --file-all")
