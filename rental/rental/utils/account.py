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
			frappe._("أنت غير مرتبط بأي حساب إيجار. يرجى الاتصال بمسؤول النظام.")
		)

	if len(accounts) > 1:
		raise frappe.ValidationError(
			frappe._("تم العثور على عدة حسابات إيجار للمستخدم {0}. يرجى الاتصال بمسؤول النظام.").format(
				user
			)
		)

	account = accounts[0]

	if not account.is_active:
		raise frappe.PermissionError(
			frappe._("حساب الإيجار الخاص بك معطل. يرجى الاتصال بمسؤول النظام.")
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
			frappe._("ليس لديك صلاحية الوصول إلى بيانات حساب الإيجار هذا")
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
				frappe._("يجب أن تنتمي جميع المستندات المرجعية إلى نفس حساب الإيجار")
			)
