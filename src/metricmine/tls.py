"""The TLS trust every keyless download in this project verifies against.

Governing finding: F-58 (docs/verification/gate_proof_findings.md).

``urllib.request.urlopen`` with no ``context=`` builds one from
``ssl.create_default_context()``, which loads OpenSSL's default verify
paths and nothing else. A python.org framework CPython on macOS ships
with those paths empty until its ``Install Certificates.command`` has
run, so every download dies with CERTIFICATE_VERIFY_FAILED before
anything builds. This module is the one place that answers it.

certifi's bundle is added to the machine's own trust, never substituted
for it. The distinction is the whole design:
``create_default_context(cafile=...)`` takes an ``if cafile ... elif``
branch that skips ``load_default_certs`` entirely, so naming a bundle
there would drop the Windows certificate store, the system bundle on
Linux, and any SSL_CERT_FILE the operator exported. Measured: on a
machine whose store held 113 anchors, the substituting form kept 109 and
lost 54 of the machine's own; the additive form below lost none. A
corporate TLS-inspecting proxy's root lives in exactly the store the
substituting form would have discarded.

So: build the default context first, then add certifi. Verification is
never disabled, the machine's trust is never narrowed, and a machine
that already worked keeps working. certifi absent, or present without a
readable bundle, degrades to the context urlopen would have built for
itself.

The three call sites are scripts/fetch_demo.py, scripts/fetch_common.py,
and scripts/fetch_sample.py. scripts/doctor.py does not import this
module: it stays standard library so it runs before the package is
trusted, and it reports the machine's own trust store, which this
context builds on rather than replaces.
"""

from __future__ import annotations

import functools
import ssl
import sys


@functools.lru_cache(maxsize=1)
def ssl_context() -> ssl.SSLContext:
    """The verification context for every download this project makes.

    Cached: the bundle is parsed once per process, not once per file in
    a multi-file source refresh. The context is read-only to callers,
    which pass it to urlopen and nothing else.
    """
    context = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        # The declared fallback: certifi is a project dependency, so its
        # absence is a deliberate or broken environment rather than an
        # anomaly worth a line. The default context already carries
        # whatever this machine trusts.
        return context
    try:
        context.load_verify_locations(cafile=certifi.where())
    except OSError as exc:
        # certifi is installed but its bundle did not load: truncated by a
        # partial wheel extraction, rewritten by a scanner, or unreadable.
        # ssl.SSLError subclasses OSError, so a corrupt PEM lands here too.
        # Raising would be worse than the failure this module prevents, but
        # staying silent on a bare interpreter reproduces exactly the
        # CERTIFICATE_VERIFY_FAILED of F-58 with nothing naming the cause,
        # and doctor cannot diagnose it because it does not import this
        # module. One line to stderr is the difference between an opaque
        # traceback and a fixable one. Never stdout: a caller may be
        # speaking a protocol on it.
        print(
            f"metricmine: certifi's CA bundle did not load ({exc}); falling"
            " back to this interpreter's own trust",
            file=sys.stderr,
        )
    return context
