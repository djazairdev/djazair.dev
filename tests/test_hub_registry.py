"""The Hub registry (ticket #15): projects.yml, its schema, and errors that name the field."""
import io
import json
import re
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hub import miniyaml, registry  # noqa: E402
from hub.__main__ import main  # noqa: E402
from hub.schemacheck import Checker  # noqa: E402

TODAY = date(2026, 10, 6)
GOOD = """\
projects:
  - repository: djazairdev/djazair.dev
    category: tool
    tags: [open-data, arabic, accessibility]
    maintainer_pledge: true
    added: 2026-10-06
  - repository: owner/name
    category: library
    tags: [payments]
    maintainer_pledge: true
    added: 2026-10-01
"""


def problems(text: str) -> list:
    return [(p.line, str(p)) for p in registry.check(text, TODAY).problems]


class MiniYAML(unittest.TestCase):
    def test_the_subset(self):
        value, where = miniyaml.load(
            '# comment\n'
            'projects:\n'
            '- repository: "a/b"   # quoted, with a comment\n'
            "  category: 'it''s'\n"
            '  tags: [x, "y z", \'w\']\n'
            '  flag: true\n'
            '  word: yes\n'
            '  none: ~\n'
            '  n: 42\n'
            '  lang: C#\n'
            '  added: 2026-10-06\n'
            'other:\n'
            '  nested:\n'
            '    - 1\n'
            '    -\n'
            '      k: v\n'
            'empty: []\n')
        self.assertEqual(value, {
            'projects': [{'repository': 'a/b', 'category': "it's", 'tags': ['x', 'y z', 'w'], 'flag': True, 'word': 'yes',
                          'none': None, 'n': 42, 'lang': 'C#', 'added': '2026-10-06'}],
            'other': {'nested': [1, {'k': 'v'}]}, 'empty': []})
        self.assertEqual(where[('projects', 0)], 3)
        self.assertEqual(where[('projects', 0, 'tags')], 5)
        self.assertEqual(where[('other', 'nested', 1, 'k')], 16)

    def test_indented_and_flush_lists_read_the_same(self):
        flush, _ = miniyaml.load('projects:\n- repository: a/b\n  category: app\n')
        indented, _ = miniyaml.load('projects:\n    -   repository: a/b\n        category: app\n')
        self.assertEqual(flush, indented)

    def test_what_is_refused_names_the_line(self):
        cases = {
            'projects:\n\t- a\n': (2, 'tabs'),
            'a: &x 1\n': (1, 'anchors'),
            'a: *x\n': (1, 'aliases'),
            'a: !tag 1\n': (1, 'tags'),
            'a: |\n  text\n': (1, 'block scalars'),
            'a: {b: 1}\n': (1, 'flow mappings'),
            'a: 1\na: 2\n': (2, 'appears twice'),
            'a: "open\n': (1, 'not closed'),
            'a: [1, 2\n': (1, 'close with ]'),
            'a: [[1]]\n': (1, 'inside lists'),
            'a: [1,,2]\n': (1, 'empty item'),
            'a:\n  b: 1\n    c: 2\n': (3, 'indentation'),
            'a: b: c\n': (1, 'quotes'),
            'a: 1\n---\nb: 2\n': (2, 'one document'),
            'just text\n': (1, 'key: value'),
        }
        for text, (line, words) in cases.items():
            with self.subTest(text=text):
                with self.assertRaises(miniyaml.YAMLError) as caught:
                    miniyaml.load(text)
                self.assertEqual(caught.exception.line, line)
                self.assertIn(words, caught.exception.message)

    def test_empty_and_bom(self):
        self.assertEqual(miniyaml.load('# only a comment\n'), (None, {}))
        self.assertEqual(miniyaml.load('\ufeffa: 1\n')[0], {'a': 1})


