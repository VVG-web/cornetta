#!/usr/bin/env python3
"""Sign and verify the Cornetta update feed with ECDSA P-256 and SHA-256.

The private key is a PEM file outside the repository. It is never printed and never committed.
The public key is a base64 X9.63 point (65 bytes, starting with 0x04), embedded in both apps.

Usage:
  scripts/sign-feed.py --public-key
  scripts/sign-feed.py --check-key
  scripts/sign-feed.py --sign site/update/feed.json
  scripts/sign-feed.py --verify site/update/feed.json site/update/feed.json.sig --public-key-base64 KEY
"""
import argparse
import base64
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEY = Path.home() / ".config" / "cornetta" / "update-feed-key.pem"
P256_SPKI_PREFIX = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200")
SIGNATURE_BYTES = 64


def fail(message: str) -> None:
    sys.exit(f"sign-feed: {message}")


def openssl(*args: str, data: bytes | None = None) -> bytes:
    result = subprocess.run(["openssl", *args], input=data, capture_output=True)
    if result.returncode != 0:
        fail(f"openssl {args[0]} failed: {result.stderr.decode(errors='replace').strip()[-300:]}")
    return result.stdout


def key_path(explicit: str | None) -> Path:
    path = Path(explicit or os.environ.get("CORNETTA_FEED_KEY_FILE") or DEFAULT_KEY).expanduser().resolve()
    if not path.is_file():
        fail(f"missing private key: {path}")
    if path == ROOT or ROOT in path.parents:
        fail("private key must stay outside the repository")
    if os.name == "posix" and path.stat().st_mode & 0o077:
        fail("private key must not be readable by other users (chmod 600)")
    return path


def public_key_base64(path: Path) -> str:
    spki = openssl("pkey", "-in", str(path), "-pubout", "-outform", "DER")
    if not spki.startswith(P256_SPKI_PREFIX):
        fail("private key is not ECDSA P-256")
    point = spki[len(P256_SPKI_PREFIX):]
    if len(point) != 65 or point[0] != 0x04:
        fail("public key is not an uncompressed P-256 point")
    return base64.b64encode(point).decode("ascii")


def der_to_raw(der: bytes) -> bytes:
    def integer(buf: bytes, index: int) -> tuple[bytes, int]:
        if buf[index] != 0x02:
            fail("unexpected ECDSA signature")
        length = buf[index + 1]
        value = buf[index + 2:index + 2 + length].lstrip(b"\x00")
        if len(value) > 32:
            fail("unexpected ECDSA signature")
        return value.rjust(32, b"\x00"), index + 2 + length

    if der[0] != 0x30:
        fail("unexpected ECDSA signature")
    start = 3 if der[1] & 0x80 else 2
    r, index = integer(der, start)
    s, _ = integer(der, index)
    return r + s


def raw_to_der(raw: bytes) -> bytes:
    def integer(value: bytes) -> bytes:
        value = value.lstrip(b"\x00") or b"\x00"
        if value[0] & 0x80:
            value = b"\x00" + value
        return bytes([0x02, len(value)]) + value

    body = integer(raw[:32]) + integer(raw[32:])
    return bytes([0x30, len(body)]) + body


def verify(feed: Path, signature: Path, public_base64: str) -> bool:
    try:
        point = base64.b64decode(public_base64, validate=True)
        raw = base64.b64decode(signature.read_text(encoding="ascii").strip(), validate=True)
    except (ValueError, UnicodeDecodeError):
        return False
    if len(point) != 65 or point[0] != 0x04 or len(raw) != SIGNATURE_BYTES:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        pub = Path(tmp) / "pub.der"
        sig = Path(tmp) / "sig.der"
        pub.write_bytes(P256_SPKI_PREFIX + point)
        sig.write_bytes(raw_to_der(raw))
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(pub), "-keyform", "DER",
             "-signature", str(sig), str(feed)],
            capture_output=True,
        )
        return result.returncode == 0


def sign(feed: Path, path: Path) -> None:
    if not feed.is_file():
        fail(f"missing feed: {feed}")
    with tempfile.TemporaryDirectory() as tmp:
        der_path = Path(tmp) / "signature.der"
        openssl("dgst", "-sha256", "-sign", str(path), "-out", str(der_path), str(feed))
        raw = der_to_raw(der_path.read_bytes())
    if len(raw) != SIGNATURE_BYTES:
        fail("unexpected ECDSA signature length")
    signature = feed.with_name(feed.name + ".sig")
    signature.write_text(base64.b64encode(raw).decode("ascii") + "\n", encoding="ascii")
    if not verify(feed, signature, public_key_base64(path)):
        fail("the signature just written does not verify")
    print(f"signed {feed} -> {signature}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", help="private key PEM (default: CORNETTA_FEED_KEY_FILE or ~/.config/cornetta/update-feed-key.pem)")
    parser.add_argument("--public-key", action="store_true", help="print the base64 public key")
    parser.add_argument("--check-key", action="store_true", help="validate the private key without signing")
    parser.add_argument("--sign", metavar="FEED", type=Path, help="sign the exact bytes of FEED, writing FEED.sig")
    parser.add_argument("--verify", nargs=2, metavar=("FEED", "SIG"))
    parser.add_argument("--public-key-base64")
    options = parser.parse_args()

    path = key_path(options.key)
    if options.public_key:
        print(public_key_base64(path))
        return
    if options.check_key:
        public = public_key_base64(path)
        if len(public) != 88 or not re.fullmatch(r"[A-Za-z0-9+/]{87}=", public):
            fail("public key has an unexpected encoding")
        print("update feed key is ready")
        return
    if options.sign:
        sign(options.sign, path)
        return
    if options.verify:
        if not options.public_key_base64:
            parser.error("--verify requires --public-key-base64")
        if not verify(Path(options.verify[0]), Path(options.verify[1]), options.public_key_base64):
            fail("signature is not valid")
        print("signature is valid")
        return
    parser.print_help()
    sys.exit(2)


if __name__ == "__main__":
    main()
