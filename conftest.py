import os
import tempfile

from django.conf import settings

from betty.conf import server

MODULE_ROOT = os.path.dirname(os.path.realpath(__file__))


def pytest_configure():
    settings.configure(
        server,
        MEDIA_ROOT=tempfile.mkdtemp("bettycropper"),
        TEMPLATE_DIRS=(os.path.join(MODULE_ROOT, 'tests', 'templates'),)
    )
