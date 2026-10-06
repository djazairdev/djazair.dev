"""From an archived release to published data, stopping at the first failure (PRD §9.5).

Validation comes first: if it fails, no later step runs, so the last good derived data
and the live site stay as they are.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Sequence

from .release import Archive
from .validate import Report, validate


class ValidationFailed(Exception):
    def __init__(self, report: Report):
        super().__init__(f'release {report.commit[:12]} failed validation with {len(report.errors)} errors')
        self.report = report


def process(archive: Archive, steps: Sequence[Callable] = (), report_path: Optional[Path] = None) -> Report:
    """Validate ``archive``, then run each step as ``step(archive)``."""
    report = validate(archive)
    if report_path:
        Path(report_path).write_text(report.markdown(), 'utf-8')
    if not report.ok:
        raise ValidationFailed(report)
    for step in steps:
        step(archive)
    return report
