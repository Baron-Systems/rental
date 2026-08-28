import frappe


def before_install():
	_create_rental_property_owner_role()


def after_install():
	_create_system_due_types()


def _create_rental_property_owner_role():
	if frappe.db.exists("Role", "Rental Property Owner"):
		return

	role = frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": "Rental Property Owner",
			"desk_access": 0,
			"disabled": 0,
		}
	)
	role.insert(ignore_permissions=True)


def _create_system_due_types():
	from rental.rental.services.due_generation_service import ensure_system_due_types
	ensure_system_due_types()
