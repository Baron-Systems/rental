import frappe


def is_system_manager(user: str | None = None) -> bool:
	if user is None:
		user = frappe.session.user
	return "System Manager" in frappe.get_roles(user)


def get_current_rental_account() -> str | None:
	if is_system_manager():
		return None

	user = frappe.session.user

	accounts = frappe.get_all(
		"Rental Account",
		filters={"owner_user": user},
		fields=["name", "is_active"],
	)

	if not accounts:
		raise frappe.PermissionError(
			frappe._("You are not linked to any Rental Account. Please contact the system administrator.")
		)

	if len(accounts) > 1:
		raise frappe.ValidationError(
			frappe._("Multiple Rental Accounts found for user {0}. Please contact the system administrator.").format(
				user
			)
		)

	account = accounts[0]

	if not account.is_active:
		raise frappe.PermissionError(
			frappe._("Your Rental Account is disabled. Please contact the system administrator.")
		)

	return account.name


def get_current_account_info() -> dict | None:
	account_name = get_current_rental_account()
	if account_name is None:
		return None

	account = frappe.db.get_value(
		"Rental Account",
		account_name,
		["name", "account_name", "is_active", "setup_completed"],
		as_dict=True,
	)

	return {
		"name": account.name,
		"account_name": account.account_name,
		"is_active": account.is_active,
		"setup_completed": account.setup_completed,
	}


def assert_account_access(doc) -> None:
	account = get_current_rental_account()
	if account is None:
		return
	if not hasattr(doc, "rental_account"):
		return
	if doc.rental_account != account:
		raise frappe.PermissionError(
			frappe._("You do not have access to this Rental Account's data")
		)


def assert_same_account(*docs) -> None:
	account = get_current_rental_account()
	if account is None:
		return

	for doc in docs:
		if doc is None:
			continue
		if not hasattr(doc, "rental_account"):
			continue
		if doc.rental_account != account:
			raise frappe.PermissionError(
				frappe._("All referenced documents must belong to the same Rental Account")
			)
