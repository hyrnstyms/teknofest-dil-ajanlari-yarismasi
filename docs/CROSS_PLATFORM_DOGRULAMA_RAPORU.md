# Cross-platform backend doğrulama raporu

Tarih: 26 Ağustos 2026  
Dal: `final-db-persistence`  
Doğrulanan kod commit'i: `aa98f62`  
GitHub Actions: <https://github.com/hyrnstyms/teknofest-dil-ajanlari-yarismasi/actions/runs/33002940951>

## Nihai karar

**CROSS-PLATFORM BLOCKER**

Python 3.12 venv, tek `requirements.txt`, uygulama importu,
`uvicorn --reload`, sade pytest komutu ve Türkçe Unicode testi gerçek macOS ve
Windows ortamlarında başarılıdır. Ancak GitHub-hosted Windows Server 2025
runner yalnız Windows container daemon'u sağladığı için Linux tabanlı
`postgres:16` ve `qdrant/qdrant` imajlarını çalıştıramamıştır. Bu nedenle Windows
üzerinde Docker Compose servisleri ile gerçek PostgreSQL Unicode round-trip bu
çalışmada doğrulanamamıştır. Docker Desktop Linux containers moduna sahip fiziksel
bir Windows/VM sonucu alınmadan “CROSS-PLATFORM READY” onayı verilmemelidir.

## 1. Platform bağımlılığı taraması

Kapsam: `backend/app/**`, `backend/tests/**`, `scripts/**` altındaki tüm Python
dosyaları. AST taraması ile importlar, platform API'leri, subprocess seçenekleri,
metin I/O encoding'i ve Windows absolute path sabitleri kontrol edildi; ayrıca
`rg` ile ikinci tarama yapıldı.

Ham sonuç:

```text
readline: 0
unix_api: 0
shell_true: 0
text_encoding: 0
hardcoded_windows_path: 0
backend/app/ingestion/doc_loader.py:96:    result = subprocess.run(
```

Sonuç: **DÜZELTİLDİ**.

- `readline`, `os.fork`, Unix-only sinyal, `chmod` mantığı ve `shell=True` yoktur.
- Tek subprocess çağrısı argüman listesiyle ve `shell=False` varsayılanıyla
  çalışır; metin çıktısı `encoding="utf-8", errors="replace"` ile okunur.
- LibreOffice ve OCR font konumları `Path` ile oluşturulur; sabit `C:\...` veya
  `/...` dosya yolu kalmamıştır.
- Test SQLite URL'leri Windows drive harflerinde geçerli olması için
  `Path.as_posix()` ile üretilir.
- Metin dosyalarının tüm `open`, `Path.read_text` ve `Path.write_text`
  çağrılarında açık `encoding="utf-8"` vardır. Binary I/O encoding almaz.

## 2. Gerçek ortam sonuçları

### a. Docker Compose: PostgreSQL ve Qdrant

macOS komutu:

```text
docker compose up -d postgres qdrant
docker compose ps
docker compose exec -T postgres pg_isready -U kamuai -d kamuai
curl --fail --silent --show-error http://127.0.0.1:6333/healthz
```

macOS ham çıktı:

```text
NAME                    IMAGE                  SERVICE    STATUS
teknofestt-postgres-1   postgres:16            postgres   Up 23 minutes (healthy)
teknofestt-qdrant-1     qdrant/qdrant:latest   qdrant     Up 23 minutes (healthy)
/var/run/postgresql:5432 - accepting connections
healthz check passed
```

macOS sonucu: **SORUN YOK**. PostgreSQL ayrıca `server_encoding=UTF8` döndürdü.

Windows Server 2025 / `windows-latest` komutu:

```powershell
docker compose up -d postgres qdrant
```

Windows ham çıktı:

```text
qdrant Pulling
postgres Pulling
no matching manifest for windows(10.0.26100)/amd64 in the manifest list entries
Error: Process completed with exit code 1.
```

