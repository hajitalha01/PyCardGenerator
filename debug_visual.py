"""Visual debug: capture screenshot and verify card visibility."""
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "windows"

os.chdir(os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QImage
from views.card_generator_view import CardGeneratorView
from views.main_window import MainWindow

app = QApplication(sys.argv)
app.setStyle("Fusion")

# Inline stylesheet (same as main.py)
stylesheet = """
QMainWindow, QWidget { background-color: #f8f9fa; font-family: "Segoe UI", "Arial", sans-serif; font-size: 13px; color: #333333; }
#viewTitle { font-size: 26px; font-weight: 700; color: #1a1a2e; }
#viewContent { background-color: #ffffff; border: 1px solid #e9ecef; border-radius: 10px; }
#previewPanel { background-color: #ffffff; }
#previewCardTitle { font-size: 12px; font-weight: 600; color: #666666; padding: 0px; }
#infoBar { background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 8px 12px; }
#infoLabel { font-size: 12px; color: #888888; }
"""
app.setStyleSheet(stylesheet)

window = MainWindow()
window._navigate_to(1)
window.resize(1400, 900)
window.show()
app.processEvents()

gen_view = window._card_generator_view

# Select template and fill fields
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

def capture_debug():
    front_preview = gen_view._front_preview
    back_preview = gen_view._back_preview
    
    # Grab the MainWindow contents
    window_pixmap = window.grab()
    window_pixmap.save("debug_window.png")
    print(f"Window screenshot saved: debug_window.png ({window_pixmap.width()}x{window_pixmap.height()})")
    
    # Grab the CardGeneratorView
    gen_view_pixmap = gen_view.grab()
    gen_view_pixmap.save("debug_generator.png")
    print(f"Generator screenshot saved: debug_generator.png ({gen_view_pixmap.width()}x{gen_view_pixmap.height()})")
    
    # Grab the PreviewCanvas
    front_pixmap = front_preview.grab()
    front_pixmap.save("debug_preview.png")
    print(f"Front preview screenshot saved: debug_preview.png ({front_pixmap.width()}x{front_pixmap.height()})")
    
    # Grab the _CardGraphicsView directly
    view_pixmap = front_preview._view.grab()
    view_pixmap.save("debug_view.png")
    print(f"View screenshot saved: debug_view.png ({view_pixmap.width()}x{view_pixmap.height()})")
    
    # Grab the viewport
    vp = front_preview._view.viewport()
    vp_pixmap = vp.grab()
    vp_pixmap.save("debug_viewport.png")
    print(f"Viewport screenshot saved: debug_viewport.png ({vp_pixmap.width()}x{vp_pixmap.height()})")
    
    # Print final state
    view = front_preview._view
    pm = view._pixmap_item.pixmap()
    t = view.transform()
    vp_w = view.viewport().width()
    vp_h = view.viewport().height()
    
    # Calculate where the card is in viewport coordinates
    scene_br = view._pixmap_item.boundingRect()
    # Top-left in viewport coordinates
    tl = view.mapFromScene(scene_br.topLeft())
    br = view.mapFromScene(scene_br.bottomRight())
    
    print(f"\n=== FINAL STATE ===")
    print(f"Pixmap: {pm.width()}x{pm.height()}")
    print(f"Viewport: {vp_w}x{vp_h}")
    print(f"View: {view.width()}x{view.height()}")
    print(f"Transform: m11={t.m11():.4f} m22={t.m22():.4f} dx={t.m31():.1f} dy={t.m32():.1f}")
    print(f"Scene BR: {scene_br}")
    print(f"Card in viewport coords: topLeft=({tl.x()},{tl.y()}) bottomRight=({br.x()},{br.y()})")
    print(f"Expected card pixels: w={pm.width()*t.m11():.1f} h={pm.height()*t.m22():.1f}")
    
    # Is the card fully visible?
    card_w_in_vp = pm.width() * t.m11()
    card_h_in_vp = pm.height() * t.m22()
    print(f"\nCard display: {card_w_in_vp:.1f}x{card_h_in_vp:.1f} in viewport {vp_w}x{vp_h}")
    print(f"Card fully visible? w={card_w_in_vp <= vp_w} h={card_h_in_vp <= vp_h}")
    print(f"Card start x={tl.x():.1f} end x={br.x():.1f} (viewport 0-{vp_w})")
    print(f"Card start y={tl.y():.1f} end y={br.y():.1f} (viewport 0-{vp_h})")
    
    # Check if the QGraphicsPixmapItem is in the scene
    print(f"\nScene items: {len(view._scene.items())}")
    print(f"Pixmap item pos: ({view._pixmap_item.pos().x()}, {view._pixmap_item.pos().y()})")
    print(f"Pixmap item zValue: {view._pixmap_item.zValue()}")
    
    # Check the VIEW for any offset
    print(f"\nView frameGeometry: {view.frameGeometry()}")
    print(f"View geometry: {view.geometry()}")
    print(f"View contentsRect: {view.contentsRect()}")
    print(f"View viewport geometry: {view.viewport().geometry()}")
    print(f"View viewport pos: {view.viewport().pos()}")
    
    # Check the scene's items for anything else
    print(f"\nAll scene items:")
    for item in view._scene.items():
        print(f"  {type(item).__name__}: {item.boundingRect()}")
    
    # Now test the Template Editor for comparison
    print(f"\n{'='*80}")
    print(f"COMPARISON WITH TEMPLATE EDITOR")
    print(f"{'='*80}")
    
    editor = window._template_editor_view
    window._navigate_to(3)
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()
    
    # Load the tatheer template
    try:
        editor.load_template(4)
        app.processEvents()
    except Exception as e:
        print(f"Cannot load template in editor: {e}")
    
    if hasattr(editor, '_canvas'):
        ec = editor._canvas
        edit_pm = ec.grab()
        edit_pm.save("debug_editor.png")
        print(f"Editor screenshot saved: debug_editor.png ({edit_pm.width()}x{edit_pm.height()})")
        
        ec_vp = ec.viewport()
        print(f"Editor viewport: {ec_vp.width()}x{ec_vp.height()}")
        print(f"Editor view: {ec.width()}x{ec.height()}")
        
        et = ec.transform()
        print(f"Editor transform: m11={et.m11():.4f} m22={et.m22():.4f}")
        
        # Show scene info
        print(f"Editor scene rect: {ec._scene.sceneRect()}")
        print(f"Editor card item: {ec._card_item.rect()}")
        print(f"Editor card item pos: ({ec._card_item.pos().x()}, {ec._card_item.pos().y()})")
        
        # Scrollbar policies
        print(f"Editor hScrollBar: {ec.horizontalScrollBarPolicy()}")
        print(f"Editor vScrollBar: {ec.verticalScrollBarPolicy()}")
        print(f"Preview hScrollBar: {view.horizontalScrollBarPolicy()}")
        print(f"Preview vScrollBar: {view.verticalScrollBarPolicy()}")
    
    print(f"\nDone. Check the PNG files.")
    app.quit()

QTimer.singleShot(1000, capture_debug)
sys.exit(app.exec())
