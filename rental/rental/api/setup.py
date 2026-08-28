"""Setup API: get setup status, complete setup wizard.

Ported from ``src/app/api/setup/route.ts``.
Source of truth: ``Rental_Management_olde/src/app/api/setup/route.ts`` +
``Rental_Management_olde/src/lib/validation.ts`` (setupCompleteSchema).
"""

from __future__ import annotations

import re

import frappe

from rental.rental.utils.account import get_current_rental_account


# ---------------------------------------------------------------------------
# Validation  (source: src/lib/validation.ts — setupCompleteSchema)
# ---------------------------------------------------------------------------

# نص رقمي غير فارغ، 4–20 خانة، يحفظ الأصفار البادئة
_LANDLORD_ID_RE = re.compile(r"^\d{4,20}$")


def _validate_setup_payload(data: dict) -> list[str]:
	"""Return a list of Arabic error messages (empty = valid).

	Mirrors ``setupCompleteSchema.superRefine`` from validation.ts:387-424.
	"""
	errors: list[str] = []

	lessor_type = (data.get("lessor_type") or data.get("landlord_type") or "").strip()
	landlord_name = (data.get("landlord_name") or "").strip()
	landlord_id = (data.get("landlord_id") or "").strip()
	currency = (data.get("currency") or "").strip()

	if not landlord_name:
		errors.append("اسم المؤجر مطلوب")

	if not landlord_id or not _LANDLORD_ID_RE.match(landlord_id):
		errors.append("رقم الهوية أو التسجيل غير صالح")

	if currency not in ("ILS", "JOD", "USD"):
		errors.append("العملة مطلوبة")

	if lessor_type == "company":
		rep_name = (data.get("landlord_representative_name") or "").strip()
		rep_id = (data.get("landlord_representative_id") or "").strip()
		rep_title = (data.get("landlord_representative_title") or "").strip()

		if not rep_name:
			errors.append("اسم المفوض مطلوب")
		# Source: validation.ts:353-356 (optionalRepresentativeIdSchema) +
		# validation.ts:409-414 (superRefine). Empty → "مطلوب",
		# non-empty invalid → "غير صالح".
		if not rep_id:
			errors.append("رقم هوية المفوض مطلوب")
		elif not _LANDLORD_ID_RE.match(rep_id):
			errors.append("رقم هوية المفوض غير صالح")
		if not rep_title:
			errors.append("صفة المفوض مطلوبة")

	return errors


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_setup():
	"""Get setup status for the current account.

	Source: ``GET /api/setup`` (route.ts:9-42).
	Returns ``{ setup, lessor }`` so the frontend can pre-fill the wizard form
	and render ContractDocument / PrintHeader / LessorClause.
	"""
	account = get_current_rental_account()
	if account is None:
		# System admin - always "complete"
		return {
			"setup_completed": True,
			"is_system_admin": True,
			"setup": None,
			"lessor": None,
		}

	account_doc = frappe.db.get_value(
		"Rental Account", account,
		["name", "account_name", "is_active", "setup_completed", "owner_user"],
		as_dict=True,
	)

	settings_name = frappe.db.get_value(
		"Rental Settings", {"rental_account": account}, "name"
	)

	# ``setup`` mirrors the original key/value map (route.ts:14-34).
	setup = {
		"setup_completed": bool(account_doc.setup_completed),
		"lessor_type": "person",
		"landlord_name": "",
		"landlord_id": "",
		"landlord_phone": "",
		"landlord_address": "",
		"company_logo": "",
		"currency": "ILS",
		"landlord_representative_name": "",
		"landlord_representative_id": "",
		"landlord_representative_title": "",
	}

	lessor = None
	if settings_name:
		settings = frappe.db.get_value(
			"Rental Settings", settings_name,
			["landlord_type", "landlord_name", "landlord_id", "landlord_phone",
			 "landlord_address", "logo",
			 "landlord_representative_name", "landlord_representative_id",
			 "landlord_representative_title", "currency"],
			as_dict=True,
		)
		if settings:
			setup["lessor_type"] = (
				"company" if settings.landlord_type == "company" else "person"
			)
			setup["landlord_name"] = settings.landlord_name or ""
			setup["landlord_id"] = settings.landlord_id or ""
			setup["landlord_phone"] = settings.landlord_phone or ""
			setup["landlord_address"] = settings.landlord_address or ""
			setup["company_logo"] = settings.logo or ""
			setup["currency"] = settings.currency or "ILS"
			setup["landlord_representative_name"] = (
				settings.landlord_representative_name or ""
			)
			setup["landlord_representative_id"] = (
				settings.landlord_representative_id or ""
			)
			setup["landlord_representative_title"] = (
				settings.landlord_representative_title or ""
			)

			# Build lessor object (mirrors getLessorData shape from settings.ts)
			lessor = {
				"type": setup["lessor_type"],
				"name": setup["landlord_name"],
				"identityOrRegistrationNumber": setup["landlord_id"],
				"phone": setup["landlord_phone"],
				"address": setup["landlord_address"],
				"representativeName": setup["landlord_representative_name"],
				"representativeId": setup["landlord_representative_id"],
				"representativeTitle": setup["landlord_representative_title"],
				"currency": setup["currency"],
				"logo": setup["company_logo"],
			}

	# Source: route.ts:36 — returns exactly { setup, lessor }
	return {
		"setup": setup,
		"lessor": lessor,
	}


