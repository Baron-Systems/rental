"""Auth API: login, logout, me.

Ported from ``src/app/api/auth/**``.
Note: change-email and change-password are NOT exposed — user management is handled
by Frappe's admin in this multi-user system.
"""

from __future__ import annotations

import frappe
from frappe.utils.password import check_password


@frappe.whitelist(allow_guest=True)
def login(email, password):
	"""Authenticate user and create session.

	Source: ``POST /api/auth/login``.
	"""
	try:
		check_password(email, password)
	except frappe.exceptions.AuthenticationError:
		frappe.throw(frappe._("Invalid email or password"), frappe.AuthenticationError)

	frappe.local.login_manager.login(email)

	user = frappe.get_doc("User", email)
	return {
		"user": {
			"name": user.name,
			"email": user.email,
			"first_name": user.first_name,
			"last_name": user.last_name,
			"full_name": user.full_name,
			"user_image": user.user_image,
		},
		"sessionId": frappe.session.sid,
	}


@frappe.whitelist()
def logout():
	"""Destroy current session.

	Source: ``POST /api/auth/logout``.
	"""
	frappe.local.login_manager.logout()
	return {"success": True}


@frappe.whitelist(allow_guest=True)
def me():
	"""Return current session user info.

	Source: ``GET /api/auth/me``.
	"""
	if frappe.session.user == "Guest":
		return {"user": None}

	user = frappe.get_doc("User", frappe.session.user)
	roles = frappe.get_roles(user.name)

	is_system_admin = "System Manager" in roles
	is_owner = "Rental Property Owner" in roles

	# Determine account
	account_name = None
	if is_owner:
		account_name = frappe.db.get_value("Rental Account", {"owner_user": user.name}, "name")

	return {
		"user": {
			"name": user.name,
			"email": user.email,
			"first_name": user.first_name,
			"last_name": user.last_name,
			"full_name": user.full_name,
			"user_image": user.user_image,
		},
		"roles": list(roles),
		"isSystemAdmin": is_system_admin,
		"isOwner": is_owner,
		"rentalAccount": account_name,
	}
