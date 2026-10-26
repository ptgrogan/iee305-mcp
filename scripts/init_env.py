"""Create .env with random secrets without printing them. Standard library only."""
from pathlib import Path
import os
import secrets

root = Path(__file__).resolve().parents[1]
destination = root / ".env"
text = (root / ".env.example").read_text(encoding="utf-8")
for key, size in [
    ("MONGO_PASSWORD", 32), ("JWT_SECRET", 32), ("JWT_REFRESH_SECRET", 32),
    ("CREDS_KEY", 32), ("CREDS_IV", 16)
]:
    text = text.replace(f"{key}=GENERATE", f"{key}={secrets.token_hex(size)}")
# O_EXCL refuses to overwrite existing deployment secrets.
fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
    stream.write(text)
print("Created .env. Fill in the hostname, CreateAI settings, and mail settings.")