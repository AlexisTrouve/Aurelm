"""Drive the REAL agent through its REAL HTTP endpoint and report what it does.

Not a pass/fail test — a probe. It boots `python -m bot`, POSTs questions to /chat,
and prints which tools the agent actually chose plus its answer. That is the only way
to see whether the three tool fixes change behaviour in conversation, as opposed to in
a unit test.

    py -3.12 bot/tests/live_agent_probe.py

Costs a few real LLM turns on the etheryale proxy.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "gui" / "integration_test" / "fixtures" / "e2e.db"
KEY = os.environ.get("ETHERYALE_API_KEY") or "eai_ESu-8usnN17_6I09zZ2F5A15rGnrZVfQ"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def build_db(dst: Path) -> Path:
    """Fixture + the shape each fix needs: a 2-hop chain, described links, and enough
    entities that any sane `limit` truncates."""
    shutil.copy(FIXTURE, dst)
    c = sqlite3.connect(dst)
    # Enough entities that a listing must be capped -> exercises the truncation notice.
    for i in range(40):
        c.execute(
            "INSERT INTO entity_entities (canonical_name, entity_type, civ_id, description,"
            " is_active) VALUES (?, 'person', 1, 'Un garde de la Confluence.', 1)",
            (f"Garde {i:02d}",))
    # The fixture already has: Rubanc -> Caste de l'Air -> Culte des Ancetres,
    # every link carrying a description. That is the 2-hop chain.
    c.commit()
    rels = c.execute(
        "SELECT s.canonical_name, r.relation_type, t.canonical_name, r.description "
        "FROM entity_relations r JOIN entity_entities s ON s.id = r.source_entity_id "
        "JOIN entity_entities t ON t.id = r.target_entity_id").fetchall()
    n = c.execute("SELECT COUNT(*) FROM entity_entities").fetchone()[0]
    c.close()
    print(f"[db] {n} entities, {len(rels)} relations")
    for a, rt, b, d in rels:
        print(f"     {a} --{rt}--> {b}   ({d})")
    return dst


def ask(port: int, question: str) -> tuple[list[str], str]:
    """POST /chat, consume the NDJSON stream, return (tools called, final answer)."""
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/chat",
        data=json.dumps({"message": question}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tools: list[str] = []
    answer = ""
    with urllib.request.urlopen(req, timeout=300) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "tool_start":
                tools.append(f"{ev.get('name')}({ev.get('input_summary', '')})")
            elif ev.get("type") == "text":
                answer = ev.get("content", "")
            elif ev.get("type") == "error":
                answer = f"[ERROR] {ev.get('message')}"
    return tools, answer


QUESTIONS = [
    ("multi-hop (fix 2)",
     "Comment Rubanc est-il lie au Culte des Ancetres ? Retrace la chaine."),
    ("relation detail (fix 2)",
     "Pourquoi Rubanc est-il rattache a la Caste de l'Air ? Donne la raison exacte."),
    ("truncation honesty (fix 3)",
     "Liste toutes les entites de type person de la Confluence. Combien y en a-t-il en tout ?"),
]


def main() -> int:
    tmp = Path(os.environ.get("TEMP", "/tmp")) / "aurelm_probe.db"
    if tmp.exists():
        tmp.unlink()
    build_db(tmp)

    port = _free_port()
    env = {**os.environ, "ETHERYALE_API_KEY": KEY}
    # Apply migrations FIRST: doing it inside the server start pushed the health check
    # past its window on a fresh DB and looked like a dead server.
    subprocess.run([sys.executable, "-m", "bot", "--db", str(tmp), "--migrate-only"],
                   cwd=str(REPO), env=env, capture_output=True, text=True)
    proc = subprocess.Popen(
        [sys.executable, "-m", "bot", "--db", str(tmp), "--port", str(port)],
        cwd=str(REPO), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        # Wait for /health rather than sleeping blind.
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            print("[!] server never became healthy; its output:")
            proc.terminate()
            out, _ = proc.communicate(timeout=10)
            print((out or "")[-2000:])
            return 1
        print(f"[server] up on :{port}\n")

        for label, q in QUESTIONS:
            print("=" * 78)
            print(f"[{label}] {q}")
            tools, answer = ask(port, q)
            print(f"  tools : {tools}")
            print(f"  answer: {answer.strip()[:700]}")
            print()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
