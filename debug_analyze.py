"""Analyze screenshots pixel-by-pixel to determine if card is clipped."""
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "windows"

os.chdir(os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QImage

from views.main_window import MainWindow

app = QApplication(sys.argv)
app.setStyle("Fusion")

# Minimal stylesheet
stylesheet = """
QMainWindow, QWidget { background-color: #f8f9fa; }
#viewContent { background-color: #ffffff; }
#previewPanel { background-color: #ffffff; }
"""
app.setStyleSheet(stylesheet)

window = MainWindow()
window._navigate_to(1)
window.resize(1400, 900)
window.show()
app.processEvents()

gen_view = window._card_generator_view

# Select template
gen_view._template_combo.setCurrentIndex(1)
gen_view._template_combo.currentIndexChanged.emit(1)
app.processEvents()

import time
time.sleep(0.3)
app.processEvents()

for field_name, value in [
    ("employee_name", "John Doe"),
    ("employee_designation", "Engineer"),
    ("employee_no", "EMP-001"),
    ("date_of_birth", "15-08-1990"),
    ("cnic", "12345-6789012-3"),
    ("employee_category", "Permanent"),
    ("blood_group", "A+"),
    ("location", "Head Office"),
    ("dependents", "Self, Spouse"),
]:
    gen_view._binding_manager.set_field(field_name, value)

app.processEvents()
time.sleep(0.3)
app.processEvents()

def analyze():
    front = gen_view._front_preview
    view = front._view
    vp = view.viewport()
    
    # Captures with a RED BORDER drawn around the card
    # First, draw border on a copy of the viewport pixmap
    vp_pm = vp.grab()
    
    # Draw a red rectangle around the card in scene coords, mapped to viewport
    painter = QPainter(vp_pm)
    painter.setPen(QPen(QColor(255, 0, 0), 2))
    
    scene_rect = view._pixmap_item.boundingRect()
    tl_scene = scene_rect.topLeft()
    br_scene = scene_rect.bottomRight()
    
    tl_vp = view.mapFromScene(tl_scene)
    br_vp = view.mapFromScene(br_scene)
    
    vp_rect = QRect(tl_vp, br_vp)
    painter.drawRect(vp_rect)
    
    # Also draw the viewport bounds
    painter.setPen(QPen(QColor(0, 255, 0), 1))
    painter.drawRect(0, 0, vp_pm.width() - 1, vp_pm.height() - 1)
    
    painter.end()
    
    marked_path = "debug_marked.png"
    vp_pm.save(marked_path)
    print(f"Marked viewport saved: {marked_path}")
    print(f"  Red rect = card bounds in viewport coordinates")
    print(f"  Green rect = viewport bounds")
    print(f"  Card topLeft=({tl_vp.x()},{tl_vp.y()}) bottomRight=({br_vp.x()},{br_vp.y()})")
    print(f"  Viewport: {vp_pm.width()}x{vp_pm.height()}")
    
    # Check if card is fully within viewport (by pixel inspection)
    card_inside = (
        tl_vp.x() >= 0 and tl_vp.y() >= 0 and
        br_vp.x() <= vp_pm.width() and br_vp.y() <= vp_pm.height()
    )
    print(f"\nCard fully inside viewport bounds: {card_inside}")
    
    if not card_inside:
        print(f"  CLIPPING DETECTED: card extends beyond viewport!")
        print(f"  Off by: left={-tl_vp.x() if tl_vp.x() < 0 else 0}, top={-tl_vp.y() if tl_vp.y() < 0 else 0}")
        print(f"  Off by: right={br_vp.x() - vp_pm.width() if br_vp.x() > vp_pm.width() else 0}, bottom={br_vp.y() - vp_pm.height() if br_vp.y() > vp_pm.height() else 0}")
    
    # Now also check with grid marks every 50px
    grid_pm = vp.grab()
    gp = QPainter(grid_pm)
    gp.setPen(QPen(QColor(255, 0, 0, 128), 1))
    # Draw vertical grid lines
    for x in range(0, grid_pm.width(), 50):
        gp.drawLine(x, 0, x, grid_pm.height() - 1)
    # Draw horizontal grid lines
    for y in range(0, grid_pm.height(), 50):
        gp.drawLine(0, y, grid_pm.width() - 1, y)
    gp.end()
    grid_pm.save("debug_grid.png")
    print(f"\nGrid overlay saved: debug_grid.png (50px grid lines)")
    
    # Now test the EXPAND PREVIEW
    print(f"\n{'='*80}")
    print(f"TESTING EXPAND PREVIEW")
    print(f"{'='*80}")
    
    from views.widgets.large_preview_dialog import LargePreviewDialog
    dialog = LargePreviewDialog(gen_view)
    
    pixmap = gen_view._front_preview.current_pixmap()
    if not pixmap.isNull():
        dialog.set_pixmap(pixmap)
    
    # Show but don't exec - we need to capture
    dialog.show()
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()
    
    dlg_vp = dialog._canvas._view.viewport()
    dlg_pm = dlg_vp.grab()
    
    dp = QPainter(dlg_pm)
    dp.setPen(QPen(QColor(255, 0, 0), 2))
    
    dlg_scene_rect = dialog._canvas._view._pixmap_item.boundingRect()
    dlg_tl = dialog._canvas._view.mapFromScene(dlg_scene_rect.topLeft())
    dlg_br = dialog._canvas._view.mapFromScene(dlg_scene_rect.bottomRight())
    dp.drawRect(QRect(dlg_tl, dlg_br))
    
    dp.setPen(QPen(QColor(0, 255, 0), 1))
    dp.drawRect(0, 0, dlg_pm.width() - 1, dlg_pm.height() - 1)
    dp.end()
    
    dlg_pm.save("debug_dialog_marked.png")
    print(f"\nDialog viewport saved: debug_dialog_marked.png")
    print(f"  Card topLeft=({dlg_tl.x()},{dlg_tl.y()}) bottomRight=({dlg_br.x()},{dlg_br.y()})")
    print(f"  Viewport: {dlg_pm.width()}x{dlg_pm.height()}")
    
    dlg_card_inside = (
        dlg_tl.x() >= 0 and dlg_tl.y() >= 0 and
        dlg_br.x() <= dlg_pm.width() and dlg_br.y() <= dlg_pm.height()
    )
    print(f"  Card fully inside viewport: {dlg_card_inside}")
    
    if not dlg_card_inside:
        print(f"  CLIPPING DETECTED in Expand Preview!")
    
    # Now also check the rendered IMAGE for fields outside bounds
    from services.preview import PreviewRenderer
    from controllers.template_controller import TemplateController
    
    tc = TemplateController()
    template = tc.get_template_by_id(4)
    fields = tc.load_all_layout(4)
    renderer = PreviewRenderer(dpi=150)
    
    model = gen_view._binding_manager.model
    field_data = model.all_values
    
    img = renderer.render_front(template, fields, field_data, None, None)
    print(f"\nRendered image size: {img.size}")
    
    # Check if any fields are rendered outside the image bounds
    px_per_mm = 150 / 25.4
    for f in fields:
        if f.page_side != "front" or not f.visible:
            continue
        if f.field_type in ("text",):
            x_px = round(f.x * px_per_mm)
            y_px = round(f.y * px_per_mm)
            w_px = round(f.width * px_per_mm)
            h_px = round(f.height * px_per_mm)
            right_edge = x_px + w_px
            bottom_edge = y_px + h_px
            if right_edge > img.width or bottom_edge > img.height:
                print(f"  FIELD OUTSIDE IMAGE: {f.field_name} at ({x_px},{y_px}) size ({w_px}x{h_px})")
                print(f"    Right edge={right_edge} > img_width={img.width}" if right_edge > img.width else "", end="")
                print(f" Bottom edge={bottom_edge} > img_height={img.height}" if bottom_edge > img.height else "")
    
    app.quit()

QTimer.singleShot(1000, analyze)
sys.exit(app.exec())
