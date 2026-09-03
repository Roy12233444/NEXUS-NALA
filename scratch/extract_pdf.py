import pypdf

reader = pypdf.PdfReader('docs/Nexus_LAB_AI/claude-co-work.pdf')
with open('docs/Nexus_LAB_AI/claude_cowork_extracted_text.txt', 'w', encoding='utf-8') as f:
    for idx, page in enumerate(reader.pages):
        f.write(f"\n\n============================== PAGE {idx+1} ==============================\n")
        f.write(page.extract_text() or '')
        if '/Annots' in page:
            for annot in page['/Annots']:
                try:
                    obj = annot.get_object()
                    if '/A' in obj and '/URI' in obj['/A']:
                        f.write(f"\n[LINK FOUND]: {obj['/A']['/URI']}\n")
                except Exception as e:
                    pass
print("Extracted successfully.")
