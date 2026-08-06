import os
import re
import tempfile
from pypdf import PdfReader, PdfWriter
from math import floor
from reportlab.pdfgen import canvas

PAGE_W = 12                    # inches
PAGE_H = 18
CARD_W = 3.9            # inches
CARD_H = 2.5
DPI = 300

COLS = 3
ROWS = 7

TEXT_OFFSET_X = 15  # Padding from the right edge
TEXT_OFFSET_Y = 10  # Padding from the bottom edge
FONT_SIZE = 8       # Size of the set number text
BG_WIDTH = 18       # Width of the white background box
BG_HEIGHT = 10      # Height of the white background box

PT = 72
PAGE_W_PT = PAGE_W * PT
PAGE_H_PT = PAGE_H * PT
CARD_W_PT = CARD_W * PT
CARD_H_PT = CARD_H * PT

GRID_W = COLS * CARD_W_PT
GRID_H = ROWS * CARD_H_PT
START_X = (PAGE_W_PT - GRID_W) / 2
START_Y = (PAGE_H_PT - GRID_H) / 2
PER_PAGE = COLS * ROWS

def generate_layout(start_set: int, end_set: int, images_dir: str):
    folders = []
    for item in os.listdir(images_dir):
        folder_path = os.path.join(images_dir, item)
        if os.path.isdir(folder_path) and not item.startswith("."):
            if any(f.lower().endswith(".png") for f in os.listdir(folder_path)):
                folders.append(folder_path)

    folders.sort()

    pairs = []
    for folder_path in folders:
        files = sorted(
            [f for f in os.listdir(folder_path) if f.lower().endswith(".png")],
            key=lambda x: [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', os.path.splitext(x)[0])]
        )
        
        # pair them up for this folder
        for i in range(0, len(files), 2):
            front = os.path.join(folder_path, files[i])
            back = None
            if i + 1 < len(files):
                back = os.path.join(folder_path, files[i + 1])
            pairs.append((front, back))

    if not pairs:
        raise Exception(f"No .png images found in subfolders of {images_dir}")

    # --- PRE-GENERATE BACK PAGES ---
    backs_pdf = tempfile.TemporaryFile()
    c_backs = canvas.Canvas(backs_pdf, pagesize=(PAGE_W_PT, PAGE_H_PT))
    for start in range(0, len(pairs), PER_PAGE):
        current_pairs = pairs[start:start + PER_PAGE]
        for idx, (front, back) in enumerate(current_pairs):
            row = idx // COLS
            col = idx % COLS
            
            y = PAGE_H_PT - START_Y - ((row + 1) * CARD_H_PT)
            x_front = START_X + (col * CARD_W_PT)
            mirrored_x = PAGE_W_PT - x_front - CARD_W_PT
            
            if back:
                c_backs.drawImage(
                    back, mirrored_x, y,
                    width=CARD_W_PT, height=CARD_H_PT,
                    preserveAspectRatio=False, mask='auto'
                )
        c_backs.showPage()
    c_backs.save()
    backs_pdf.seek(0)
    backs_reader = PdfReader(backs_pdf)

    # --- PRE-GENERATE FRONT BASE PAGES ---
    fronts_base_pdf = tempfile.TemporaryFile()
    c_fronts = canvas.Canvas(fronts_base_pdf, pagesize=(PAGE_W_PT, PAGE_H_PT))
    for start in range(0, len(pairs), PER_PAGE):
        current_pairs = pairs[start:start + PER_PAGE]
        for idx, (front, back) in enumerate(current_pairs):
            row = idx // COLS
            col = idx % COLS
            
            x = START_X + (col * CARD_W_PT)
            y = PAGE_H_PT - START_Y - ((row + 1) * CARD_H_PT)
            
            c_fronts.drawImage(
                front, x, y,
                width=CARD_W_PT, height=CARD_H_PT,
                preserveAspectRatio=False, mask='auto'
            )
        c_fronts.showPage()
    c_fronts.save()

    # --- GENERATE FINAL DOCUMENT ---
    final_writer = PdfWriter()

    for set_num in range(start_set, end_set + 1):
        # Create Overlay PDF (just the text numbers)
        overlay_pdf = tempfile.TemporaryFile()
        c_overlay = canvas.Canvas(overlay_pdf, pagesize=(PAGE_W_PT, PAGE_H_PT))
        
        for start in range(0, len(pairs), PER_PAGE):
            current_pairs = pairs[start:start + PER_PAGE]
            for idx, (front, back) in enumerate(current_pairs):
                row = idx // COLS
                col = idx % COLS
                
                x = START_X + (col * CARD_W_PT)
                y = PAGE_H_PT - START_Y - ((row + 1) * CARD_H_PT)
                
                # Draw set number on front (bottom right)
                c_overlay.saveState()
                c_overlay.translate(x + CARD_W_PT - TEXT_OFFSET_X, y + TEXT_OFFSET_Y)
                c_overlay.setFillColorRGB(1, 1, 1)
                c_overlay.rect(-BG_WIDTH/2, -BG_HEIGHT/4, BG_WIDTH, BG_HEIGHT, fill=1, stroke=0)
                c_overlay.setFillColorRGB(0, 0, 0)
                c_overlay.setFont("Helvetica-Bold", FONT_SIZE)
                c_overlay.drawCentredString(0, 0, str(set_num))
                c_overlay.restoreState()
            c_overlay.showPage()
        
        c_overlay.save()
        overlay_pdf.seek(0)
        overlay_reader = PdfReader(overlay_pdf)
        
        # Re-read fresh base fronts
        fronts_base_pdf.seek(0)
        fronts_base_reader = PdfReader(fronts_base_pdf)
        
        for i in range(len(fronts_base_reader.pages)):
            front_page = fronts_base_reader.pages[i]
            overlay_page = overlay_reader.pages[i]
            front_page.merge_page(overlay_page)
            
            final_writer.add_page(front_page)
            final_writer.add_page(backs_reader.pages[i])
            
    final_output = tempfile.TemporaryFile()
    final_writer.write(final_output)
    final_output.seek(0)
    
    return final_output
