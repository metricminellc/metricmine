"""The TLS context every keyless download verifies against (F-58).

scripts/fetch_demo.py, scripts/fetch_common.py, and scripts/fetch_sample.py
all pass this context to urlopen, so a machine whose OpenSSL default verify
paths are empty still downloads. These tests hold the module to three
things: certifi's bundle is the real code path, the machine's own trust
survives beside it rather than under it, and the ImportError branch is a
safety net that still verifies rather than a way to disable verification.
The last two read every fetch script in the tree, because a fix that a
later edit can silently drop is not fixed. Keyless and offline; nothing here
opens a socket.
"""

from __future__ import annotations

import ast
import ssl
import sys
from collections.abc import Iterator
from pathlib import Path

import certifi
import pytest

from metricmine import tls

REPO = Path(__file__).resolve().parents[1]
# F-58's class is "a download that does not name its trust store", which is
# not confined to a filename shape: every module that could open one is read,
# and the ones that make no urlopen call skip.
SOURCES = sorted(
    [*REPO.joinpath("scripts").glob("*.py"), *REPO.joinpath("src").rglob("*.py")]
)
DIRECT_CALLERS = {"fetch_common.py", "fetch_demo.py", "fetch_sample.py"}


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
    # certifi's anchors alone, loaded into an otherwise empty context, so the
    # expectation is the bundle rather than a replay of the two calls the
    # implementation makes. Built the earlier way -- default context plus
    # certifi -- this assertion was true by construction for anything that
    # made those calls and tested nothing.
    bundle = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    bundle.load_verify_locations(cafile=certifi.where())
    assert _anchors(bundle) <= _anchors(tls.ssl_context())


def test_the_context_keeps_the_machines_own_trust() -> None:
    # Nothing the machine trusts may go missing from the context this project
    # downloads with. Measured on a machine holding 113 anchors, the
    # substituting form lost 54 of them. This assertion sees that only where
    # the machine has a store to lose: on a bare interpreter it compares the
    # empty set and passes either way, which is why the next test exists.
    machine = _anchors(ssl.create_default_context())
    assert machine <= _anchors(tls.ssl_context())


def test_the_context_is_built_additively(monkeypatch: pytest.MonkeyPatch) -> None:
    # The same guard, independent of the ambient store, so it holds on the
    # bare interpreter F-58 is about. create_default_context(cafile=...)
    # takes an `if cafile or capath or cadata` branch whose `elif` holds
    # load_default_certs, so naming a bundle there silently drops the
    # Windows certificate store, the system bundle on Linux, and any
    # exported SSL_CERT_FILE. The keyword must never be passed.
    seen: list[dict[str, object]] = []
    real = ssl.create_default_context

    def record(*args: object, **kwargs: object) -> ssl.SSLContext:
        seen.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(ssl, "create_default_context", record)
    tls.ssl_context()
    assert seen, "ssl_context built no default context"
    for kwargs in seen:
        assert "cafile" not in kwargs
        assert "capath" not in kwargs
        assert "cadata" not in kwargs


def test_the_context_verifies() -> None:
    context = tls.ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_the_fallback_still_verifies(monkeypatch: pytest.MonkeyPatch) -> None:
    # certifi absent is a safety net, never a way to skip verification: the
    # fallback is the context urlopen would have built for itself.
    # A None entry makes exactly `import certifi` raise and touches nothing
    # else. Replacing builtins.__import__ would route every import executed
    # anywhere during the call through the shim.
    monkeypatch.setitem(sys.modules, "certifi", None)
    context = tls.ssl_context()
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def _urlopen_calls(source: str) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Attribute) and node.func.attr == "urlopen")
            or (isinstance(node.func, ast.Name) and node.func.id == "urlopen")
        )
    ]


def test_the_direct_download_sites_are_the_known_ones() -> None:
    # Every other module routes through fetch_common.download and inherits
    # the context from there. A new one that opens its own urlopen shows up
    # here first, so the sweep below can never quietly match nothing.
    direct = {
        source.name
        for source in SOURCES
        if _urlopen_calls(source.read_text(encoding="utf-8"))
    }
    assert direct == DIRECT_CALLERS


@pytest.mark.parametrize("script", SOURCES, ids=lambda p: p.name)
def test_every_download_passes_the_shared_context(script: Path) -> None:
    # Read as a syntax tree, not as text: the call sites wrap across lines,
    # so a line-shaped assertion would pass on a call that dropped the
    # keyword. Both call shapes count too, so a later `from urllib.request
    # import urlopen` cannot slip a bare call past the guard. Every urlopen
    # in the tree must carry context=ssl_context().
    source = script.read_text(encoding="utf-8")
    calls = _urlopen_calls(source)
    if not calls:
        return  # routes through fetch_common.download, checked there
    assert "from metricmine.tls import ssl_context" in source
    for call in calls:
        keywords = {kw.arg: kw.value for kw in call.keywords}
        context = keywords.get("context")
        assert isinstance(context, ast.Call), f"{script.name}:{call.lineno} has no context="
        assert isinstance(context.func, ast.Name)
        assert context.func.id == "ssl_context", f"{script.name}:{call.lineno}"
