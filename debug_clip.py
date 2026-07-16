"""Runtime debug: trace the complete Card Generator preview pipeline.

Run:  python debug_clip.py
"""

import sys
import os
import time
from pathlib import Path

# --- Patch preview_canvas BEFORE any imports ---
import views.widgets.preview_canvas as pvc_mod

_orig_set_pixmap = pvc_mod._CardGraphicsView.set_pixmap
_orig_fit_in_view = pvc_mod._CardGraphicsView.fit_in_view
_orig_resize_event = pvc_mod._CardGraphicsView.resizeEvent if hasattr(pvc_mod._CardGraphicsView, 'resizeEvent') else None

def _traced_set_pixmap(self, pixmap):
    print(f"\n=== set_pixmap ===")
    print(f"  time={time.perf_counter():.3f}")
    if pixmap is not None and not pixmap.isNull():
        print(f"  pixmap size: {pixmap.width()} x {pixmap.height()}")
    print(f"  viewport (before): {self.viewport().width()} x {self.viewport().height()}")
    print(f"  view size (before): {self.width()} x {self.height()}")
    result = _orig_set_pixmap(self, pixmap)
    if pixmap is not None and not pixmap.isNull():
        t = self.transform()
        print(f"  transform (after fitInView): m11={t.m11():.4f} m12={t.m12():.4f} m21={t.m21():.4f} m22={t.m22():.4f} dx={t.m31():.1f} dy={t.m32():.1f}")
        print(f"  viewport (after): {self.viewport().width()} x {self.viewport().height()}")
        print(f"  scene rect: {self._scene.sceneRect().x():.1f}, {self._scene.sceneRect().y():.1f}, {self._scene.sceneRect().width():.1f}, {self._scene.sceneRect().height():.1f}")
        print(f"  pixmap_item pos: ({self._pixmap_item.pos().x()}, {self._pixmap_item.pos().y()})")
        print(f"  pixmap_item boundingRect: ({self._pixmap_item.boundingRect().x()}, {self._pixmap_item.boundingRect().y()}, {self._pixmap_item.boundingRect().width()}, {self._pixmap_item.boundingRect().height()})")
        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        pm_w = self._pixmap_item.pixmap().width()
        pm_h = self._pixmap_item.pixmap().height()
        scale = min(vp_w / pm_w, vp_h / pm_h) if pm_w > 0 and pm_h > 0 else 1
        print(f"  expected scale: {scale:.4f}")
        print(f"  expected rendered size: {pm_w * scale:.1f} x {pm_h * scale:.1f}")
    return result

def _traced_fit_in_view(self):
    print(f"\n=== fit_in_view ===")
    print(f"  time={time.perf_counter():.3f}")
    if not self._pixmap_item.pixmap().isNull():
        pm_w = self._pixmap_item.pixmap().width()
        pm_h = self._pixmap_item.pixmap().height()
        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        print(f"  pixmap: {pm_w} x {pm_h}")
        print(f"  viewport: {vp_w} x {vp_h}")
        print(f"  view: {self.width()} x {self.height()}")
        scale_before = min(vp_w / pm_w, vp_h / pm_h) if pm_w > 0 and pm_h > 0 else 1
        print(f"  expected scale: {scale_before:.4f}")
    result = _orig_fit_in_view(self)
    if not self._pixmap_item.pixmap().isNull():
        t = self.transform()
        print(f"  transform AFTER: m11={t.m11():.4f} m22={t.m22():.4f} dx={t.m31():.1f} dy={t.m32():.1f}")
    return result

def _traced_resize_event(self, event):
    print(f"\n=== resizeEvent ===")
    print(f"  time={time.perf_counter():.3f}")
    print(f"  old size: {event.oldSize().width()} x {event.oldSize().height()}")
    print(f"  new size: {event.size().width()} x {event.size().height()}")
    return _orig_resize_event(self, event)

pvc_mod._CardGraphicsView.set_pixmap = _traced_set_pixmap
pvc_mod._CardGraphicsView.fit_in_view = _traced_fit_in_view

# Patch resizeEvent if it exists
if hasattr(pvc_mod._CardGraphicsView, 'resizeEvent'):
    pvc_mod._CardGraphicsView.resizeEvent = _traced_resize_event

