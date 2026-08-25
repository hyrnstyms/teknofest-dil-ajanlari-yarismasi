import sys, json
sys.path.insert(0, ".")

# Test setindeki hangi sorular hangi kaynak dokumana ait?
with open("data/evaluation/legal/rag_test_seti.jsonl", encoding="utf-8") as f:
    recs = [json.loads(l) for l in f if l.strip()]

from collections import Counter
src_counter = Counter(r.get("kaynak_dokuman", "?") for r in recs)
print("Test seti - kaynak_dokuman dagilimi:")
for src, cnt in src_counter.most_common():
    print(f"  {src}: {cnt} soru")

print()
# resmi_yazisma sorulari
rw = [r for r in recs if "resmi_yazisma" in r.get("kaynak_dokuman", "")]
print(f"resmi_yazisma soruları: {len(rw)}")
for r in rw[:5]:
    print(f"  {r['id']}: {r['soru'][:60]} -> {r['dogru_madde_no']}")

# 4982 sorulari
be = [r for r in recs if "4982" in r.get("kaynak_dokuman", "")]
print(f"\n4982 soruları: {len(be)}")
for r in be[:5]:
    print(f"  {r['id']}: {r['soru'][:60]} -> {r['dogru_madde_no']}")
