"""The documentation: every relative link in the READMEs and docs/ leads to a file that exists,
and every #anchor to a heading in it, as GitHub shows them."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = sorted([*ROOT.glob('*.md'), *ROOT.glob('*/README.md'), *ROOT.glob('docs/*.md'), ROOT / 'site' / 'README.md'])
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
HEADING = re.compile(r'^#{1,6} +(.+?) *#*$')
FENCE = re.compile(r'^ *(```|~~~)')


def prose(path: Path):
    """The lines of a Markdown file outside code blocks."""
    fenced = False
    for line in path.read_text('utf-8').splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            yield line


def anchors(path: Path) -> set:
    """The anchors GitHub gives the headings of a Markdown file."""
    found, seen = set(), {}
    for line in prose(path):
        m = HEADING.match(line)
        if not m:
            continue
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', m.group(1))      # a link keeps its text
        slug = re.sub(r'[^\w\- ]', '', text.replace('`', '').lower()).replace(' ', '-')
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        found.add(slug if n == 0 else f'{slug}-{n}')
    return found


class Links(unittest.TestCase):
    def test_docs_are_found(self):
        names = {p.relative_to(ROOT).as_posix() for p in DOCS}
        self.assertTrue({'README.md', 'CONTRIBUTING.md', 'docs/launch.md', 'docs/reports.md', 'site/README.md'} <= names)

    def test_relative_links_resolve(self):
        problems = []
        for doc in DOCS:
            for line in prose(doc):
                for target in LINK.findall(line):
                    if re.match(r'[a-z]+:', target):      # https:, mailto:
                        continue
                    path, _, anchor = target.partition('#')
                    file = (doc.parent / path).resolve() if path else doc
                    where = f'{doc.relative_to(ROOT)}: {target}'
                    if not file.exists():
                        problems.append(f'{where} (no such file)')
                    elif anchor and file.suffix == '.md' and anchor not in anchors(file):
                        problems.append(f'{where} (no such heading)')
        self.assertEqual(problems, [])

    def test_anchors_follow_github(self):
        doc = ROOT / 'docs' / 'deploy.md'
        self.assertIn('one-time-setup-founder', anchors(doc))
        self.assertIn('data-updates', anchors(doc))


if __name__ == '__main__':
    unittest.main()
