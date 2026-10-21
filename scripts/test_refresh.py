"""Offline regression tests: python3 -m unittest discover -s scripts -p 'test_*.py'."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest
import tempfile
import refresh
from unittest.mock import patch

from classify import BROAD_ORDER, reconcile
from refresh import fetch_public


def repo(name='example/tool', node='R_1', **kw):
    return dict(full_name=name, node_id=node, private=False,
                description='CLI tool', stars=2, language='Python', pushed='today', **kw)


def run(*args):
    with contextlib.redirect_stdout(io.StringIO()):
        return reconcile(*args)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.old = repo()
        self.curated = {'example/tool': dict(lists=['finance'], narrow=['codex'], why='Curated')}

    def test_preserves_manual_and_updates_metadata(self):
        out = run([self.old], self.curated, [self.old])['example/tool']
        for field in ('lists', 'narrow', 'why'):
            self.assertEqual(out[field], self.curated['example/tool'][field])
        self.assertEqual(out['stars'], 2)

    def test_rename_by_node_id_legacy(self):
        renamed = repo('new/name')
        self.assertEqual(run([renamed], self.curated, [self.old])['new/name']['lists'], ['finance'])

    def test_rename_by_stored_node_id(self):
        self.curated['example/tool']['node_id'] = 'R_1'
        self.assertEqual(run([repo('new/name')], self.curated, [])['new/name']['why'], 'Curated')

    def test_prunes_unstarred(self):
        self.assertEqual(run([], self.curated, [self.old]), {})

    def test_excludes_private_and_unknown_visibility(self):
        private = dict(self.old, private=True)
        unknown = dict(self.old)
        del unknown['private']
        self.assertEqual(run([private, unknown], self.curated, [self.old]), {})

    def test_reused_name_does_not_keep_curated_fields(self):
        self.curated['example/tool']['node_id'] = 'R_old'
        out = run([self.old], self.curated, [self.old])
        self.assertEqual(out['example/tool']['lists'], ['devtools'])

    def test_reconciliation_idempotent(self):
        first = run([self.old], self.curated, [self.old])
        self.assertEqual(first, run([self.old], first, [self.old]))

    def test_fetch_projects_only_public_allowlisted_fields(self):
        public = dict(self.old, stargazers_count=3, pushed_at='now', secret='never serialize')
        private = dict(public, private=True, full_name='example/hidden')
        with patch('refresh.subprocess.check_output', side_effect=['example\n', json.dumps([[public], [private]])]) as mock:
            out = fetch_public()
        self.assertEqual(len(out), 1)
        self.assertNotIn('secret', out[0])
        self.assertIn('users/example/starred?per_page=100', mock.call_args.args[0])

    def test_fetch_failure_propagates(self):
        with patch('refresh.subprocess.check_output', side_effect=subprocess.CalledProcessError(1, 'gh')):
            with self.assertRaises(subprocess.CalledProcessError):
                fetch_public()

    def test_refresh_pipeline_idempotent_and_failure_no_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir()
            export = root / 'data/stars-export.json'
            classifications = root / 'data/classifications.json'
            export.write_text(json.dumps([self.old]))
            classifications.write_text(json.dumps(self.curated))
            def snapshot():
                return export.read_bytes(), classifications.read_bytes()
            with patch.object(refresh, 'ROOT', root), patch.object(refresh, 'fetch_public', return_value=[repo('new/name')]):
                with contextlib.redirect_stdout(io.StringIO()):
                    refresh.main()
                    first = snapshot()
                    refresh.main()
                self.assertEqual(first, snapshot())
            with patch.object(refresh, 'ROOT', root), patch.object(refresh, 'fetch_public', side_effect=RuntimeError('network failure')):
                with self.assertRaises(RuntimeError):
                    refresh.main()
                self.assertEqual(first, snapshot())
            with patch.object(refresh, 'ROOT', root), patch.object(refresh, 'fetch_public', return_value=[]):
                with self.assertRaises(RuntimeError):
                    refresh.main()
                self.assertEqual(first, snapshot())

    def test_checked_in_data_consistent(self):
        root = Path(__file__).resolve().parents[1]
        stars = json.loads((root / 'data/stars-export.json').read_text())
        c = json.loads((root / 'data/classifications.json').read_text())
        self.assertTrue(all(s['private'] is False for s in stars))
        self.assertEqual(len(stars), len({s['node_id'] for s in stars}))
        self.assertEqual({s['full_name']: s['node_id'] for s in stars}, {n: v['node_id'] for n, v in c.items()})
        self.assertTrue(all(v['lists'] and set(v['lists']) <= set(BROAD_ORDER) for v in c.values()))


if __name__ == '__main__':
    unittest.main()