# --- Patch PreviewRenderer ---
import services.preview.preview_renderer as pr_mod

_orig_render_side = pr_mod.PreviewRenderer._render_side

def _traced_render_side(self, template, fields, field_data, photo_path, side, cache):
    canvas_size = self._canvas_size(template)
    print(f"\n=== render_side: {side} ===")
    print(f"  canvas_size: {canvas_size}")
    print(f"  template.canvas_width={template.canvas_width} canvas_height={template.canvas_height}")
    print(f"  px_per_mm={self.px_per_mm:.4f}")
    result = _orig_render_side(self, template, fields, field_data, photo_path, side, cache)
    print(f"  result image: {result.size}")
    return result

pr_mod.PreviewRenderer._render_side = _traced_render_side

# --- Patch LargePreviewDialog ---
import views.widgets.large_preview_dialog as lpd_mod

_orig_set_pixmap_dialog = lpd_mod.LargePreviewDialog.set_pixmap

def _traced_set_pixmap_dialog(self, pixmap):
    print(f"\n=== LargePreviewDialog.set_pixmap ===")
    if pixmap is not None and not pixmap.isNull():
        print(f"  pixmap: {pixmap.width()} x {pixmap.height()}")
    print(f"  dialog size: {self.width()} x {self.height()}")
    print(f"  canvas size: {self._canvas.width()} x {self._canvas.height()}")
    return _orig_set_pixmap_dialog(self, pixmap)

lpd_mod.LargePreviewDialog.set_pixmap = _traced_set_pixmap_dialog

# --- Now run the app ---
os.environ["QT_QPA_PLATFORM"] = "windows"

os.chdir(Path(__file__).parent)

from PySide6.QtWidgets import QApplication
from views.card_generator_view import CardGeneratorView
from views.main_window import MainWindow

app = QApplication(sys.argv)
app.setStyle("Fusion")

# Import stylesheets
# Apply stylesheet (copy from main.py)
stylesheet: str = """
/* ---- Root ---- */
QMainWindow, QWidget {
    background-color: #f8f9fa;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
    color: #333333;
}
/* ---- Header ---- */
#header {
    background-color: #ffffff;
    border-bottom: 1px solid #dee2e6;
}
#headerTitle {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a2e;
}
#headerVersion {
    font-size: 11px;
    color: #888888;
    margin-left: 6px;
}
#headerDate {
    font-size: 12px;
    color: #666666;
}
/* ---- Sidebar ---- */
#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #dee2e6;
}
#sidebarTitle {
    font-size: 16px;
    font-weight: 700;
    color: #1a1a2e;
    padding: 0px 16px;
}
#sidebarVersion {
    font-size: 11px;
    color: #aaaaaa;
    padding: 8px 0px;
}
#navButton {
    background-color: transparent;
    color: #555555;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    text-align: left;
}
#navButton:hover {
    background-color: #e8f0fe;
    color: #1a73e8;
}
#navButton:checked {
    background-color: #e8f0fe;
    color: #1a73e8;
    font-weight: 600;
}
/* ---- Content pages ---- */
#viewTitle {
    font-size: 26px;
    font-weight: 700;
    color: #1a1a2e;
}
#viewDescription {
    font-size: 14px;
    color: #888888;
}
#viewContent {
    background-color: #ffffff;
    border: 1px solid #e9ecef;
    border-radius: 10px;
}
/* ---- Form controls ---- */
#formScroll {
    background-color: transparent;
}
#formContainer {
    background-color: transparent;
}
#formSectionTitle {
    font-size: 13px;
    font-weight: 600;
    color: #333333;
}
#photoPlaceholder {
    background-color: #f8f9fa;
    border: 2px dashed #cccccc;
    border-radius: 8px;
    color: #aaaaaa;
    font-size: 12px;
}
#photoButton {
    background-color: #f0f0f0;
    color: #333333;
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
}
#photoButton:hover {
    background-color: #e4e4e4;
    border-color: #aaaaaa;
}
#fieldInput {
    background-color: #ffffff;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    color: #333333;
}
#fieldInput:focus {
    border-color: #1a73e8;
}
#fieldInput[invalid="true"] {
    border: 1px solid #dc3545;
    background-color: #fff5f5;
}
#actionButton {
    background-color: #f0f0f0;
    color: #333333;
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
}
#actionButton:hover {
    background-color: #e4e4e4;
    border-color: #aaaaaa;
}
#actionButton:disabled {
    background-color: #f8f8f8;
    color: #bbbbbb;
    border-color: #e0e0e0;
}
#sideTabBtn {
    background-color: #f0f0f0;
    color: #666666;
    border: 1px solid #cccccc;
    border-radius: 6px;
    padding: 6px 18px;
    font-size: 12px;
    font-weight: 500;
}
#sideTabBtn:hover {
    background-color: #e4e4e4;
    border-color: #aaaaaa;
}
#sideTabBtn:checked {
    background-color: #1a73e8;
    color: #ffffff;
    border-color: #1a73e8;
    font-weight: 600;
}
/* ---- Preview controls ---- */
#previewTitle {
    font-size: 13px;
    font-weight: 600;
    color: #555555;
}
#previewPanel {
    background-color: #ffffff;
}
#previewCardTitle {
    font-size: 12px;
    font-weight: 600;
    color: #666666;
    padding: 0px;
}
#cardFrame {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
}
/* ---- Info bar ---- */
#infoBar {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 6px;
    padding: 8px 12px;
}
#infoLabel {
    font-size: 12px;
    color: #888888;
}
/* ---- Divider ---- */
#divider {
    background-color: #e0e0e0;
}
/* ---- Status bar ---- */
#statusBar {
    background-color: #ffffff;
    border-top: 1px solid #dee2e6;
    font-size: 12px;
    color: #888888;
    padding: 2px 12px;
}
#statusBar QLabel {
    padding: 0px 12px;
}
QToolTip {
    background-color: #333333;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
"""
app.setStyleSheet(stylesheet)

