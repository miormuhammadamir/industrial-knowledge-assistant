import fitz

def extract_pages(path):
    with fitz.open(path) as pdf:
        if pdf.needs_pass: raise ValueError('Password-protected PDFs are not supported')
        result=[(i+1,' '.join(page.get_text().split())) for i,page in enumerate(pdf)]
        if not any(text for _,text in result): raise ValueError('No extractable text. OCR is not supported in v1')
        return result

def validate_pdf(path):
    with open(path,'rb') as f:
        if f.read(5)!=b'%PDF-': raise ValueError('Invalid PDF signature')
    with fitz.open(path) as pdf:
        if pdf.needs_pass: raise ValueError('Password-protected PDF')
        if pdf.page_count<1: raise ValueError('Empty PDF')