@frappe.whitelist()
def complete_setup(
	lessor_type: str | None = None,
	landlord_name: str | None = None,
	landlord_id: str | None = None,
	landlord_phone: str | None = None,
	landlord_address: str | None = None,
	company_logo: str | None = None,
	currency: str | None = None,
	landlord_representative_name: str | None = None,
	landlord_representative_id: str | None = None,
	landlord_representative_title: str | None = None,
) -> dict:
	"""Complete the setup wizard.

	Source: ``PUT /api/setup`` (route.ts:44-86).
	Validates with the equivalent of ``setupCompleteSchema`` and upserts
	the Rental Settings doc, then marks the account as setup_completed.
	"""
	account = get_current_rental_account()
	if account is None:
		frappe.throw(
			frappe._("System Manager cannot complete setup wizard"),
			frappe.PermissionError,
		)

	# Normalize lessor_type: accept "person" | "company"
	if lessor_type not in ("person", "company"):
		lessor_type = "person"

	data = {
		"lessor_type": lessor_type,
		"landlord_name": landlord_name or "",
		"landlord_id": landlord_id or "",
		"landlord_phone": landlord_phone or "",
		"landlord_address": landlord_address or "",
		"company_logo": company_logo or "",
		"currency": currency or "",
		"landlord_representative_name": landlord_representative_name or "",
		"landlord_representative_id": landlord_representative_id or "",
		"landlord_representative_title": landlord_representative_title or "",
	}

	# Validate (source: setupCompleteSchema — validation.ts:387-424)
	errors = _validate_setup_payload(data)
	if errors:
		frappe.throw(
			frappe._("، ".join(errors)),
			frappe.ValidationError,
		)

	existing_settings = frappe.db.get_value(
		"Rental Settings", {"rental_account": account}, "name"
	)

	if existing_settings:
		settings = frappe.get_doc("Rental Settings", existing_settings)
	else:
		settings = frappe.get_doc({"doctype": "Rental Settings"})
		settings.rental_account = account

	# Map wizard fields → Rental Settings fields
	# (source: route.ts:56-68 upsert keys)
	settings.landlord_type = lessor_type
	settings.landlord_name = data["landlord_name"]
	settings.landlord_id = data["landlord_id"]
	settings.landlord_phone = data["landlord_phone"]
	settings.landlord_address = data["landlord_address"]
	settings.landlord_representative_name = data["landlord_representative_name"]
	settings.landlord_representative_id = data["landlord_representative_id"]
	settings.landlord_representative_title = data["landlord_representative_title"]
	# company_logo from the wizard maps to the ``logo`` Attach Image field.
	# The original stores base64 data URL; Frappe stores a file URL when
	# uploaded via /api/method/upload_file. Both are accepted here.
	if data["company_logo"]:
		settings.logo = data["company_logo"]
	settings.currency = data["currency"]

	settings.save(ignore_permissions=True)

	frappe.db.set_value("Rental Account", account, "setup_completed", 1)
	frappe.db.commit()

	return {"success": True}
