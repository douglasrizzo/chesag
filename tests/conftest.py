"""Shared pytest configuration for the test suite."""

from __future__ import annotations

import os

from hypothesis import settings

settings.register_profile("ci", max_examples=50)
if os.environ.get("CI"):
  settings.load_profile("ci")