window = MainWindow()

# Navigate to Card Generator (index 1)
window._navigate_to(1)

# Force layout + show
window.resize(1400, 900)
window.show()
app.processEvents()

# CardGeneratorView is stored on MainWindow
gen_view = window._card_generator_view

print("\n" + "=" * 80)
print("WINDOW SHOWN - LAYOUT COMPLETE")
print("=" * 80)

# Print preview panel sizes
preview_panel = gen_view.findChild(type(gen_view), "previewPanel") if False else None
# Just use the child widget directly
print(f"\nGenerator view size: {gen_view.width()} x {gen_view.height()}")

# Find preview canvases
front_preview = gen_view._front_preview
back_preview = gen_view._back_preview

print(f"front_preview size: {front_preview.width()} x {front_preview.height()}")
print(f"  title_label height: {front_preview._title_label.height()}")
print(f"  view size: {front_preview._view.width()} x {front_preview._view.height()}")
print(f"  view viewport size: {front_preview._view.viewport().width()} x {front_preview._view.viewport().height()}")
print(f"  isVisible: {front_preview.isVisible()}")
print(f"back_preview size: {back_preview.width()} x {back_preview.height()}")
print(f"  isVisible: {back_preview.isVisible()}")

# Select the template
print("\n" + "=" * 80)
print("SELECTING TEMPLATE...")
print("=" * 80)

gen_view._template_combo.setCurrentIndex(1)  # tatheer
gen_view._template_combo.currentIndexChanged.emit(1)
app.processEvents()
time.sleep(0.2)
app.processEvents()

print(f"\nAfter template select:")
print(f"front_preview size: {front_preview.width()} x {front_preview.height()}")
print(f"  view viewport: {front_preview._view.viewport().width()} x {front_preview._view.viewport().height()}")

# Set field values
print("\n" + "=" * 80)
print("SETTING FIELD VALUES...")
print("=" * 80)

field_values = [
    ("employee_name", "John Doe"),
    ("employee_designation", "Engineer"),
    ("employee_no", "EMP-001"),
    ("date_of_birth", "15-08-1990"),
    ("cnic", "12345-6789012-3"),
    ("employee_category", "Permanent"),
    ("blood_group", "A+"),
    ("location", "Head Office"),
    ("dependents", "Self, Spouse"),
]

from PySide6.QtCore import QTimer
for field_name, value in field_values:
    gen_view._binding_manager.set_field(field_name, value)

