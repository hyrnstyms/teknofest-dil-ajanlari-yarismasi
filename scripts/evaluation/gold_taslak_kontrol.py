import json
import sys
import re
import os

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path for KAMUAI backend imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.app.official_writing.format_validator import validate_format


def parse_taslak_metni(metin: str) -> dict:
    """Metni basit kurallarla ayristirip validator'in bekledigi dict yapisina cevirir."""
    lines = [line.strip() for line in metin.splitlines() if line.strip()]
    taslak = {}
    
    if not lines:
        return taslak
        
    if len(lines) >= 3:
        taslak["tc_baslik"] = {
            "idare_adi": lines[1],
            "birim_adi": lines[2]
        }
    
    konu_idx = -1
    for i, line in enumerate(lines):
        if "Sayı:" in line:
            m = re.search(r'Sayı:\s*(\S+)', line)
            if m: taslak["sayi"] = m.group(1)
            
            m_tarih = re.search(r'(?:Tarih:\s*)?((\d{2}\.\d{2}\.\d{4})|(\d{1,2}\s+[a-zA-ZÇĞİÖŞÜçğıöşü]+\s+\d{4}))\s*$', line)
            if m_tarih:
                taslak["tarih"] = m_tarih.group(1).strip()
        elif "Tarih:" in line and "tarih" not in taslak:
            m = re.search(r'Tarih:\s*(.+)', line)
            if m: taslak["tarih"] = m.group(1).strip()
        if line.startswith("Konu:"):
            taslak["konu"] = line[5:].strip()
            konu_idx = i
            
    if konu_idx != -1 and konu_idx + 1 < len(lines):
        muhatap_line = lines[konu_idx + 1]
        if not muhatap_line.startswith("İlgi:"):
            if muhatap_line == "DAĞITIM YERLERİNE":
                taslak["muhatap"] = {"tur": "dagitim", "isim": ""}
            elif muhatap_line.startswith("Sayın "):
                taslak["muhatap"] = {"tur": "gercek_kisi", "isim": muhatap_line[6:]}
            else:
                taslak["muhatap"] = {"tur": "kurum", "isim": muhatap_line}
                
    ilgi_list = []
    for line in lines:
        if line.startswith("İlgi:"):
            m = re.search(r"İlgi:\s*(.*?)tarihli ve\s*(.*?)sayılı\s*(.*)\.", line)
            if m:
                ilgi_list.append({"tarih": m.group(1), "sayi": m.group(2), "aciklama": m.group(3)})
            else:
                ilgi_list.append({"tarih": "", "sayi": "", "aciklama": line.replace("İlgi: ", "")})
    if ilgi_list:
        taslak["ilgi"] = ilgi_list

    kapanis_phrases = ["arz ederim.", "rica ederim.", "arz ve rica ederim.", "Saygılarımla.", "İyi dileklerimle.", "Bilgilerinize sunulur.", "tekiden rica ederim."]
    kapanis_idx = -1
    for i in range(len(lines)-1, -1, -1):
        line_lower = lines[i].lower().replace("i̇", "i")
        for phrase in kapanis_phrases:
            phrase_lower = phrase.lower().replace("i̇", "i")
            if line_lower.endswith(phrase_lower):
                taslak["kapalis_ifadesi"] = phrase
                kapanis_idx = i
                break
        if kapanis_idx != -1:
            break
            
    if "kapalis_ifadesi" in taslak:
        k = taslak["kapalis_ifadesi"]
        if k == "arz ederim.": taslak["muhatap_turu"] = "kurum_ust"
        elif k == "rica ederim.": taslak["muhatap_turu"] = "kurum_alt"
        elif k == "arz ve rica ederim.": taslak["muhatap_turu"] = "kurum_karisik"
        elif k in ["Saygılarımla.", "İyi dileklerimle.", "Bilgilerinize sunulur."]: taslak["muhatap_turu"] = "gercek_kisi"
        elif k == "tekiden rica ederim.": taslak["muhatap_turu"] = "kurum_ust"
    
    if kapanis_idx != -1 and kapanis_idx + 2 < len(lines):
        ad_soyad_line = lines[kapanis_idx + 1]
        unvan_line = lines[kapanis_idx + 2]
        yetki_turu = "normal"
        vekil_makam = ""
        
        if unvan_line.endswith(" a."):
            yetki_turu = "yetki_devri"
            vekil_makam = unvan_line[:-3]
            if kapanis_idx + 3 < len(lines):
                unvan_line = lines[kapanis_idx + 3]
        elif unvan_line.endswith(" V."):
            yetki_turu = "vekaletname"
            vekil_makam = unvan_line[:-3]
            unvan_line = "Bilinmeyen Unvan"
            
        taslak["imza"] = {
            "ad_soyad": ad_soyad_line,
            "unvan": unvan_line,
            "yetki_turu": yetki_turu,
            "vekil_makam": vekil_makam
        }

    ekler = []
    for line in lines:
        if line.startswith("Ek:"):
            if "konulmadı" not in line and "adet" not in line:
                m = re.search(r"Ek:\s*(.*?)\s*\((.*?)\)", line)
                if m:
                    ekler.append({"ad": m.group(1), "bilgi": m.group(2)})
                else:
                    ekler.append({"ad": line.replace("Ek:", "").strip(), "bilgi": "Bilinmiyor"})
    if ekler:
        taslak["ekler"] = ekler
        
    taslak["metin_paragraflari"] = [metin]
    return taslak

def main():
    asl_dosya = str(_PROJECT_ROOT / 'data' / 'evaluation' / 'gold_taslaklar.jsonl')
    sablon_dosya = str(_PROJECT_ROOT / 'data' / 'evaluation' / 'gold_taslaklar_sablon.jsonl')
    
    hedef_dosya = asl_dosya if os.path.exists(asl_dosya) else sablon_dosya
    
    try:
        with open(hedef_dosya, 'r', encoding='utf-8') as f:
            lines = [line for line in f if line.strip()]
    except FileNotFoundError:
        print(f"HATA: {hedef_dosya} bulunamadi.")
        return

    toplam = 0
    gecen = 0
    
    for line in lines:
        data = json.loads(line)
        toplam += 1
        
        yazi_turu = data.get('yazi_turu')
        metin = data.get('taslak_metni', '')
        
        # Inform the user that bilgilendirme_yazisi uses ust_yazi validation
        if yazi_turu == "bilgilendirme_yazisi":
            yazi_turu = "ust_yazi"
            
        taslak_dict = parse_taslak_metni(metin)
        
        # If taslak_metni is empty, it will fail all checks, which is expected for templates
        # We can pass an empty dict to validator
        
        sonuc = validate_format(taslak_dict, yazi_turu)
        
        if sonuc.gecerli:
            print(f"{data['id']}: ✅ geçti")
            gecen += 1
        else:
            hata_mesajlari = " | ".join([f"[{h.kural_kodu}] {h.mesaj}" for h in sonuc.hatalar])
            print(f"{data['id']}: ❌ HATA — {hata_mesajlari}")
            
    kalan = toplam - gecen
    print(f"\n{toplam} taslaktan {gecen}'i geçti, {kalan}'i düzeltme gerektiriyor.")

if __name__ == "__main__":
    main()
