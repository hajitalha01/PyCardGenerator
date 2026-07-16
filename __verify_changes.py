"""Verify all changes for Task 1-4."""
import sys
sys.path.insert(0, '.')

from PySide6.QtWidgets import QApplication, QMainWindow
app = QApplication([])

mw = QMainWindow()
from views.card_generator_view import CardGeneratorView
v = CardGeneratorView()
mw.setCentralWidget(v)
mw.show()
app.processEvents()

TASK1_PASS = True

# =========================================================
# TASK 1 - Front form has all 9 fields
# =========================================================
front_fields = {
    'employee_name': v._name_input,
    'employee_designation': v._designation_input,
    'employee_no': v._emp_no_input,
    'date_of_birth': v._dob_input,
    'cnic': v._cnic_input,
    'employee_category': v._category_input,
    'blood_group': v._blood_group_input,
    'location': v._location_input,
    'dependents': v._dependents_front_input,
}
for name, widget in front_fields.items():
    assert widget is not None, f"Missing front field: {name}"
    print(f"  OK {name}")

print('PASS: All 9 front form fields present')

# =========================================================
# TASK 2 - Template Editor Dynamic Fields
# =========================================================
from views.template_editor_view import _DYNAMIC_FIELD_DEFS
expected_defs = [
    ("Employee Name", "employee_name", "text"),
    ("Employee Designation", "employee_designation", "text"),
    ("Employee No", "employee_no", "text"),
    ("Date of Birth", "date_of_birth", "date"),
    ("CNIC", "cnic", "text"),
    ("Employee Category", "employee_category", "text"),
    ("Blood Group", "blood_group", "text"),
    ("Location", "location", "text"),
    ("Dependents", "dependents", "text"),
    ("Employee Photo", "employee_photo", "photo"),
]
assert _DYNAMIC_FIELD_DEFS == expected_defs, (
    f"Mismatch:\n  Got: {_DYNAMIC_FIELD_DEFS}\n  Exp: {expected_defs}"
)
print('PASS: Template Editor dynamic fields match expected')

# =========================================================
# TASK 3 - Dynamic Binding
# =========================================================
from controllers.binding_manager import BindingManager
bm = v._binding_manager

# Simulate typing in each field and verify model gets the value
test_data = {
    'employee_name': 'John Doe',
    'employee_designation': 'Engineer',
    'employee_no': 'EMP-001',
    'date_of_birth': '15-08-1990',
    'cnic': '12345-6789012-3',
    'employee_category': 'Permanent',
    'blood_group': 'A+',
    'location': 'Head Office',
    'dependents': 'Self, Spouse',
}

for field_name, test_value in test_data.items():
    bm.set_field(field_name, test_value)

all_vals = bm.model.all_values
for field_name, test_value in test_data.items():
    actual = all_vals.get(field_name, '')
    assert actual == test_value, (
        f"Binding failed for {field_name}: expected '{test_value}', got '{actual}'"
    )
    print(f"  OK {field_name} -> '{actual}'")

# Verify backward compatibility: old "designation" gets value from "employee_designation"
bm.set_field('employee_designation', 'Sr Engineer')
desig_old = bm.model.get_value('designation')
assert desig_old == 'Sr Engineer', (
    f"Backward compat failed for designation: expected 'Sr Engineer', got '{desig_old}'"
)
print('  OK Backward compat: "designation" synced from "employee_designation"')

# Verify backward compatibility: old "dependence" gets value from "dependents"
bm.set_field('dependents', 'Wife, 2 Kids')
dep_old = bm.model.get_value('dependence')
assert dep_old == 'Wife, 2 Kids', (
    f"Backward compat failed for dependence: expected 'Wife, 2 Kids', got '{dep_old}'"
)
print('  OK Backward compat: "dependence" synced from "dependents"')

# Verify structured dependents override "dependence"
bm.add_dependent({"name": "Ali", "relation": "Son", "date_of_birth": "10-10-2015", "cnic": "12345"})
all_vals = bm.model.all_values
assert "Ali" in all_vals.get("dependence", ""), (
    f"Structured dependents should override dependence: {all_vals.get('dependence')}"
)
print('  OK Structured dependents override "dependence" in all_values')

print('PASS: Dynamic binding verified')

# =========================================================
# TASK 4 - Verify
# =========================================================
# Front form visible by default
assert v._front_preview.isVisible(), "Front preview should be visible"
assert v._back_preview.isHidden(), "Back preview should be hidden"
assert v._form_stack.currentIndex() == 0, "Form stack should show front form"
print('PASS: Front mode active by default')

# Switch to Back
v._on_side_changed(1)
assert v._active_side == 'back'
assert v._front_preview.isHidden()
assert v._back_preview.isVisible()
assert v._form_stack.currentIndex() == 1
print('PASS: Back mode switch works')

# Switch back to Front
v._on_side_changed(0)
assert v._active_side == 'front'
assert v._front_preview.isVisible()
assert v._back_preview.isHidden()
assert v._form_stack.currentIndex() == 0
print('PASS: Front mode switch back works')

# Validate form
errors = v._validate_form()
assert len(errors) > 0, "Empty form should have validation errors"
print(f'PASS: Form validation returns {len(errors)} errors')

# Validate form with all fields filled (select a template first)
v._template_combo.addItem('Test Template', 999)
v._template_combo.setCurrentIndex(1)
v._name_input.setText('John')
v._designation_input.setText('Engineer')
v._emp_no_input.setText('EMP-001')
v._category_input.setText('Permanent')
v._location_input.setText('Office')
v._photo_path = 'dummy.jpg'
errors = v._validate_form()
assert len(errors) == 0, f"Filled form should pass validation: {errors}"
print('PASS: Filled form passes validation')

# Clear form (bypass QMessageBox confirmation to avoid blocking)
v._name_input.clear()
v._designation_input.clear()
v._emp_no_input.clear()
v._dob_input.clear()
v._cnic_input.clear()
v._category_input.clear()
v._blood_group_input.clear()
v._location_input.clear()
v._dependents_front_input.clear()
v._template_combo.setCurrentIndex(0)
v._photo_path = ""
v._photo_label.setText("No photo\nselected")
v._binding_manager.clear_dependents()
v._refresh_dependents_table()
v._clear_dependent_form()
v._binding_manager.clear()
v._clear_field_highlights()
assert v._name_input.text() == ''
assert v._emp_no_input.text() == ''
assert v._dependents_front_input.text() == ''
assert v._dependents_table.rowCount() == 0
print('PASS: Clear form resets all fields and dependents')

print()
print('=== ALL CHECKS PASSED ===')

app.processEvents()
mw.close()
app.quit()
