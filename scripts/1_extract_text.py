import os
from PyPDF2 import PdfReader

input_folder = "data/laws"
output_path = "embeddings/all_text.txt"

os.makedirs("embeddings", exist_ok=True)
all_text = ""

for filename in os.listdir(input_folder):
    if filename.endswith(".pdf"):
        reader = PdfReader(os.path.join(input_folder, filename))
        for page in reader.pages:
            all_text += page.extract_text() + "\n"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(all_text)

print("✅ Text extracted and saved.")
