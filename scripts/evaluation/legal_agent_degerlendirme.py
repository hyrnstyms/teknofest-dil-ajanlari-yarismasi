"""
scripts/evaluation/legal_agent_degerlendirme.py
-------------------------------------------------
Legal Agent'i 45 soruluk RAG test setiyle degerlendirir.

Calistirma:
    python -m scripts.evaluation.legal_agent_degerlendirme
"""
import sys
import json
import re
import unicodedata

# Force UTF-8 output on Windows
# Removed sys.stdout wrapper

sys.path.insert(0, ".")

from backend.app.agents.legal_agent import LegalAgent

# --- Yardimci Fonksiyonlar ---

def normalize_madde_no(raw: str) -> str:
    """'Madde 3', '3-', '3.', '3' -> canonical '3'"""
    if not raw:
        return ""
    s = str(raw).strip()
    s = re.sub(r"(?i)madde\s*", "", s)
    s = s.rstrip(".-").strip()
    return s.upper()


def normalize_text_for_check(text: str) -> str:
    """Whitespace+lower+unicode normalize."""
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.lower().split())


def evidence_in_source(evidence_text: str, sources: list) -> bool:
    """Evidence metni, ajanin donurdugu retrieved_sources icinde geciyor mu?"""
    norm_ev = normalize_text_for_check(evidence_text)
    if not norm_ev:
        return False
    for src in sources:
        src_text = normalize_text_for_check(src.get("text", "") or "")
        if norm_ev in src_text:
            return True
    return False


def get_agent_madde_no(result: dict) -> str | None:
    """Ajanin donurdugu result dict'inden madde_no cikarir."""
    retrieved = result.get("retrieved_sources", [])
    if retrieved:
        return normalize_madde_no(
            str(retrieved[0].get("madde_no", "") or "")
        )
    return None


# --- Ana Degerlendirme ---

