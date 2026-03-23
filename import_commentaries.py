import os
from pathlib import Path

SOURCE_DIR = Path("/Users/george/Documents/Spiritual/Refrence")
OUTPUT_DIR = Path("/Users/george/Library/Mobile Documents/com~apple~CloudDocs/Bible_Study_Aid/04_Commentaries")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_pdf_text(pdf_path):
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(str(pdf_path))
        if text and len(text.strip()) > 100:
            return text
    except Exception as e:
        print(f"PDFMiner failed on {pdf_path.name}: {e}")
    return ""

def fallback_ocr(pdf_path):
    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(pdf_path, first_page=1, last_page=20)
        text = ""

        for img in images:
            text += pytesseract.image_to_string(img)

        return text
    except Exception as e:
        print(f"OCR failed on {pdf_path.name}: {e}")
        return ""

def process_pdf(pdf_path):
    print(f"Processing: {pdf_path.name}")

    text = extract_pdf_text(pdf_path)

    if len(text.strip()) < 100:
        print(" -> Trying OCR fallback...")
        text = fallback_ocr(pdf_path)

    if len(text.strip()) < 100:
        print(" -> FAILED (no usable text)")
        return

    output_file = OUTPUT_DIR / (pdf_path.stem + ".txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f" -> WROTE: {output_file.name}")

def main():
    pdf_files = list(SOURCE_DIR.rglob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files.\n")

    for pdf in pdf_files:
        process_pdf(pdf)

    print("\nCommentary import complete.")

if __name__ == "__main__":
    main()