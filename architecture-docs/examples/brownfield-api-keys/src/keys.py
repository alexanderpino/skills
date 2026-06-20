"""API-key management for LinkShort (illustrative excerpt)."""
import hashlib
import os
import secrets

# ARCH-REF: ADR-0001 (docs/architecture/decisions/ADR-0001-hashed-api-key-storage.md)
# Keys are stored only as salted SHA-256 hashes; the plaintext token is returned once.


def issue(account_id, repo):
    token = secrets.token_urlsafe(32)
    salt = os.urandom(16)
    key_hash = hashlib.sha256(salt + token.encode()).hexdigest()
    repo.save(account_id=account_id, salt=salt.hex(), key_hash=key_hash)
    return token  # shown to the integrator exactly once


def verify(token, repo):
    for row in repo.active_keys():
        salt = bytes.fromhex(row["salt"])
        if secrets.compare_digest(hashlib.sha256(salt + token.encode()).hexdigest(), row["key_hash"]):
            return row["account_id"]
    return None
