import os
from PyPDF2 import PdfReader

def pdf_to_text_file(pdf_path):
    # Extract base name and prepare output path
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(os.path.dirname(pdf_path), f"{base_name}.txt")

    # Read PDF and extract text
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    # Save text to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ Text saved to: {output_path}")

# Example usage from CLI
if __name__ == "__main__":
    pdf_to_text_file("/home/omkar/Documents/IITB-KG/3_engine_fundamentals.pdf")