class Registry(unittest.TestCase):
    def test_a_valid_registry(self):
        result = registry.check(GOOD, TODAY)
        self.assertTrue(result.ok, result.problems)
        self.assertEqual([p.repository for p in result.projects], ['djazairdev/djazair.dev', 'owner/name'])
        self.assertEqual((result.projects[0].owner, result.projects[0].line), ('djazairdev', 2))

    def test_the_file_in_the_repository_passes(self):
        result = registry.load()
        self.assertTrue(result.ok, [str(p) for p in result.problems])

    def test_the_example_in_projects_yml_passes(self):
        text = registry.REGISTRY.read_text()
        example = [re.sub(r'^#   ', '', line) for line in text.splitlines() if line.startswith('#   ')]
        self.assertTrue(example, 'projects.yml shows an example entry')
        result = registry.check('projects:\n' + '\n'.join(example) + '\n', TODAY)
        self.assertTrue(result.ok, [str(p) for p in result.problems])
        self.assertEqual(len(result.projects), 1)

    def test_every_error_names_the_field_and_line(self):
        found = problems(GOOD.replace('category: tool', 'category: framework')
                             .replace('tags: [payments]', 'tags: [payments, space]')
                             .replace('maintainer_pledge: true\n    added: 2026-10-01', 'maintainer_pledge: yes\n    added: 2026-10-01'))
        self.assertEqual([line for line, _ in found], [3, 9, 10])
        self.assertIn('projects[0] (djazairdev/djazair.dev).category: "framework" is not one of: app, library, tool, dataset', found[0][1])
        self.assertIn('projects[1] (owner/name).tags[1]: "space" is not one of', found[1][1])
        self.assertIn('projects[1] (owner/name).maintainer_pledge: must be true, not "yes"', found[2][1])

    def test_missing_and_unknown_fields(self):
        found = problems('projects:\n  - repository: a/b\n    category: app\n    tags: [maps]\n    language: Python\n')
        messages = [m for _, m in found]
        self.assertTrue(any('maintainer_pledge: is missing' in m for m in messages), messages)
        self.assertTrue(any('added: is missing' in m for m in messages), messages)
        self.assertTrue(any('language: is not a field of this entry. The language is read from GitHub' in m for m in messages))

    def test_repository_form(self):
        for bad in ('https://github.com/a/b', 'a', 'a/b/c', '-a/b', 'a-/b', 'a/b.git', 'a/..', 'a b/c', 'a' * 40 + '/b'):
            with self.subTest(repo=bad):
                found = problems(GOOD.replace('owner/name', bad))
                self.assertTrue(found and 'repository' in found[0][1] and 'owner/name' in found[0][1], found)
        for good in ('a/b', 'A-1/x.y_z-2', 'a' * 39 + '/b'):
            with self.subTest(repo=good):
                self.assertEqual(problems(GOOD.replace('owner/name', good)), [])

    def test_tags(self):
        self.assertIn('needs at least 1 item', problems(GOOD.replace('[payments]', '[]'))[0][1])
        self.assertIn('at most 5', problems(GOOD.replace('[payments]', '[payments, maps, health, transport, education, arabic]'))[0][1])
        self.assertIn('listed twice', problems(GOOD.replace('[payments]', '[payments, payments]'))[0][1])
        self.assertEqual(registry.tags()[:2], ['algerian-maintainers', 'arabic'])

    def test_dates(self):
        self.assertIn('not a date', problems(GOOD.replace('2026-10-01', '2026-02-30'))[0][1])
        self.assertIn('not a date', problems(GOOD.replace('2026-10-01', '6 Oct 2026'))[0][1])
        self.assertIn('in the future', problems(GOOD.replace('2026-10-01', '2026-10-09'))[0][1])
        self.assertEqual(problems(GOOD.replace('2026-10-01', '2026-10-07')), [], 'a day ahead is allowed (time zones)')

    def test_a_repository_listed_twice(self):
        found = problems(GOOD.replace('owner/name', 'DjazairDev/Djazair.dev'))
        self.assertEqual(found, [(7, 'projects[1] (DjazairDev/Djazair.dev).repository: DjazairDev/Djazair.dev is already '
                                    'listed as projects[0].')])

    def test_the_top_level(self):
        self.assertIn('empty', problems('# nothing\n')[0][1])
        self.assertIn('projects: is missing', problems('items: []\n')[0][1])
        self.assertIn('expected a list', problems('projects: owner/name\n')[0][1])
        self.assertEqual(problems('projects:\n  - repository: [\n'), [(2, 'a [ list must close with ] on the same line')])


class Schema(unittest.TestCase):
    def test_unsupported_keywords_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'oneOf'):
            Checker({'type': 'object', 'properties': {'a': {'oneOf': [{'type': 'string'}]}}})

    def test_the_schema_is_valid_json_schema_shape(self):
        schema = json.loads(registry.SCHEMA.read_text())
        self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        Checker(schema)
        self.assertEqual(schema['$defs']['project']['properties']['category']['enum'], ['app', 'library', 'tool', 'dataset'])


class CommandLine(unittest.TestCase):
    def run_cli(self, text, actions=False):
        path = ROOT / 'tests' / '__pycache__' / 'projects-test.yml'
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)
        self.addCleanup(path.unlink)
        out = io.StringIO()
        env = {'GITHUB_ACTIONS': 'true'} if actions else {}
        with mock.patch.dict('os.environ', env), redirect_stdout(out), \
                mock.patch.object(registry, 'date', wraps=date) as fake:
            fake.today.return_value = TODAY
            code = main(['check-registry', str(path)])
        return code, out.getvalue()

    def test_valid(self):
        code, out = self.run_cli(GOOD)
        self.assertEqual(code, 0)
        self.assertIn('2 projects, valid', out)

    def test_invalid_fails_with_an_annotation_on_the_line(self):
        code, out = self.run_cli(GOOD.replace('category: tool', 'category: framework'), actions=True)
        self.assertEqual(code, 1)
        self.assertRegex(out, r'::error file=.*projects-test\.yml,line=3,title=projects\.yml::projects\[0\] '
                              r'\(djazairdev/djazair\.dev\)\.category')
        self.assertIn('1 problem in', out)

    def test_ci_checks_the_registry(self):
        self.assertIn('python -m hub check-registry', (ROOT / '.github' / 'workflows' / 'ci.yml').read_text())


if __name__ == '__main__':
    unittest.main()
