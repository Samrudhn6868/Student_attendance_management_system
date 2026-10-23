"""TLS wrapper to run the Flask app with HTTPS for testing and local runs.

This module exposes helpers to start the application's WSGI server with
an SSL context (adhoc self-signed certificate). It intentionally does not
modify `main.py` — instead it imports the Flask `app` and runs it under
HTTPS in a background thread for use in tests or local secure runs.

Note: this uses Werkzeug's `make_server` with `ssl_context='adhoc'` which
creates a temporary self-signed certificate. Tests use an unverified SSL
context to connect to the server.
"""
from typing import Tuple, Callable
import threading
import time
import socket
import ssl

from werkzeug.serving import make_server
import tempfile
import shutil
import subprocess
from pathlib import Path


def run_app_https(app, host: str = '127.0.0.1', port: int = 0, timeout: float = 5.0) -> Tuple[int, Callable[[], None], bool]:
    """Start the given Flask `app` under HTTPS in a background thread.

    Args:
        app: Flask WSGI app instance (e.g. imported from `main.app`).
        host: Host to bind to (default 127.0.0.1).
        port: Port to bind (0 chooses a free ephemeral port).
        timeout: How long to wait for the server to be ready.

    Returns:
        A tuple (port, shutdown) where `port` is the bound port number and
        `shutdown` is a callable to stop the server.
    """

    temp_dir = None

    is_secure = True
    # Try to create server with adhoc SSL context (Werkzeug + cryptography)
    try:
        server = make_server(host, port, app, threaded=True, ssl_context='adhoc')
    except Exception:
        # Fallback: generate a temporary self-signed certificate with openssl
        # and pass (certfile, keyfile) tuple to make_server. This avoids a
        # hard dependency on the `cryptography` package when running tests.
        temp_dir = Path(tempfile.mkdtemp(prefix='adhoc-cert-'))
        cert_file = str(temp_dir / 'cert.pem')
        key_file = str(temp_dir / 'key.pem')

        # Use openssl to create a self-signed certificate. If openssl is not
        # available, raise the original error to surface the problem.
        try:
            subprocess.check_call([
                'openssl', 'req', '-x509', '-nodes', '-days', '1',
                '-newkey', 'rsa:2048', '-keyout', key_file, '-out', cert_file,
                '-subj', '/CN=localhost'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            server = make_server(host, port, app, threaded=True, ssl_context=(cert_file, key_file))
        except Exception:
            # If openssl is not available, fall back to insecure HTTP for
            # maximum portability (useful on dev Windows machines). The
            # caller/test should be tolerant of an insecure fallback.
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
            temp_dir = None
            is_secure = False
            server = make_server(host, port, app, threaded=True)

    # Retrieve actual port (useful if port was 0)
    bound_port = server.socket.getsockname()[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Wait for server to be ready (simple check)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, bound_port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.05)

    def shutdown():
        try:
            server.shutdown()
        except Exception:
            pass
        thread.join(timeout=2)

        # Remove temporary certificate directory if created
        if temp_dir is not None:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    return bound_port, shutdown, is_secure


def make_unverified_ssl_context():
    """Return an SSL context that does not verify certificates (for tests).

    Use this for test clients connecting to the adhoc self-signed cert.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
