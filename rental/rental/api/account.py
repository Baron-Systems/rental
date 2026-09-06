import frappe

from rental.rental.utils.account import is_system_manager, get_current_rental_account, get_current_account_info


@frappe.whitelist()
def has_app_permission(user: str | None = None) -> bool:
	if user is None:
		user = frappe.session.user

	if is_system_manager(user):
		return True

	if "Rental Property Owner" not in frappe.get_roles(user):
		return False

	accounts = frappe.get_all(
		"Rental Account",
		filters={"owner_user": user, "is_active": 1},
		fields=["name"],
		limit=1,
	)

	return len(accounts) > 0


@frappe.whitelist()
def get_current_account() -> dict | None:
	from rental.rental.utils.account import is_system_manager

	if is_system_manager():
		return {
			"name": None,
			"account_name": None,
			"is_active": True,
			"setup_completed": True,
			"is_system_admin": True,
		}

	# Rental Property Owner without an account linked yet
	user = frappe.session.user
	accounts = frappe.get_all(
		"Rental Account",
		filters={"owner_user": user},
		fields=["name", "account_name", "is_active", "setup_completed"],
		limit=1,
	)
	if not accounts:
		# No account linked — return a marker so the frontend can handle it
		return {
			"name": None,
			"account_name": None,
			"is_active": False,
			"setup_completed": False,
			"is_system_admin": False,
			"needs_account": True,
		}

	info = accounts[0]
	if not info.is_active:
		return {
			"name": None,
			"account_name": info.account_name,
			"is_active": False,
			"setup_completed": False,
			"is_system_admin": False,
			"account_disabled": True,
		}

	settings = _get_safe_settings(info["name"])
	info["settings"] = settings
	info["is_system_admin"] = False
	return info


@frappe.whitelist()
def list_rental_accounts() -> dict:
	"""Return all active Rental Accounts with their currency.

	Used by the dashboard account selector (System Manager only).
	"""
	from rental.rental.utils.account import is_system_manager

	if not is_system_manager():
		# Regular users have exactly one account — return it for convenience.
		own = get_current_rental_account()
		if not own:
			return {"accounts": []}
		cur = frappe.db.get_value(
			"Rental Settings", {"rental_account": own}, "currency"
		) or "ILS"
		name_val = frappe.db.get_value("Rental Account", own, "account_name") or own
		return {"accounts": [{"name": own, "account_name": name_val, "currency": cur}]}

	rows = frappe.get_all(
		"Rental Account",
		filters={"is_active": 1},
		fields=["name", "account_name"],
		order_by="account_name asc",
	)
	accounts = []
	for r in rows:
		cur = frappe.db.get_value(
			"Rental Settings", {"rental_account": r.name}, "currency"
		) or "ILS"
		accounts.append({
			"name": r.name,
			"account_name": r.account_name or r.name,
			"currency": cur,
		})
	return {"accounts": accounts}


def _get_safe_settings(account_name: str) -> dict | None:
	"""Return lessor data in the LessorData shape expected by the frontend.

	Source: old program ``getLessorData()`` (settings.ts:34-48) — returns
	``{ type, name, identityOrRegistrationNumber, phone, address,
	representativeName, representativeId, representativeTitle, currency, logo }``.
	The frontend's ``ContractDocument.vue`` uses this object as ``lessorData``
	via ``session.state.account.settings``.
	"""
	settings_name = frappe.db.get_value(
		"Rental Settings", {"rental_account": account_name}, "name"
	)
	if not settings_name:
		return None

	s = frappe.db.get_value(
		"Rental Settings",
		settings_name,
		["landlord_type", "landlord_name", "landlord_id", "landlord_phone",
		 "landlord_address", "logo", "currency", "currency_locked",
		 "landlord_representative_name", "landlord_representative_id",
		 "landlord_representative_title"],
		as_dict=True,
	)
	if not s:
		return None

	return {
		"type": "company" if s.landlord_type == "company" else "person",
		"name": s.landlord_name or "",
		"identityOrRegistrationNumber": str(s.landlord_id or ""),
		"phone": s.landlord_phone or "",
		"address": s.landlord_address or "",
		"representativeName": s.landlord_representative_name or "",
		"representativeId": str(s.landlord_representative_id or ""),
		"representativeTitle": s.landlord_representative_title or "",
		"currency": s.currency or "ILS",
		"logo": s.logo or "",
		"currency_locked": s.currency_locked,
	}
