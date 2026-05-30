"""
Credential store: age-encrypted secrets with consume-only enforcement.

Secrets are stored encrypted at:
  credentials/<project_id>.age

At runtime, the orchestrator calls load() which decrypts into a dict
and injects the values as env vars into the tmux session. Values are
never written to disk unencrypted.

Setup (one-time, per project):
  age-keygen -o ~/.age-key.txt
  # Then encrypt your secrets file:
  python3 credential_store.py encrypt projects/my-project/secrets.env my-project

secrets.env format (one KEY=value per line, # for comments):
  ANTHROPIC_API_KEY=sk-ant-...
  DATABASE_URL=postgres://...
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

CREDENTIALS_DIR = Path(__file__).parent.parent / "credentials"
DEFAULT_KEY_PATH = Path.home() / ".age-key.txt"


class CredentialStore:
    def __init__(self, project_id: str, key_path: Optional[str | Path] = None):
        self.project_id = project_id
        self.key_path = Path(key_path) if key_path else DEFAULT_KEY_PATH
        self.encrypted_path = CREDENTIALS_DIR / f"{project_id}.age"

    def exists(self) -> bool:
        return self.encrypted_path.exists()

    def load(self) -> dict[str, str]:
        """
        Decrypt and return credentials as a dict.
        Values are held in memory only — never written to disk.
        Raises if the key file or encrypted store is missing.
        """
        if not self.key_path.exists():
            raise FileNotFoundError(
                f"age key not found at {self.key_path}. "
                f"Run: age-keygen -o {self.key_path}"
            )
        if not self.encrypted_path.exists():
            raise FileNotFoundError(
                f"Credential store not found: {self.encrypted_path}. "
                f"Run: python3 credential_store.py encrypt <secrets.env> {self.project_id}"
            )

        result = subprocess.run(
            ["age", "--decrypt", "-i", str(self.key_path), str(self.encrypted_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Decryption failed: {result.stderr.strip()}")

        return _parse_env(result.stdout)

    def inject_into_tmux(self, session_name: str, credentials: dict[str, str]) -> None:
        """
        Inject credentials as env vars into an existing tmux session.
        Values are passed directly to tmux setenv — not via shell or temp files.
        """
        for key, value in credentials.items():
            subprocess.run(
                ["tmux", "setenv", "-t", session_name, key, value],
                check=True,
                capture_output=True,
            )

    @classmethod
    def encrypt(cls, secrets_file: str | Path, project_id: str, key_path: Optional[str | Path] = None) -> Path:
        """
        Encrypt a plaintext secrets.env file into credentials/<project_id>.age.
        Deletes nothing — the caller is responsible for removing the plaintext file.
        """
        key_path = Path(key_path) if key_path else DEFAULT_KEY_PATH
        if not key_path.exists():
            raise FileNotFoundError(f"age key not found at {key_path}")

        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = CREDENTIALS_DIR / f"{project_id}.age"

        # Extract the public key from the identity file
        pub_result = subprocess.run(
            ["age-keygen", "-y", str(key_path)],
            capture_output=True,
            text=True,
        )
        if pub_result.returncode != 0:
            raise RuntimeError(f"Could not read public key: {pub_result.stderr}")
        public_key = pub_result.stdout.strip()

        result = subprocess.run(
            ["age", "--encrypt", "-r", public_key, "-o", str(out_path), str(secrets_file)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Encryption failed: {result.stderr.strip()}")

        return out_path


def _parse_env(content: str) -> dict[str, str]:
    """Parse a KEY=value env file, skipping comments and blank lines."""
    result = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip()
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Credential store management")
    sub = parser.add_subparsers(dest="cmd")

    enc = sub.add_parser("encrypt", help="Encrypt a secrets.env file")
    enc.add_argument("secrets_file")
    enc.add_argument("project_id")
    enc.add_argument("--key", default=str(DEFAULT_KEY_PATH))

    dec = sub.add_parser("list-keys", help="List credential keys (not values) for a project")
    dec.add_argument("project_id")
    dec.add_argument("--key", default=str(DEFAULT_KEY_PATH))

    args = parser.parse_args()

    if args.cmd == "encrypt":
        out = CredentialStore.encrypt(args.secrets_file, args.project_id, args.key)
        print(f"Encrypted → {out}")
        print("Remember to delete the plaintext secrets file.")
    elif args.cmd == "list-keys":
        store = CredentialStore(args.project_id, args.key)
        creds = store.load()
        print(f"Keys for project '{args.project_id}':")
        for k in creds:
            print(f"  {k}")
    else:
        parser.print_help()
