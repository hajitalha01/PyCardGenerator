"""Quick verification that the coordinate normalization fix works."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ['QT_QPA_PLATFORM'] = 'windows'

from services.preview import PreviewRenderer
from controllers.template_controller import TemplateController

tc = TemplateController()
template = tc.get_template_by_id(4)
fields = tc.load_all_layout(4)

renderer = PreviewRenderer(dpi=150)

model = type('obj', (object,), {'all_values': {
    'employee_name': 'John Doe',
    'employee_designation': 'Engineer',
    'employee_no': 'EMP-001',
    'date_of_birth': '15-08-1990',
    'cnic': '12345-6789012-3',
    'employee_category': 'Permanent',
    'blood_group': 'A+',
    'location': 'Head Office',
    'dependents': 'Self, Spouse',
}})()

img = renderer.render_front(template, fields, model.all_values, None, None)

px_per_mm = 150 / 25.4
margin_mm_x = 60 * 85.6 / 600
margin_mm_y = 60 * 54.0 / 379

img_w, img_h = img.size
print(f"Canvas: {img_w} x {img_h}")
print(f"margin_mm_x={margin_mm_x:.4f} margin_mm_y={margin_mm_y:.4f}")
print()

clipped = []
safe = []
for f in fields:
    if f.page_side != 'front' or not f.visible:
        continue
    norm_x = max(0.0, f.x - margin_mm_x)
    norm_y = max(0.0, f.y - margin_mm_y)
    x_px = round(norm_x * px_per_mm)
    y_px = round(norm_y * px_per_mm)
    w_px = round(f.width * px_per_mm)
    h_px = round(f.height * px_per_mm)
    right = x_px + w_px
    bottom = y_px + h_px
    if right > img_w or bottom > img_h:
        clipped.append((f.field_name, x_px, y_px, w_px, h_px, right, bottom))
    else:
        safe.append(f.field_name)

print(f"Fields within canvas: {len(safe)}")
if clipped:
    print(f"Fields CLIPPED: {len(clipped)} (canvas {img_w}x{img_h})")
    for name, x, y, w, h, r, b in clipped:
        print(f"  {name}: pos=({x},{y}) size=({w}x{h}) right={r} bot={b}")
else:
    print(f"All {len(fields)} front fields fit within canvas - NO CLIPPING")

w, h = img.size
samples = {
    'top-left': (0, 0),
    'top-right': (w-1, 0),
    'bottom-left': (0, h-1),
    'bottom-right': (w-1, h-1),
    'center': (w//2, h//2),
}

white_pixels = []
for name, (x, y) in samples.items():
    px = img.getpixel((x, y))
    is_white = px == (255, 255, 255, 255)
    status = "WHITE" if is_white else "OK"
    print(f"  {name}: {px} {status}")
    if is_white:
        white_pixels.append(name)

if white_pixels:
    print(f"WARNING: Background gaps at: {white_pixels}")
else:
    print(f"Background fills entire canvas - NO GAPS")