def main():
    print("Legal Agent Degerlendirme Baslatiliyor...")
    print("Qdrant'a baglaniliyor ve embedding servisi yukleniyor...\n")

    agent = LegalAgent()

    with open(
        "data/evaluation/legal/rag_test_seti.jsonl",
        encoding="utf-8",
    ) as f:
        records = [json.loads(l) for l in f if l.strip()]

    print(f"Toplam soru: {len(records)}\n")
    print("=" * 70)

    results_log = []
    matched = 0
    mismatched = 0
    empty_results = 0

    eval_records = [r for r in records if r.get("dogrulama_durumu") != "insan_dogrulamasi_gerekli"]
    special_records = [r for r in records if r.get("dogrulama_durumu") == "insan_dogrulamasi_gerekli"]

    print(f"Degerlendirme kapsami: {len(eval_records)} soru")
    print(f"Ozel durum (insan_dogrulamasi_gerekli): {len(special_records)} soru\n")

    for i, rec in enumerate(eval_records, 1):
        soru_id = rec.get("id", f"Q{i}")
        soru = rec.get("soru", "")
        dogru_madde = normalize_madde_no(rec.get("dogru_madde_no", ""))
        zorluk = rec.get("zorluk", "?")

        try:
            result = agent.analyze(query=soru, top_k=5)
        except Exception as e:
            print(f"[HATA] [{soru_id}] {e}")
            results_log.append({
                "id": soru_id,
                "zorluk": zorluk,
                "sonuc": "HATA",
                "ajan_madde": None,
                "dogru_madde": dogru_madde,
                "soru": soru,
            })
            empty_results += 1
            continue

        agent_madde = get_agent_madde_no(result)
        retrieval_score = result.get("retrieval_score", 0.0)

        evidence_list = result.get("evidence", [])
        all_evidence_in_source = True
        bad_evidence = []
        for ev_item in evidence_list:
            ev_text = ev_item.get("evidence", "")
            if not evidence_in_source(ev_text, result.get("retrieved_sources", [])):
                all_evidence_in_source = False
                bad_evidence.append(ev_text[:80])

        if not agent_madde:
            status = "BOS"
            empty_results += 1
        elif agent_madde == dogru_madde:
            status = "ESLESTI"
            matched += 1
        else:
            status = "FARKLI"
            mismatched += 1

        prefix = "[OK]" if status == "ESLESTI" else ("[?]" if status == "BOS" else "[X]")
        ev_warn = " [EV_UYARISIZLIK]" if bad_evidence else ""
        print(
            f"{prefix} [{soru_id}] {zorluk:8} | "
            f"Beklenen: {dogru_madde:18} | "
            f"Ajan: {str(agent_madde):18} | "
            f"Score: {retrieval_score:.3f} | {status}{ev_warn}"
        )
        if bad_evidence:
            for b in bad_evidence:
                print(f"     UYARI Kaynak disi evidence: '{b}...'")

        results_log.append({
            "id": soru_id,
            "zorluk": zorluk,
            "sonuc": status,
            "ajan_madde": agent_madde,
            "dogru_madde": dogru_madde,
            "retrieval_score": retrieval_score,
            "evidence_count": len(evidence_list),
            "all_evidence_in_source": all_evidence_in_source,
            "bad_evidence": bad_evidence,
            "soru": soru,
        })

    # --- ADIM 4: RAG-035 Ozel Testi ---
    print("\n" + "=" * 70)
    print("ADIM 4 -- RAG-035 Ozel Durum Testi (insan_dogrulamasi_gerekli)")
    print("=" * 70)

    for rec in special_records:
        soru_id = rec.get("id")
        soru = rec.get("soru", "")
        dogru_madde = normalize_madde_no(rec.get("dogru_madde_no", ""))
        print(f"\nSoru ({soru_id}): {soru}")
        print(f"Beklenen madde: {dogru_madde}")

        result = agent.analyze(query=soru, top_k=5)
        agent_madde = get_agent_madde_no(result)
        retrieval_score = result.get("retrieval_score", 0.0)
        answer = result.get("answer", "")
        evidence_list = result.get("evidence", [])

        print(f"Ajan madde: {agent_madde} (retrieval_score={retrieval_score:.3f})")
        print(f"Ajan cevabi: {answer[:300]}")
        print(f"Evidence sayisi: {len(evidence_list)}")
        if evidence_list:
            for ev in evidence_list:
                print(f"  - '{ev.get('evidence', '')[:100]}'")

        if not evidence_list:
            print("UYARI RAG-035: Ajan hic evidence uretemedi -> 'bilmiyorum' davranisi")
        elif agent_madde != dogru_madde:
            print(f"UYARI RAG-035: Ajan yanlis madde verdi ({agent_madde} != {dogru_madde})")
        else:
            print(f"OK RAG-035: Ajan dogru maddeyi buldu ({agent_madde})")

    # --- ADIM 5: Halusinasyon Testi ---
    print("\n" + "=" * 70)
    print("ADIM 5 -- Halusinasyon Testi (Mevzuatta Olmayan Madde)")
    print("=" * 70)

    halusinasyon_sorulari = [
        "Resmi yazismalarda kullanilan yazi tipi buyuklugu Madde 99'da mi tanimlanir?",
        "4982 sayili Kanun'un Madde 150'si vatandaslarin sikayet haklarini duzenler mi?",
    ]

    for halusinasyon_sorusu in halusinasyon_sorulari:
        print(f"\nTest sorusu: {halusinasyon_sorusu}")
        result = agent.analyze(query=halusinasyon_sorusu, top_k=5)
        agent_madde = get_agent_madde_no(result)
        retrieval_score = result.get("retrieval_score", 0.0)
        answer = result.get("answer", "")
        evidence_list = result.get("evidence", [])

        print(f"Ajan madde: {agent_madde} (retrieval_score={retrieval_score:.3f})")
        print(f"Ajan cevabi: {answer[:300]}")
        print(f"Evidence sayisi: {len(evidence_list)}")
        if evidence_list:
            for ev in evidence_list:
                print(f"  - '{ev.get('evidence', '')[:100]}'")
        else:
            print("OK Ajan hic evidence uretemedi -- halusin asyon yok")

    # --- Ozet ---
    print("\n" + "=" * 70)
    print("GENEL DOGRULUK OZETI")
    print("=" * 70)
    toplam = len(eval_records)
    print(f"Degerlendirilen soru: {toplam}")
    print(f"  [OK] ESLESTI  : {matched}")
    print(f"  [X]  FARKLI   : {mismatched}")
    print(f"  [?]  BOS/HATA : {empty_results}")
    if toplam > 0:
        print(f"  Dogruluk      : {matched}/{toplam} = {matched/toplam*100:.1f}%")

    for zorluk_seviye in ["kolay", "orta", "zor"]:
        grp = [r for r in results_log if r["zorluk"] == zorluk_seviye]
        if grp:
            grp_matched = sum(1 for r in grp if r["sonuc"] == "ESLESTI")
            print(f"  {zorluk_seviye:8}: {grp_matched}/{len(grp)}")

    failures = [r for r in results_log if r["sonuc"] in ("FARKLI", "BOS", "HATA")]
    if failures:
        print(f"\nHatali sorular ({len(failures)}):")
        for r in failures:
            print(f"  [{r['id']}] {r['zorluk']:8} | Beklenen: {r['dogru_madde']:18} | Ajan: {str(r['ajan_madde'])}")

    out_path = "scripts/evaluation/legal_agent_sonuclari.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_log, f, ensure_ascii=False, indent=2)
    print(f"\nDetayli sonuclar kaydedildi: {out_path}")


if __name__ == "__main__":
    main()
