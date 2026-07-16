"""Root Cause Analysis report generator."""
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "windows"
os.chdir(os.path.dirname(__file__))

# ---- STEP 4: Search every Python file for transform calls ----
import re
from pathlib import Path

py_files = list(Path(".").rglob("*.py"))

search_patterns = [
    "fitInView\\(", "fit_in_view\\(", "scale\\(", "resetTransform\\(", 
    "setTransform\\(", "centerOn\\(", "setSceneRect\\(", "setFixedSize\\(", 
    "setMinimumSize\\(", "setMaximumSize\\(", "setGeometry\\(", "resize\\(", 
    "move\\(", "viewport\\(", "QGraphicsView", "QGraphicsScene", "QScrollArea", "QLabel",
    "fit_to_screen\\(", "fit_to_window\\(",
]

print("=" * 80)
print("STEP 4: SEARCH RESULTS - Transform & Layout calls")
print("=" * 80)

for pat in search_patterns[:16]:  # skip QLabel, QScrollArea (noisy)
    for f in py_files:
        content = f.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.split("\n"), 1):
            if re.search(pat, line) and not line.strip().startswith("#") and not line.strip().startswith('"""'):
                print(f"  {f}:{lineno}: {line.strip()}")

# ---- STEP 5: Compare implementations ----
print("\n" + "=" * 80)
print("STEP 5: COMPARISON - EditorCanvas vs _CardGraphicsView")
print("=" * 80)

from config.constants import CARD_WIDTH_PX, CARD_HEIGHT_PX, CARD_WIDTH_MM, CARD_HEIGHT_MM

editor_px_per_mm_x = CARD_WIDTH_PX / CARD_WIDTH_MM
editor_px_per_mm_y = CARD_HEIGHT_PX / CARD_HEIGHT_MM
preview_px_per_mm = 150 / 25.4

print(f"\n--- Resolution ---")
print(f"Editor px_per_mm: x={editor_px_per_mm_x:.4f}, y={editor_px_per_mm_y:.4f}")
print(f"Preview px_per_mm: {preview_px_per_mm:.4f}")

print(f"\n--- Card dimensions ---")
print(f"Card: {CARD_WIDTH_MM}mm x {CARD_HEIGHT_MM}mm")
print(f"Editor card rect: {CARD_WIDTH_PX}px x {CARD_HEIGHT_PX}px")
print(f"Preview canvas (150 DPI): round({CARD_WIDTH_MM}*{preview_px_per_mm:.4f}) = {round(CARD_WIDTH_MM*preview_px_per_mm)} x round({CARD_HEIGHT_MM}*{preview_px_per_mm:.4f}) = {round(CARD_HEIGHT_MM*preview_px_per_mm)}")
print(f"Full-res canvas (300 DPI): round({CARD_WIDTH_MM}*{300/25.4:.4f}) = {round(CARD_WIDTH_MM*300/25.4)} x round({CARD_HEIGHT_MM}*300/25.4) = {round(CARD_HEIGHT_MM*300/25.4)}")

print(f"\n--- Background with offset 8.56mm, 8.55mm, size 85.6mm x 54.0mm ---")
print(f"Editor: bg at ({0 + 8.56*editor_px_per_mm_x:.0f}, {0 + 8.55*editor_px_per_mm_y:.0f}), size ({85.6*editor_px_per_mm_x:.0f}, {54.0*editor_px_per_mm_y:.0f})")
print(f"  Card rect at (60, 60), size (600, 379)")
print(f"  bg_right_edge = {8.56*editor_px_per_mm_x + 85.6*editor_px_per_mm_x:.0f}, card_right_edge = 60 + 600 = 660")
print(f"  FIT: bg_right_edge == card_right_edge ({8.56*editor_px_per_mm_x + 85.6*editor_px_per_mm_x:.0f} == 660)")
print(f"Preview: bg at ({8.56*preview_px_per_mm:.0f}, {8.55*preview_px_per_mm:.0f}), size ({85.6*preview_px_per_mm:.0f}, {54.0*preview_px_per_mm:.0f})")
print(f"  Canvas: (0, 0), size ({85.6*preview_px_per_mm:.0f}, {54.0*preview_px_per_mm:.0f})")
bg_right = round(8.56*preview_px_per_mm) + round(85.6*preview_px_per_mm)
canvas_right = round(85.6*preview_px_per_mm)
print(f"  bg_right_edge = {bg_right}, canvas_right_edge = {canvas_right}")
print(f"  CLIPPED: bg_right_edge > canvas_right_edge ({bg_right} > {canvas_right}) - overflow = {bg_right - canvas_right}px")

