import json
import random
import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

# Paths
BASE_DIR = Path(__file__).parent.parent.parent  # scripts/evaluation -> scripts -> proje kökü
EVRAKLAR_PATH = BASE_DIR / "data" / "synthetic" / "evraklar.jsonl"
OUT_DIR = BASE_DIR / "data" / "synthetic" / "ocr_gorseller"

# Platform bağımsız font tespiti
def _find_font() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\arial.ttf",           # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Ubuntu/Debian
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

FONT_PATH = _find_font()
if FONT_PATH is None:
    print("[UYARI] Uygun font bulunamadı; PIL varsayılan fontu kullanılacak.")

random.seed(42)
np.random.seed(42)

def load_evraklar():
    evraklar = []
    with open(EVRAKLAR_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                evraklar.append(json.loads(line))
    return evraklar

def select_samples(evraklar, samples_per_type=12):
    by_type = {}
    for evrak in evraklar:
        t = evrak.get("evrak_turu_dogru")
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(evrak)
    
    selected = []
    for t, docs in by_type.items():
        if len(docs) >= samples_per_type:
            selected.extend(random.sample(docs, samples_per_type))
        else:
            selected.extend(docs)
    
    random.shuffle(selected)
    return selected

def add_salt_and_pepper_noise(image, amount=0.02):
    # Convert image to numpy array
    img_arr = np.array(image)
    
    # Create mask for salt and pepper
    row, col, ch = img_arr.shape
    num_salt = np.ceil(amount * img_arr.size * 0.5)
    num_pepper = np.ceil(amount * img_arr.size * 0.5)
    
    # Add Salt noise
    coords = [np.random.randint(0, i - 1, int(num_salt)) for i in img_arr.shape[:2]]
    img_arr[tuple(coords)] = 255
    
    # Add Pepper noise
    coords = [np.random.randint(0, i - 1, int(num_pepper)) for i in img_arr.shape[:2]]
    img_arr[tuple(coords)] = 0
    
    return Image.fromarray(img_arr)

def draw_text_wrapped(draw, text, font, max_width, start_x, start_y):
    lines = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        words = paragraph.split()
        current_line = words[0] if words else ""
        for word in words[1:]:
            # Get text bounding box for the line + new word
            bbox = draw.textbbox((0, 0), current_line + " " + word, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    
    y = start_y
    for line in lines:
        if line:
            draw.text((start_x, y), line, font=font, fill="black")
        y += font.size + int(font.size * 0.5)  # Line spacing
    return y

def create_base_image(text):
    # A4 proportions (approx 1240 x 1754 for 150 dpi)
    width, height = 1240, 1754
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype(FONT_PATH, 24)
    except Exception as e:
        print(f"Error loading font {FONT_PATH}: {e}")
        font = ImageFont.load_default()
        
    margin = 100
    max_width = width - (2 * margin)
    
    draw_text_wrapped(draw, text, font, max_width, margin, margin)
    return img

def apply_orta_kalite(img):
    # Slight rotation (1-3 degrees) and slight Gaussian blur
    angle = random.uniform(-3, 3)
    if abs(angle) < 1:
        angle = 1.0 if angle >= 0 else -1.0
    img = img.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor='white')
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.0)))
    return img

def apply_zor_kalite(img):
    # Prominent rotation (3-7 degrees), noticeable blur, contrast reduction, noise
    angle = random.uniform(-7, 7)
    if abs(angle) < 3:
        angle = 3.0 if angle >= 0 else -3.0
    img = img.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor='white')
    img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(1.5, 2.5)))
    
    # Contrast reduction
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(random.uniform(0.4, 0.7))
    
    # Add salt and pepper noise
    img = add_salt_and_pepper_noise(img, amount=random.uniform(0.01, 0.03))
    return img

def main():
    print("Loading evraklar...")
    evraklar = load_evraklar()
    
    # Target 60-80 images, distributed in 3 tiers. 
    # Say we take 12 samples per 6 types = 72 total.
    selected = select_samples(evraklar, samples_per_type=12)
    print(f"Selected {len(selected)} samples for OCR generation.")
    
    # Split into 3 chunks for 3 quality tiers
    chunk_size = math.ceil(len(selected) / 3)
    chunks = [selected[i:i+chunk_size] for i in range(0, len(selected), chunk_size)]
    
    tiers = [
        ("temiz", lambda img: img),
        ("orta_kalite", apply_orta_kalite),
        ("zor", apply_zor_kalite)
    ]
    
    for tier_name, _ in tiers:
        (OUT_DIR / tier_name).mkdir(parents=True, exist_ok=True)
    
    for i, (tier_name, transform_fn) in enumerate(tiers):
        chunk = chunks[i] if i < len(chunks) else []
        print(f"Generating {len(chunk)} images for tier: {tier_name}")
        
        for evrak in chunk:
            evrak_id = evrak["id"]
            metin = evrak.get("metin", "")
            
            base_img = create_base_image(metin)
            final_img = transform_fn(base_img)
            
            out_path = OUT_DIR / tier_name / f"{evrak_id}_{tier_name}.png"
            final_img.save(out_path)
            
    print("OCR image generation complete.")

if __name__ == "__main__":
    main()
