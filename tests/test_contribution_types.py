"""Task hints must preserve human-maintained beginner labels and handle ambiguity."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'site'))
from djsite.contributions import kind


class ContributionTypes(unittest.TestCase):
    def test_unknown_tasks_are_not_presented_as_code(self):
        self.assertEqual(kind({'title': 'Discuss a transport idea', 'labels': ['help wanted']}), 'other')
        self.assertEqual(kind({}), 'other')

    def test_testing_a_code_feature_remains_a_testing_task(self):
        self.assertEqual(kind({'title': 'Test the JavaScript charts', 'labels': ['help wanted']}), 'testing')

    def test_arabic_title_can_use_a_maintainer_type_label(self):
        self.assertEqual(kind({'title': 'مراجعة نصوص الواجهة', 'labels': ['Translation']}), 'translation')

    def test_beginner_label_does_not_imply_a_task_type(self):
        issue = {'title': 'Help with release planning', 'labels': ['good first issue']}
        self.assertEqual(kind(issue), 'other')
        self.assertEqual(issue['labels'], ['good first issue'])
