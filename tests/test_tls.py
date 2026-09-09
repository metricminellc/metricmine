"""The TLS context every keyless download verifies against (F-58).

scripts/fetch_demo.py, scripts/fetch_common.py, and scripts/fetch_sample.py
all pass this context to urlopen, so a machine whose OpenSSL default verify
paths are empty still downloads. These tests hold the module to two things:
certifi's bundle is the real code path, and the ImportError branch is a
safety net that still verifies rather than a way to disable verification.
The fourth reads the three call sites, because a fix that a later edit can
silently drop is not fixed. Keyless and offline; nothing here opens a
socket.
"""

from __future__ import annotations

import ast
import builtins
import ssl
from collections.abc import Iterator
from pathlib import Path

import certifi
import pytest

from metricmine import tls

SCRIPTS = Path(__file__).resolve().parents[1].joinpath("scripts")
CALL_SITES = ("fetch_common.py", "fetch_demo.py", "fetch_sample.py")


@pytest.fixture(autouse=True)
def _uncached_context() -> Iterator[None]:
    # ssl_context caches, so every test here builds its own and leaves
    # nothing behind for the next one.
    tls.ssl_context.cache_clear()
    yield
    tls.ssl_context.cache_clear()


def _anchors(context: ssl.SSLContext) -> set[tuple[str, str]]:
    return {(c["serialNumber"], str(c["issuer"])) for c in context.get_ca_certs()}


def test_the_context_carries_certifis_bundle() -> None:
    # A subset, not an equality: the context is certifi's anchors ON TOP OF
    # the machine's. An equality assertion here would pass only for the
    # substituting form this module deliberately does not use.
    bundle = ssl.create_default_context()
    bundle.load_verify_locations(cafile=certifi.where())
    assert _anchors(bundle) <= _anchors(tls.ssl_context())


def test_the_context_keeps_the_machines_own_trust() -> None:
    # The regression guard. ssl.create_default_context(cafile=...) takes an
    # `if cafile ... elif` branch that skips load_default_certs, so naming a
    # bundle there drops the Windows certificate store, the system bundle on
    # Linux, and any exported SSL_CERT_FILE. Measured on a machine holding
    # 113 anchors, that form lost 54 of them. Nothing the machine trusts may
    # go missing from the context this project downloads with.
    machine = _anchors(ssl.create_default_context())
    assert machine <= _anchors(tls.ssl_context())


def test_the_context_verifies() -> None:
    context = tls.ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_the_fallback_still_verifies(monkeypatch: pytest.MonkeyPatch) -> None:
    # certifi absent is a safety net, never a way to skip verification: the
    # fallback is the context urlopen would have built for itself.
    real_import = builtins.__import__

    def refuse_certifi(name: str, *args: object, **kwargs: object) -> object:
        if name == "certifi":
            raise ImportError("certifi is not installed")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", refuse_certifi)
    context = tls.ssl_context()
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("script", CALL_SITES)
def test_every_download_passes_the_shared_context(script: str) -> None:
    # Read as a syntax tree, not as text: the call sites wrap across lines,
    # and both call shapes count, so a later `from urllib.request import
    # urlopen` cannot slip a bare call past the guard.
    # and a line-shaped assertion would pass on a call that dropped the
    # keyword. Every urlopen in the tree must carry context=ssl_context().
    source = SCRIPTS.joinpath(script).read_text(encoding="utf-8")
    assert "from metricmine.tls import ssl_context" in source
    calls = [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr == "urlopen")
            or (isinstance(node.func, ast.Name) and node.func.id == "urlopen")
        )
    ]
    assert calls, f"{script} makes no urlopen call"
    for call in calls:
        keywords = {kw.arg: kw.value for kw in call.keywords}
        context = keywords.get("context")
        assert isinstance(context, ast.Call), f"{script}:{call.lineno} has no context="
        assert isinstance(context.func, ast.Name)
        assert context.func.id == "ssl_context", f"{script}:{call.lineno}"
