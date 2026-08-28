import frappe

from rental.rental.utils.account import is_system_manager, get_current_rental_account


def get_permission_query_conditions(user: str | None = None, doctype: str | None = None):
	if user is None:
		user = frappe.session.user

	if is_system_manager(user):
		return None

	if doctype is None:
		doctype = frappe.form_dict.get("doctype")

	if not doctype:
		return None

	try:
		account = get_current_rental_account()
	except frappe.PermissionError:
		return " 1=0 "
	except frappe.ValidationError:
		return " 1=0 "

	if not account:
		return None

	if doctype == "Rental Due Type":
		return f"""(`tab{doctype}`.`rental_account` = "{account}" OR `tab{doctype}`.`is_system` = 1 OR `tab{doctype}`.`rental_account` IS NULL)"""

	return f'`tab{doctype}`.`rental_account` = "{account}"'


def has_account_permission(doc, user: str | None = None) -> bool:
	if user is None:
		user = frappe.session.user

	if is_system_manager(user):
		return True

	if not hasattr(doc, "rental_account"):
		return True

	if doc.doctype == "Rental Due Type":
		if doc.get("is_system"):
			return True
		if not doc.get("rental_account"):
			return True

	try:
		account = get_current_rental_account()
	except (frappe.PermissionError, frappe.ValidationError):
		return False

	if not account:
		return True

	return doc.rental_account == account
