"""Shared, conservative contribution-type suggestions for the Home and Hub feeds."""
import re

TYPES = ('code', 'testing', 'docs', 'translation', 'design', 'other')


def kind(issue: dict) -> str:
    labels = ' '.join(issue.get('labels', [])).lower()
    text = labels + ' ' + issue.get('title', '').lower() + ' ' + issue.get('needs', '').lower()
    for key, pattern in (
        ('translation', r'\b(translat\w*|locali[sz]\w*|proofread\w*|fluent arabic)\b'),
        ('testing', r'\b(test\w*|screen reader|qa)\b'),
        ('docs', r'\b(docs|documentation|document|readme|writing)\b'),
        ('design', r'\b(design|figma|illustration)\b'),
        ('code', r'\b(implement\w*|refactor\w*|type hints|css|javascript|typescript|programming)\b'),
    ):
        if re.search(pattern, text):
            return key
    return 'other'
