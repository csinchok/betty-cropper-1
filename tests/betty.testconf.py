import os
import tempfile

MODULE_ROOT = os.path.dirname(os.path.realpath(__file__))

CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
BETTY_DEFAULT_IMAGE = 666
BETTY_IMAGE_URL = "http://localhost:8081/images/"
MEDIA_ROOT = tempfile.mkdtemp("bettycropper")
TEMPLATE_DIRS = (os.path.join(MODULE_ROOT, "tests", "templates"),)
BETTY_WIDTHS = [240, 640, 820, 960, 1200]
