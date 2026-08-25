import pdfplumber
with pdfplumber.open('data/regulations/resmi_yazisma_yonetmeligi.pdf') as pdf:
    print(repr(pdf.pages[0].extract_text()[:200]))
