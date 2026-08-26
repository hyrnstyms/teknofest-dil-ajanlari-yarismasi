import os
from docx import Document

dir_path = "ornek_dilekceler"

for filename in os.listdir(dir_path):
    if filename.endswith(".txt"):
        txt_path = os.path.join(dir_path, filename)
        docx_path = os.path.join(dir_path, filename.replace(".txt", ".docx"))
        
        doc = Document()
        
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                doc.add_paragraph(line.strip())
                
        doc.save(docx_path)
        print(f"Created {docx_path}")
