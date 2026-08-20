import json
from pathlib import Path
import re
from backend.app.ocr.ocr_service import OCRService

def normalize(text):
    trans = str.maketrans('IİÖÜÇĞŞ', 'ıiöüçğş')
    t = text.translate(trans).lower()
    t = re.sub(r'\s+', ' ', t).strip()
    return t

ocr_service = OCRService()
evraklar = {}
with open('data/evaluation/synthetic/evraklar.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        evraklar[data['id']] = data['metin']

images = list(Path('data/evaluation/ocr/temiz').glob('*.png'))[:5]

for img_path in images:
    doc_id = img_path.stem.split('_')[0]
    gold_text = evraklar.get(doc_id, '')
    
    ocr_text = ocr_service.extract_text_from_image(str(img_path))
    
    norm_gold = normalize(gold_text)
    norm_ocr = normalize(ocr_text)
    
    match = (norm_gold == norm_ocr)
    print(f"{doc_id}: Exact Match? {match}")
    if not match:
        print(f"  Gold len: {len(norm_gold)}, OCR len: {len(norm_ocr)}")
        for i in range(min(len(norm_gold), len(norm_ocr))):
            if norm_gold[i] != norm_ocr[i]:
                print(f"  Diff at {i}: Gold '{norm_gold[max(0,i-10):i+20]}' vs OCR '{norm_ocr[max(0,i-10):i+20]}'")
                break
