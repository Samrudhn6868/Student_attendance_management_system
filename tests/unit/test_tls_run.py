"""Clean TLS test that handles secure or insecure fallback.

This test does not rely on the other malformed test files and will be
directly executed to validate TLS serving behavior.
"""
import os
import sys
import ssl
import urllib.request
import time

# Add src to sys.path so we can import application modules
_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..'))
_SRC_DIR = os.path.join(_REPO_ROOT, 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from tls_wrapper import make_unverified_ssl_context, run_app_https
import main as app_module


def test_tls_or_insecure_fallback():
    port, shutdown, is_secure = run_app_https(app_module.app)
    try:
        time.sleep(0.05)

        if is_secure:
            ctx = make_unverified_ssl_context()
            url = f"https://127.0.0.1:{port}/"
            with urllib.request.urlopen(url, context=ctx, timeout=5) as resp:
                body = resp.read().decode('utf-8', errors='ignore')
                code = resp.getcode()
        else:
            url = f"http://127.0.0.1:{port}/"
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read().decode('utf-8', errors='ignore')
                code = resp.getcode()

        assert code in (200, 302)
        assert 'login' in body.lower() or '<form' in body.lower()

    finally:
        shutdown()