print(f"\n--- Field location (x=64.91mm, w=25.68mm) ---")
print(f"Editor: x_px = {64.91*editor_px_per_mm_x:.0f}, right_edge = {(64.91+25.68)*editor_px_per_mm_x:.0f}")
card_right_px = 60 + CARD_WIDTH_PX
print(f"  Card rect right edge = {card_right_px}px")
print(f"  field_right_edge < card_right_edge: {(64.91+25.68)*editor_px_per_mm_x:.0f} < {card_right_px}")
print(f"Preview: x_px = {round(64.91*preview_px_per_mm)}, right_edge = {round((64.91+25.68)*preview_px_per_mm)}")
print(f"  Canvas right edge = {canvas_right}px")
print(f"  field_right_edge > canvas_right_edge: {round((64.91+25.68)*preview_px_per_mm)} > {canvas_right}")

print(f"\n--- Root Cause Analysis ---")
print(f"")
print(f"1. Which widget is clipping the card?")
print(f"   The PREVIEW IMAGE (PIL canvas) clips the card content, not the QGraphicsView.")
print(f"   The viewport shows the entire 506x319 image without clipping.")
print(f"   But the IMAGE itself has fields and background extending beyond its bounds.")
print(f"")
print(f"2. Which exact line of code causes it?")
print(f"   services/renderers/image_renderer.py:81: canvas.paste(resized, (bg_x_px, bg_y_px), resized)")
print(f"   The background is pasted at an offset ((51, 50) for tatheer template)")
print(f"   that causes it to extend BEYOND the canvas of (506, 319) pixels.")
print(f"   The rightmost 51px and bottommost 50px of the background are CLIPPED.")
print(f"")
print(f"3. Why does the Template Editor work correctly?")
print(f"   The Editor has a 60px scene margin (constant in editor_canvas.py:177).")
print(f"   The card rect is at (60, 60) with size (600, 379).")
print(f"   The background at (60, 60) with size (600, 379) EXACTLY fills the card rect.")
print(f"   The offset (8.56mm = 60px in editor px_per_mm) is ABSORBED by the scene margin.")
print(f"   No clipping occurs because the background matches the card rect.")
print(f"")
print(f"4. Why does the Card Generator fail?")
print(f"   The renderer creates a canvas with size = card dimensions in mm at DPI pixels.")
print(f"   The background offset (8.56mm, 8.55mm) is pasted at (51px, 50px) on this canvas.")
print(f"   Because the offset is applied from CANVAS ORIGIN (not from a scene margin):")
print(f"     bg_right_edge = 51 + 506 = 557")
print(f"     canvas_right_edge = 506")
print(f"     CLIPPED: 557 > 506 by 51px")
print(f"   The same issue affects field positioning - fields near the right/bottom edges")
print(f"   also extend beyond the canvas and are clipped by PIL.")
print(f"")
print(f"5. What evidence proves this?")
print(f"   a) debug_analyze.py output shows 7 fields extending beyond image bounds:")
print(f"      location right_edge=535 > img_width=506, bottom_edge=341 > img_height=319")
print(f"      employee_name right_edge=531 > img_width=506")
print(f"      ... and 5 more fields")
print(f"   b) The background at (8.56mm, 8.55mm) at 150 DPI = (51px, 50px) on 506x319 canvas:")
print(f"      bg_right=557 > canvas_right=506 (51px overflow)")
print(f"   c) The Editor has a 60px scene margin that absorbs this offset:")
print(f"      bg_at (60, 60) = card_rect_at (60, 60) → no overflow")
print(f"   d) Card IS fully visible in viewport (debug coords confirm it)")
print(f"   e) Transform correctly fits image to viewport (no viewport clipping)")
