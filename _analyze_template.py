"""Analyze template 'M Fccl' — dump all fields and properties."""
from database.db_manager import DatabaseManager

db = DatabaseManager()
db.connect()

tpl = db.fetch_one('SELECT * FROM templates WHERE template_name = ?', ('M Fccl',))
if not tpl:
    print("Template 'M Fccl' not found")
    exit(1)

print('=== TEMPLATE ===')
for k, v in dict(tpl).items():
    print(f'  {k}: {v}')

fields = db.fetch_all(
    'SELECT * FROM template_fields WHERE template_id = ? ORDER BY page_side, z_order',
    (tpl['id'],)
)
print(f'\n=== FIELDS ({len(fields)}) ===')
for f in fields:
    d = dict(f)
    print(f'  [id={d["id"]}] side={d["page_side"]} z={d["z_order"]} type={d["field_type"]} '
          f'static={d["is_static"]} name="{d["field_name"]}" '
          f'mapped="{d["mapped_field"]}" '
          f'x={d["x"]:.2f} y={d["y"]:.2f} w={d["width"]:.2f} h={d["height"]:.2f} '
          f'font={d["font_family"]} size={d["font_size"]} bold={d["bold"]} '
          f'color={d["font_color"]} align={d["alignment"]} '
          f'visible={d["visible"]} static_text="{d["static_text"]}"')
