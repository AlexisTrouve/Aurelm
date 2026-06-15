"""Quick test: run entity tag assignment on a few T08 entities and print results."""
import sys, re, json, sqlite3

sys.path.insert(0, "C:/Users/alexi/Documents/projects/Aurelm/pipeline")

from pipeline.entity_profiler import ENTITY_TAG_VOCAB, PROFILE_PROMPT
from pipeline.llm_provider import OpenRouterProvider

DB = "C:/Users/alexi/Documents/projects/Aurelm/pipeline/aurelm_v22_2_2.db"
MODEL = "qwen3:14b"

def parse_json(text: str) -> dict:
    """Extract first JSON object from LLM response (strips think tags etc.)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    return {}

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

entities = conn.execute("""
    SELECT DISTINCT e.id, e.canonical_name, e.entity_type
    FROM entity_entities e
    JOIN entity_mentions m ON e.id = m.entity_id
    JOIN turn_turns t ON m.turn_id = t.id
    WHERE t.turn_number = 8 AND e.disabled = 0
    ORDER BY (SELECT COUNT(*) FROM entity_mentions m2 WHERE m2.entity_id = e.id) DESC
    LIMIT 4
""").fetchall()

llm = OpenRouterProvider()

for ent in entities:
    eid, name, etype = ent["id"], ent["canonical_name"], ent["entity_type"]

    mentions = conn.execute("""
        SELECT m.context, t.turn_number FROM entity_mentions m
        JOIN turn_turns t ON m.turn_id = t.id
        WHERE m.entity_id = ? ORDER BY t.turn_number LIMIT 8
    """, (eid,)).fetchall()

    mentions_text = "\n\n".join(
        f"[Tour {m['turn_number']}]\n{m['context']}"
        for m in mentions if m["context"]
    )
    if not mentions_text:
        print(f"\n[{name}] — no contexts")
        continue

    prompt = PROFILE_PROMPT.format(
        name=name, entity_type=etype,
        mentions=mentions_text[:4000],
        tag_vocab=", ".join(ENTITY_TAG_VOCAB),
    )

    print(f"\n{'='*60}\nEntity: {name} ({etype})")
    try:
        raw = llm.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            num_ctx=8192, max_tokens=2000, temperature=0,
        )
        data = parse_json(raw)
        valid_tags = [t for t in data.get("tags", []) if t in ENTITY_TAG_VOCAB]
        print(f"  Tags   : {valid_tags}")
        print(f"  Desc   : {data.get('description', '')[:120]}...")
    except Exception as e:
        print(f"  ERROR  : {e}")

conn.close()
