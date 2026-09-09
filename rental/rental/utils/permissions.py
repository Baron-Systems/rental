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

	if doctype in ("Rental Due Type", "Unit Type", "Unit Attribute"):
		return f"""(`tab{doctype}`.`rental_account` = "{account}" OR `tab{doctype}`.`is_system` = 1 OR `tab{doctype}`.`rental_account` IS NULL)"""

	if doctype == "User Unit Preference":
		return f'`tab{doctype}`.`rental_account` = "{account}" AND `tab{doctype}`.`user` = "{user}"'

	# Rental Account: filter by owner_user (the account itself has no rental_account field)
	if doctype == "Rental Account":
		return f'`tabRental Account`.`owner_user` = "{user}"'

	return f'`tab{doctype}`.`rental_account` = "{account}"'


def has_account_permission(doc, user: str | None = None) -> bool:
	if user is None:
		user = frappe.session.user

	if is_system_manager(user):
		return True

	if not hasattr(doc, "rental_account"):
		# Rental Account: check owner_user matches current user
		if doc.doctype == "Rental Account":
			return doc.owner_user == user
		return True

	# User Unit Preference: must match both rental_account AND user
	if doc.doctype == "User Unit Preference":
		try:
			account = get_current_rental_account()
		except (frappe.PermissionError, frappe.ValidationError):
			return False
		if not account:
			return True
		return doc.rental_account == account and doc.user == user

	if doc.doctype in ("Rental Due Type", "Unit Type", "Unit Attribute"):
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
