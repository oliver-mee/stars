#!/usr/bin/env python3
"""Read public stars via gh; reconcile classifications before replacing the export."""
import json
from pathlib import Path
import subprocess

from classify import reconcile
from generate import scrub

ROOT = Path(__file__).resolve().parents[1]


def fetch_public():
    # The public user endpoint excludes private stars even with a privileged token.
    login = subprocess.check_output(['gh', 'api', 'user', '--jq', '.login'], text=True).strip()
    pages = json.loads(subprocess.check_output([
        'gh', 'api', '--paginate', '--slurp',
        f'users/{login}/starred?per_page=100',
        '-H', 'Accept: application/vnd.github+json',
    ], text=True))
    public = {}
    for page in pages:
        for repo in page:
            if repo.get('private') is not False or repo.get('visibility', 'public') != 'public':
                continue
            item = {key: repo.get(key) for key in
                    ('full_name', 'node_id', 'description', 'language', 'topics')}
            item.update(private=False, stars=repo['stargazers_count'], pushed=repo['pushed_at'])
            public[item['node_id']] = item
    return sorted(public.values(), key=lambda s: s['full_name'].casefold())


def main():
    old = json.loads((ROOT / 'data/stars-export.json').read_text())
    previous = json.loads((ROOT / 'data/classifications.json').read_text())
    stars = fetch_public()  # All pages must succeed before writing anything.
    if not stars and old:
        raise RuntimeError('Refusing to replace a populated export with an empty response')
    classifications = reconcile(stars, previous, old)
    payloads = {'stars-export': stars, 'classifications': classifications}
    texts = {name: json.dumps(value, indent=1, sort_keys=True) + '\n'
             for name, value in payloads.items()}
    for name, text in texts.items():
        scrub(text, name)
    for name, text in texts.items():
        (ROOT / f'data/{name}.json').write_text(text)
    print(f'PUBLIC EXPORTED: {len(stars)}')


if __name__ == '__main__':
    main()
