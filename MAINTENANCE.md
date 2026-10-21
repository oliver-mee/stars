# Maintaining the public stars archive

Requires Python 3 (standard library only) and `gh` authenticated to the account whose stars you intend to export. Check `gh api user --jq .login` first.

```sh
git switch -c review/refresh-stars
python3 scripts/refresh.py
# Review new classifications in the diff; edit data/classifications.json as needed.
python3 scripts/classify.py
python3 scripts/generate.py
python3 -m unittest discover -s scripts -p 'test_*.py' -v
git diff --check
git diff --stat
```

`refresh.py` uses only read requests through `gh`: `/user` to identify the active account, then the paginated **public** `/users/{login}/starred` endpoint. It retains only allowlisted public fields, filters private/unknown visibility, and scrubs both JSON payloads before writing. API failures abort without replacing the existing export. An empty response cannot silently erase an existing archive. The source export itself must never include private repositories, not just the generated lists.

Classifications are reconciled by stable `node_id`, using the old export to migrate legacy records that did not store IDs. Renames/transfers retain curated `lists`, `narrow`, and `why`; star counts, language and pushed timestamps refresh. Repositories absent from the public snapshot are pruned, including repos that are no longer public. Existing curated fields win over keyword rules and `MANUAL` entries. Edit classifications directly to change an existing filing; `MANUAL` seeds only new entries. New records use the existing rules, with a printed review warning for unmatched fallbacks. Review all new entries: substring rules can overmatch descriptions and topics.

Generation validates export/classification identity agreement and public flags and scrubs the source data and rendered Markdown. The README orders buckets by descending repository count, with alphabetical title ordering for ties. Keep the index reader-facing: no maintenance section, scripts pointer or narrow-tags section. Do not render narrow-tag chips on bucket pages either: the archive has no tag-filtering UI. Preserve `narrow` in source data for compatibility with the separate native-list tooling; removing public tag labels must not mutate GitHub Lists or checkpoints. The denylist is defense in depth, not a substitute for the public-only source endpoint. Repeated classification/generation with unchanged inputs must produce byte-identical files. A later network refresh can legitimately change stars and pushed timestamps.

`data/applied.json`, `data/apply-failures.json`, and `data/list-ids.json` are historical native-list checkpoints, **not** inputs to the archive refresh. They are deliberately left untouched, including old names. `scripts/apply.py` is a separate, mutating operation: do not run it as part of refresh or tests. In particular, its `--file-sample` option performs real mutations despite the old “dry-test” label. Native GitHub Lists, pushes and merges need separate explicit approval.

Review the diff before committing. Do not rewrite published history as part of routine refresh; any historical sensitive-data cleanup is a separate coordinated operation.
