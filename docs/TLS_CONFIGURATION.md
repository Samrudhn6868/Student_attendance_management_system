# TLS Configuration

## Overview

This project includes a TLS wrapper (`src/tls_wrapper.py`) that enables running the Flask application over HTTPS using self-signed certificates for local development and testing. The wrapper **does not modify** the main application code (`src/main.py`) and is intended for secure API communications.

## How It Works

The `tls_wrapper.py` module provides two main functions:

### 1. `run_app_https(app, host='127.0.0.1', port=0, timeout=5.0)`

Starts the Flask application in a background thread with HTTPS enabled.

**Parameters:**
- `app`: The Flask WSGI application instance (imported from `main`)
- `host`: Host to bind to (default: `127.0.0.1`)
- `port`: Port to bind (0 = auto-select an available port)
- `timeout`: Seconds to wait for server startup

**Returns:**
A tuple `(port, shutdown, is_secure)`:
- `port`: The actual port number the server is listening on
- `shutdown`: A callable function to stop the server
- `is_secure`: Boolean indicating whether HTTPS is active

**SSL Certificate Priority:**
1. **Werkzeug + cryptography** (preferred): Uses `ssl_context='adhoc'` to generate a temporary self-signed certificate
2. **OpenSSL fallback**: If `cryptography` is not installed, attempts to use system `openssl` command
3. **Insecure HTTP fallback**: If neither method works, falls back to plain HTTP (useful on development machines without TLS tools)

### 2. `make_unverified_ssl_context()`

Returns an SSL context that does not verify certificates, suitable for testing against self-signed certificates.

## Usage Example

```python
from src.tls_wrapper import run_app_https, make_unverified_ssl_context
from src.main import app
import urllib.request

# Start the app with HTTPS
port, shutdown, is_secure = run_app_https(app)

try:
    if is_secure:
        # Make an HTTPS request with unverified context
        ctx = make_unverified_ssl_context()
        url = f"https://127.0.0.1:{port}/"
        with urllib.request.urlopen(url, context=ctx, timeout=5) as resp:
            print(resp.read().decode())
    else:
        # Fallback to HTTP
        url = f"http://127.0.0.1:{port}/"
        with urllib.request.urlopen(url, timeout=5) as resp:
            print(resp.read().decode())
finally:
    shutdown()
```

## Running Tests

The test suite includes `tests/unit/test_tls_run.py` which verifies HTTPS functionality:

```powershell
pytest tests/unit/test_tls_run.py -v
```

This test:
- Starts the Flask app with HTTPS (or HTTP fallback)
- Makes a request to the root endpoint
- Validates the response contains login-related content
- Properly shuts down the server

## Dependencies

For full HTTPS support, install the `cryptography` package:

```powershell
pip install -r requirements.txt
```

The `cryptography` package is included in `requirements.txt`. If unavailable, the wrapper will attempt to use system `openssl` or fall back to HTTP.

## CI/CD Integration

The GitHub Actions CI pipeline (`.github/workflows/ci.yml`) automatically installs dependencies from `requirements.txt`, including `cryptography`, ensuring HTTPS tests run successfully in CI environments.

## Production Deployment

For production deployments, use a proper reverse proxy (nginx, Apache) or a WSGI server (Gunicorn, uWSGI) with a valid TLS certificate from a trusted Certificate Authority. The `tls_wrapper` is intended for **development and testing only**.

## Security Notes

- Self-signed certificates should **never** be used in production
- The unverified SSL context (`ssl.CERT_NONE`) disables certificate validation and should only be used in tests
- For production, obtain certificates from Let's Encrypt or another CA
- Use environment variables to configure TLS settings (cert paths, key paths)

## Troubleshooting

**Error: "Using ad-hoc certificates requires the cryptography library"**
- Install: `pip install cryptography`

**Error: "Failed to generate adhoc certificate. Install cryptography or openssl."**
- Install `cryptography` package OR ensure `openssl` is available on your system PATH
- On Windows, consider installing [Win32 OpenSSL](https://slproweb.com/products/Win32OpenSSL.html)

**Test falls back to HTTP instead of HTTPS**
- This is expected behavior when neither `cryptography` nor `openssl` are available
- The test will still pass, but will use HTTP instead of HTTPS
- Install `cryptography` to enable HTTPS testing