app.processEvents()
time.sleep(0.3)
app.processEvents()

print(f"\nAfter setting fields:")
print(f"front_preview size: {front_preview.width()} x {front_preview.height()}")
print(f"  view viewport: {front_preview._view.viewport().width()} x {front_preview._view.viewport().height()}")

if not front_preview._view._pixmap_item.pixmap().isNull():
    pm = front_preview._view._pixmap_item.pixmap()
    print(f"  pixmap: {pm.width()} x {pm.height()}")
    t = front_preview._view.transform()
    print(f"  transform: m11={t.m11():.4f} m22={t.m22():.4f} dx={t.m31():.1f} dy={t.m32():.1f}")

# Now test Expand Preview
print("\n" + "=" * 80)
print("OPENING EXPAND PREVIEW DIALOG...")
print("=" * 80)

def open_and_check():
    """Open the Expand Preview dialog and check sizes."""
    # Manually create the dialog
    from views.widgets.large_preview_dialog import LargePreviewDialog
    
    dialog = LargePreviewDialog(gen_view)
    
    pixmap = gen_view._front_preview.current_pixmap()
    if not pixmap.isNull():
        dialog.set_pixmap(pixmap)
    
    print(f"\nBefore show:")
    print(f"  dialog size: {dialog.width()} x {dialog.height()}")
    print(f"  canvas size: {dialog._canvas.width()} x {dialog._canvas.height()}")
    print(f"  view size: {dialog._canvas._view.width()} x {dialog._canvas._view.height()}")
    print(f"  view viewport: {dialog._canvas._view.viewport().width()} x {dialog._canvas._view.viewport().height()}")
    
    if not dialog._canvas._view._pixmap_item.pixmap().isNull():
        pm = dialog._canvas._view._pixmap_item.pixmap()
        t = dialog._canvas._view.transform()
        print(f"  pixmap: {pm.width()} x {pm.height()}")
        print(f"  transform: m11={t.m11():.4f} m22={t.m22():.4f} dx={t.m31():.1f} dy={t.m32():.1f}")
    
    # Show the dialog
    dialog.show()
    app.processEvents()
    
    print(f"\nAfter show:")
    print(f"  dialog size: {dialog.width()} x {dialog.height()}")
    print(f"  canvas size: {dialog._canvas.width()} x {dialog._canvas.height()}")
    print(f"  view size: {dialog._canvas._view.width()} x {dialog._canvas._view.height()}")
    print(f"  view viewport: {dialog._canvas._view.viewport().width()} x {dialog._canvas._view.viewport().height()}")
    
    if not dialog._canvas._view._pixmap_item.pixmap().isNull():
        pm = dialog._canvas._view._pixmap_item.pixmap()
        t = dialog._canvas._view.transform()
        print(f"  pixmap: {pm.width()} x {pm.height()}")
        print(f"  transform: m11={t.m11():.4f} m22={t.m22():.4f} dx={t.m31():.1f} dy={t.m32():.1f}")
        print(f"  isVisible: {dialog._canvas._view.isVisible()}")
        print(f"  scene rect: {dialog._canvas._view._scene.sceneRect().x():.1f}, {dialog._canvas._view._scene.sceneRect().y():.1f}, {dialog._canvas._view._scene.sceneRect().width():.1f}, {dialog._canvas._view._scene.sceneRect().height():.1f}")
    
    # Check the back canvas too
    print(f"\nBack canvas state in dialog:")
    print(f"  visible: {back_preview.isVisible()}")
    print(f"  size: {back_preview.width()} x {back_preview.height()}")
    if not back_preview._view._pixmap_item.pixmap().isNull():
        pm_b = back_preview._view._pixmap_item.pixmap()
        print(f"  pixmap: {pm_b.width()} x {pm_b.height()}")
        t_b = back_preview._view.transform()
        print(f"  transform: m11={t_b.m11():.4f} m22={t_b.m22():.4f}")
    
    # Check layout dump
    print(f"\nParent chain for front view:")
    p = front_preview._view
    while p:
        print(f"  {p.__class__.__name__}: size={p.width()}x{p.height()} visible={p.isVisible()}")
        p = p.parentWidget()
    
    dialog.close()

QTimer.singleShot(500, open_and_check)

sys.exit(app.exec())
