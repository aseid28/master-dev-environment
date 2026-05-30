import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the pattern logic directly without running main()
from hooks.pre_tool_call import is_write_op


# --- Should block ---
BLOCKED = [
    "curl -X POST https://api.example.com/data",
    "curl -X PUT https://api.example.com/item/1",
    "curl -X DELETE https://api.example.com/item/1",
    "curl -X PATCH https://api.example.com/item/1",
    "curl --request POST https://api.example.com",
    "requests.post(url, json=payload)",
    "requests.put(url, data=data)",
    "requests.delete(url)",
    "requests.patch(url, json=update)",
    "httpx.post('https://api.example.com')",
    "INSERT INTO users VALUES (1, 'test')",
    "UPDATE users SET name='x' WHERE id=1",
    "DELETE FROM sessions WHERE expired=true",
    "DROP TABLE users",
    "CREATE TABLE foo (id INT)",
    "ALTER TABLE users ADD COLUMN x INT",
    "git push origin main",
    "git push --force",
    "git reset --hard HEAD~1",
    "rm -rf ./tmp",
    "sendmail -v user@example.com",
]

# --- Should allow ---
ALLOWED = [
    "curl https://api.example.com/items",
    "curl -X GET https://api.example.com/items",
    "requests.get(url)",
    "httpx.get('https://api.example.com')",
    "SELECT * FROM users WHERE id=1",
    "SELECT COUNT(*) FROM events",
    "git status",
    "git log --oneline",
    "git diff HEAD",
    "git pull origin main",
    "ls -la",
    "python3 -m pytest",
    "cat README.md",
    "echo 'hello'",
]


def test_blocked_operations():
    for cmd in BLOCKED:
        assert is_write_op(cmd), f"Should have blocked: {cmd}"


def test_allowed_operations():
    for cmd in ALLOWED:
        assert not is_write_op(cmd), f"Should have allowed: {cmd}"
