# bist_project/__init__.py
from __future__ import absolute_import, unicode_literals

# This will ensure Celery loads when Django starts
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError as e:
    import sys
    print(f"Celery import hatası: {e}", file=sys.stderr)
    celery_app = None
    __all__ = ()