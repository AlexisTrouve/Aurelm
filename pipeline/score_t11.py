import json, unicodedata
from pipeline.db import get_connection

def normalize(text):
    text = text.lower().strip()
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    # Expand ligatures before NFD decomposition (NFD doesn't split oe ligature)
    text = text.replace("\u0153", "oe").replace("\u0152", "OE")
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    for art in ["l'", "le ", "la ", "les "]:
        if text.startswith(art):
            text = text[len(art):]
    return text

ref = json.load(open("data/reference_turn11.json"))
ref_canonicals = {ent["name"] for ent in ref["entities"]}
all_ref_norms = {}
for ent in ref["entities"]:
    all_ref_norms[normalize(ent["name"])] = ent["name"]
    for a in ent.get("aliases", []):
        all_ref_norms[normalize(a)] = ent["name"]

conn = get_connection("C:/Users/alexi/AppData/Local/Temp/t11_test.db")
extracted = [r["canonical_name"] for r in conn.execute("SELECT canonical_name FROM entity_entities").fetchall()]
conn.close()

matched_ref = set()
fp_names = []
for name in extracted:
    n = normalize(name)
    if n in all_ref_norms:
        matched_ref.add(all_ref_norms[n])
    else:
        fp_names.append(name)

tp = len(matched_ref)
fn_entities = sorted(ref_canonicals - matched_ref)
fn = len(fn_entities)
fp = len(fp_names)

precision = tp / (tp + fp) if (tp + fp) > 0 else 0
recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

print(f"Reference: {len(ref_canonicals)} entites | Extracted: {len(extracted)}")
print(f"TP={tp}  FP={fp}  FN={fn}")
print(f"Precision={precision:.1%}  Recall={recall:.1%}  F1={f1:.1%}")
print()
print("=== FN (manques) ===")
for n in fn_entities:
    print(f"  - {n}")
print()
print("=== FP (faux positifs) ===")
for n in sorted(fp_names):
    print(f"  - {n}")