Windows sonucu: **DÜZELTME GEREKİYOR (DOĞRULAMA ORTAMI BLOCKER'I)**. Compose
dosyasından kaynaklanan bir YAML/config hatası görülmedi; Windows hosted runner
Linux container çalıştırmadığı için imaj seçimi aşamasında durdu. README Windows
talimatı bu nedenle Docker Desktop'ın Linux containers modunu açıkça şart koşar.

### b. Python 3.12 venv

macOS runner komutu ve ham çıktı:

```text
python -m venv venv
source venv/bin/activate
Python 3.12.10
```

Windows runner komutu ve ham çıktı:

```text
python -m venv venv
.\venv\Scripts\Activate.ps1
Python 3.12.10
```

Sonuç: macOS **SORUN YOK**, Windows **SORUN YOK**.

### c. Tek requirements.txt kurulumu

Her iki runner'da aynı komut:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS ham sonuç:

```text
Successfully installed ... paddleocr-3.7.0 paddlepaddle-3.3.1
... psycopg-3.3.4 psycopg-binary-3.3.4 ...
```

Windows ham sonuç:

```text
Using cached paddlepaddle-3.3.1-cp312-cp312-win_amd64.whl (104.8 MB)
Using cached psycopg_binary-3.3.4-cp312-cp312-win_amd64.whl (3.6 MB)
Successfully installed ... paddleocr-3.7.0 paddlepaddle-3.3.1
... psycopg-3.3.4 psycopg-binary-3.3.4 ...
```

Sonuç: macOS **SORUN YOK**, Windows **SORUN YOK**. Windows'ta ilgili paketler
wheel olarak kuruldu; Visual C++ Build Tools veya platform marker'ı gerekmedi.
Yerel macOS venv'de `python -m pip check` çıktısı:

```text
No broken requirements found.
```

### d. Uvicorn reload modu

Her iki platformda çalıştırılan uygulama komutu:

```text
python -m uvicorn backend.app.main:app --reload --port 8010
```

macOS ham çıktı:

```text
INFO:     Uvicorn running on http://127.0.0.1:8010 (Press CTRL+C to quit)
INFO:     Application startup complete.
{"status":"ok","message":"KAMUAI API çalışıyor."}
```

Windows ham sağlık çıktısı:

```text
KAMUAI MVP API
{"status":"ok","message":"KAMUAI API çalışıyor."}
```

Sonuç: macOS **SORUN YOK**, Windows **SORUN YOK**.

### e. Sade test komutu

Her iki venv'de, test davranışını değiştiren env-var olmadan çalıştırılan komut:

```text
python -m pytest backend/tests -q
```

macOS ham çıktı:

```text
410 passed, 1 skipped, 24 warnings in 46.60s
```

Windows ham çıktı:

```text
410 passed, 1 skipped, 18 warnings in 118.50s (0:01:58)
```

Sonuç: macOS **SORUN YOK**, Windows **SORUN YOK**. Temiz checkout'ta `.env`
olmadan ortaya çıkan eski `evren` kod varsayılanı `.env.example` ile uyumlu
olacak biçimde `ollama` yapılarak **DÜZELTİLDİ**.

Yerel macOS'ta commit arşivi ayrı geçici dizine açılarak `.env` olmadan aynı sade
komut ayrıca çalıştırıldı:

```text
410 passed, 1 skipped, 24 warnings in 47.73s
```

Bu çalıştırmada host shell'in geçersiz `C.UTF-8` değeri için yalnız `tar` locale
uyarısı görüldü; Python/pytest çökmedi ve `LANG`/`LC_ALL` değişkeni verilmedi.

### f. Türkçe karakter round-trip

Test edilen değerler arasında şunlar vardır:

```text
Çığ, şüphe, ılık göl ve üzüm
ç, ş, ğ, ı, ö, ü ve büyükleri Ç, Ş, Ğ, İ, Ö, Ü
```

macOS gerçek PostgreSQL komutu ve ham çıktı:

```bash
TEST_DATABASE_URL="$(sed -n 's/^DATABASE_URL=//p' .env)" \
  python -m pytest backend/tests/test_db_repository.py \
  -k turkish_unicode_round_trip -vv
backend/tests/test_db_repository.py::test_turkish_unicode_round_trip PASSED
1 passed, 5 deselected in 0.25s
```

Windows venv/SQLite ham çıktı:

```text
platform win32 -- Python 3.12.10 -- ...\venv\Scripts\python.exe
backend/tests/test_db_repository.py::test_turkish_unicode_round_trip PASSED
```

Sonuç: macOS gerçek PostgreSQL **SORUN YOK**; Windows dosya/JSON/SQLite Unicode
round-trip **SORUN YOK**; Windows gerçek PostgreSQL **DÜZELTME GEREKİYOR** çünkü
Docker servisi hosted runner'da başlayamadı. Bu eksik doğrulama final blocker'dır.

## 3. Ortak ve platforma özel ayarlar

Sonuç: **SORUN YOK**.

- Tek `requirements.txt`, tek `docker-compose.yml`, tek `.env.example` korunmuştur.
- Paketlerde platform marker/fork gerekmedi; aynı pin'ler iki Python runner'ında
  kuruldu.
- Compose'un eski `version` alanı kaldırıldı; Postgres ve Qdrant'a ortak
  healthcheck eklendi.
- macOS `LANG=C` / `LC_ALL=C` notu yalnız macOS bölümündedir ve yalnız belirli
  Conda Python 3.13 + geçersiz host locale birleşimi için opsiyoneldir.
- Windows activation/execution-policy notu yalnız Windows bölümündedir; execution
  policy değiştirmek zorunlu değildir.

## 4. README ve sürekli doğrulama

Sonuç: **DÜZELTİLDİ**.

- README tek “Kurulum” başlığı altında ortak Docker, macOS, Windows ve ortak test
  bölümlerine ayrıldı.
- `.github/workflows/cross-platform-backend.yml` her push/PR'da macOS-14 ve
  Windows-latest üzerinde gerçek venv, ortak dependency kurulumu, import,
  `uvicorn --reload`, tam test ve Unicode testini çalıştırır.
- Windows Docker probe ayrı job'dur; Python başarısını Docker altyapı sonucuyla
  karıştırmaz ve daemon/image hatasını gizlemez.

## Kapatma ölçütü

Windows 10/11 veya Windows VM üzerinde Docker Desktop **Linux containers** modunda
aşağıdaki üç doğrulama ham çıktıyla başarıyla alınmalıdır:

```text
docker compose up -d postgres qdrant
docker compose ps
$env:TEST_DATABASE_URL = "postgresql+psycopg://kamuai:kamuai@127.0.0.1:5432/kamuai"
python -m pytest backend/tests/test_db_repository.py -k turkish_unicode_round_trip -vv
```

İki servis `healthy` ve son test gerçek `TEST_DATABASE_URL` ile `PASSED` olmadan
nihai durum **CROSS-PLATFORM BLOCKER** olarak kalır.
