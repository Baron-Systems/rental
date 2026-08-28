"""Settings API: get/update settings + due-types CRUD.

Ported from ``src/app/api/settings/**``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager


# ---------------------------------------------------------------------------
# Settings  (source: GET/PUT /api/settings)
# ---------------------------------------------------------------------------

# All fields that can be read/updated via the settings API.
SETTINGS_FIELDS = [
	"landlord_type",
	"landlord_name",
	"landlord_id",
	"landlord_phone",
	"landlord_address",
	"logo",
	"landlord_representative_name",
	"landlord_representative_id",
	"landlord_representative_title",
	"currency",
	"contract_prefix",
	"contract_counter",
	"due_prefix",
	"due_counter",
	"receipt_prefix",
	"receipt_counter",
	"default_contract_duration",
	"default_payment_frequency",
	"default_payment_method",
	"contract_alert_days",
	"auto_approve_contract",
	"print_header",
	"print_footer",
	"print_logo",
	"show_due_schedule",
	"default_contract_terms",
]

# Legal-sensitive fields that require confirmation when approved contracts exist.
# Source: settings.ts:143-150 (6-field list).
LEGAL_SENSITIVE_FIELDS = [
	"landlord_type",
	"landlord_name",
	"landlord_id",
	"landlord_representative_name",
	"landlord_representative_id",
	"landlord_representative_title",
]

CONFIRMATION_MESSAGE = (
	"سيتم استخدام البيانات الجديدة في العقود الجديدة والتجديدات القادمة فقط، "
	"ولن تتغير بيانات العقود المعتمدة سابقًا. هل تريد المتابعة؟"
)


@frappe.whitelist()
def get_settings() -> dict | None:
	account = _get_account_or_fallback()
	if account is None:
		return None

	settings_name = frappe.db.get_value(
		"Rental Settings", {"rental_account": account}, "name"
	)
	if not settings_name:
		return None

	settings = frappe.db.get_value(
		"Rental Settings",
		settings_name,
		["name", "rental_account"] + SETTINGS_FIELDS + ["currency_locked"],
		as_dict=True,
	)

	if settings:
		locked = _is_currency_locked(account)
		# C13: meta includes hasApprovedContract, hasDue, hasReceipt (legacy route.ts:18-28).
		# hasApprovedContract: active/expired/evicted OR cancelled with lessor_snapshot (settings.ts:170-179).
		settings["meta"] = {
			"locked": locked,
			"hasApprovedContract": _has_approved_contracts(account),
			"hasDue": frappe.db.count("Rental Due", {"rental_account": account, "docstatus": 1}) > 0,
			"hasReceipt": frappe.db.count("Rental Receipt", {"rental_account": account, "docstatus": 1}) > 0,
		}

	return settings


def _get_account_or_fallback() -> str | None:
	"""Return the current user's rental account, or the first active account for System Manager."""
	account = get_current_rental_account()
	if account is not None:
		return account
	# System Manager: fall back to the first active rental account
	accounts = frappe.get_all("Rental Account", filters={"is_active": 1}, fields=["name"], limit=1)
	if not accounts:
		return None
	return accounts[0]["name"]


def _is_currency_locked(account: str) -> bool:
	"""Currency is locked once any approved contract, due, or receipt exists.

	Source: getCurrencyLockStatus (settings.ts:188-205).
	locked = hasApprovedContract || hasDue || hasReceipt.
	"""
	if _has_approved_contracts(account):
		return True

	approved_dues = frappe.db.count("Rental Due", {"rental_account": account, "docstatus": 1})
	if approved_dues > 0:
		return True

	approved_receipts = frappe.db.count("Rental Receipt", {"rental_account": account, "docstatus": 1})
	if approved_receipts > 0:
		return True

	return False


def _has_approved_contracts(account: str) -> bool:
	"""Check if any approved contract exists.

	Source: getApprovedContractCount (settings.ts:170-179).
	Approved = active/expired/evicted OR cancelled with lessor_snapshot.
	"""
	non_cancelled = frappe.db.count(
		"Lease Contract",
		{"rental_account": account, "status": ["in", ["active", "expired", "evicted"]]},
	)
	if non_cancelled > 0:
		return True

	# Cancelled contracts count only if they have a lessor_snapshot
	cancelled_with_snapshot = frappe.db.count(
		"Lease Contract",
		{
			"rental_account": account,
			"status": "cancelled",
			"lessor_snapshot": ["is", "set"],
		},
	)
	return cancelled_with_snapshot > 0


def _normalize_for_comparison(value) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _has_legal_sensitive_changes(settings_doc, kwargs: dict) -> bool:
	"""Check if any legal-sensitive field is being changed.

	Source: hasLegalSensitiveChanges (settings.ts:161-168).
	"""
	for field in LEGAL_SENSITIVE_FIELDS:
		if field in kwargs:
			current_val = _normalize_for_comparison(getattr(settings_doc, field, None))
			new_val = _normalize_for_comparison(kwargs[field])
			if current_val != new_val:
				return True
	return False


def _validate_lessor_data(lessor_type: str, landlord_name: str, landlord_id: str,
						  landlord_representative_name: str = "",
						  landlord_representative_id: str = "",
						  landlord_representative_title: str = "") -> None:
	"""Validate lessor data using the same rules as setupCompleteSchema.

	Source: setupCompleteSchema (validation.ts:387-424).
	"""
	if not landlord_name or not landlord_name.strip():
		frappe.throw(frappe._("اسم المؤجر مطلوب"), frappe.ValidationError)

	if not landlord_id:
		frappe.throw(frappe._("رقم الهوية أو التسجيل غير صالح"), frappe.ValidationError)

	# landlord_id must be 4-20 digits
	import re
	if not re.match(r"^\d{4,20}$", str(landlord_id).strip()):
		frappe.throw(frappe._("رقم الهوية أو التسجيل غير صالح"), frappe.ValidationError)

	if lessor_type == "company":
		if not landlord_representative_name or not landlord_representative_name.strip():
			frappe.throw(frappe._("اسم المفوض مطلوب"), frappe.ValidationError)
		if not landlord_representative_id:
			frappe.throw(frappe._("رقم هوية المفوض مطلوب"), frappe.ValidationError)
		if not re.match(r"^\d{4,20}$", str(landlord_representative_id).strip()):
			frappe.throw(frappe._("رقم هوية المفوض غير صالح"), frappe.ValidationError)
		if not landlord_representative_title or not landlord_representative_title.strip():
			frappe.throw(frappe._("صفة المفوض مطلوبة"), frappe.ValidationError)


@frappe.whitelist()
def update_settings(**kwargs) -> dict:
	"""Update settings.

	Source: PUT /api/settings (route.ts:49-141).
	- Currency lock: cannot change currency once locked.
	- Legal-sensitive fields: require confirmation if approved contracts exist.
	- Validates lessor data when landlord fields are updated.
	"""
	account = _get_account_or_fallback()
	if account is None:
		frappe.throw(
			frappe._("No active Rental Account found. Please complete setup first."),
			frappe.PermissionError,
		)

	settings_name = frappe.db.get_value(
		"Rental Settings", {"rental_account": account}, "name"
	)
	if not settings_name:
		frappe.throw(
			frappe._("Settings not found. Please complete setup first."),
			frappe.ValidationError,
		)

	settings = frappe.get_doc("Rental Settings", settings_name)
	confirmed = bool(int(kwargs.get("confirmed", 0) or 0))

	# Currency lock check
	locked = _is_currency_locked(account)
	current_currency = settings.currency or "ILS"
	new_currency = kwargs.get("currency", current_currency)
	if _normalize_for_comparison(current_currency) != _normalize_for_comparison(new_currency) and locked:
		frappe.throw(
			frappe._("لا يمكن تغيير العملة الأساسية بعد بدء المعاملات المالية."),
			frappe.ValidationError,
		)

	# Legal-sensitive field change confirmation
	has_approved = _has_approved_contracts(account)
	if has_approved and not confirmed:
		legal_changed = _has_legal_sensitive_changes(settings, kwargs)
		if legal_changed:
			return {"needsConfirmation": True, "error": CONFIRMATION_MESSAGE}

	# Validate lessor data if any landlord-related fields are being updated
	has_landlord_update = any(f in kwargs for f in LEGAL_SENSITIVE_FIELDS)
	if has_landlord_update:
		lessor_type = kwargs.get("landlord_type", settings.landlord_type) or "person"
		landlord_name = kwargs.get("landlord_name", settings.landlord_name) or ""
		landlord_id = kwargs.get("landlord_id", settings.landlord_id) or ""
		rep_name = kwargs.get("landlord_representative_name", settings.landlord_representative_name) or ""
		rep_id = kwargs.get("landlord_representative_id", settings.landlord_representative_id) or ""
		rep_title = kwargs.get("landlord_representative_title", settings.landlord_representative_title) or ""
		_validate_lessor_data(lessor_type, landlord_name, landlord_id, rep_name, rep_id, rep_title)

	# Apply all provided fields
	for field in SETTINGS_FIELDS:
		if field in kwargs:
			value = kwargs[field]
			# Convert checkbox values
			if field in ("auto_approve_contract", "print_logo", "show_due_schedule"):
				if isinstance(value, str):
					value = int(value) if value in ("1", "0", "true", "false") else 0
				elif isinstance(value, bool):
					value = int(value)
			# Convert int fields
			elif field in ("contract_counter", "due_counter", "receipt_counter",
						  "default_contract_duration", "contract_alert_days"):
				try:
					value = int(value) if value is not None else 0
				except (ValueError, TypeError):
					value = 0
			setattr(settings, field, value)

	settings.save(ignore_permissions=True)
	return {"status": "success"}


# ---------------------------------------------------------------------------
# Due Types  (source: GET/POST /api/settings/due-types, /api/settings/due-types/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_due_types(include_system=1, include_inactive=0):
	"""List all due types for the current account.

	Source: ``GET /api/settings/due-types?includeSystem=true``.
	Ensures system due types exist before returning the list.
	"""
	from rental.rental.services.due_generation_service import ensure_system_due_types
	ensure_system_due_types()

	account = get_current_rental_account()

	# Build filters — include both account-specific and system (null account) due types
	# System due types have rental_account = NULL, custom types have rental_account = account
	or_filters = {}
	if account:
		or_filters = {
			"rental_account": account,
			"is_system": 1,
		}

	filters = {}
	if not int(include_system):
		filters["is_system"] = 0
	if not int(include_inactive):
		filters["is_active"] = 1

	types = frappe.get_all(
		"Rental Due Type",
		filters=filters if filters else None,
		or_filters=or_filters if or_filters else None,
		fields=[
			"name", "due_type_code", "due_type_name",
			"is_system", "is_active", "rental_account",
		],
		order_by="is_system desc, due_type_name asc",
	)
	return {"dueTypes": types}


@frappe.whitelist()
def create_due_type(due_type_name, due_type_code=None, is_active=1, rental_account=None):
	"""Create a custom due type.

	Source: ``POST /api/settings/due-types`` (due-types/route.ts:34-63).
	- Only requires name (code is optional, auto-generated if not provided).
	- Prevents creating a type with a reserved system name or code.
	"""
	from rental.rental.services.due_generation_service import ensure_system_due_types

	account = rental_account or get_current_rental_account()
	if account is None:
		# System Manager: fall back to the first active rental account
		accounts = frappe.get_all("Rental Account", filters={"is_active": 1}, fields=["name"], limit=1)
		if not accounts:
			frappe.throw(frappe._("No active Rental Account found. Please complete setup first."), frappe.PermissionError)
		account = accounts[0]["name"]

	name = (due_type_name or "").strip()
	if not name:
		frappe.throw(frappe._("اسم نوع الالتزام مطلوب"), frappe.ValidationError)

	# Ensure system due types exist and prevent creating a duplicate/reserved one
	ensure_system_due_types()

	# Check reserved system names
	system_names = {"إيجار", "كهرباء", "مياه"}
	if name in system_names:
		frappe.throw(
			frappe._("لا يمكن إنشاء نوع التزام بنفس اسم أو رمز نوع نظامي محجوز"),
			frappe.ValidationError,
		)

	# Auto-generate code if not provided
	if not due_type_code:
		due_type_code = name.replace(" ", "_").lower()[:50]

	# Check reserved system codes
	system_codes = {"rent", "electricity", "water"}
	if due_type_code in system_codes:
		frappe.throw(
			frappe._("لا يمكن إنشاء نوع التزام بنفس اسم أو رمز نوع نظامي محجوز"),
			frappe.ValidationError,
		)

	# Check unique code per account
	existing = frappe.db.exists(
		"Rental Due Type",
		{"rental_account": account, "due_type_code": due_type_code},
	)
	if existing:
		frappe.throw(
			frappe._("اسم أو رمز نوع الالتزام مستخدم مسبقًا. يرجى إدخال اسم مختلف."),
			frappe.ValidationError,
		)

	# Check unique name per account
	existing_name = frappe.db.exists(
		"Rental Due Type",
		{"rental_account": account, "due_type_name": name},
	)
	if existing_name:
		frappe.throw(
			frappe._("اسم أو رمز نوع الالتزام مستخدم مسبقًا. يرجى إدخال اسم مختلف."),
			frappe.ValidationError,
		)

	doc = frappe.get_doc({
		"doctype": "Rental Due Type",
		"rental_account": account,
		"due_type_code": due_type_code,
		"due_type_name": name,
		"is_system": 0,
		"is_active": is_active,
	})
	doc.insert(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def update_due_type(name, is_active=None):
	"""Update a due type — only the active state can be toggled.

	Source: ``PUT /api/settings/due-types/[id]`` (due-types/[id]/route.ts:29-68).
	- System types cannot be modified.
	- Only is_active can be changed.
	- Cannot disable if used in an alive contract charge.
	"""
	from rental.rental.services.due_generation_service import ensure_system_due_types
	ensure_system_due_types()

	doc = frappe.get_doc("Rental Due Type", name)
	if not is_system_manager():
		doc.check_permission("write")

	if doc.is_system:
		frappe.throw(frappe._("لا يمكن تعديل أنواع النظام الثابتة"), frappe.PermissionError)

	if is_active is None:
		frappe.throw(frappe._("حالة التفعيل مطلوبة"), frappe.ValidationError)

	if not int(is_active):
		# C9: check hasAliveContractCharge before disabling
		# (legacy due-types/[id]/route.ts:48-54)
		today = frappe.utils.today()
		alive_charge = frappe.db.exists(
			"Contract Charge",
			{
				"due_type": name,
				"parenttype": "Lease Contract",
				"docstatus": ["<", 2],
			},
		)
		if alive_charge:
			# Check the parent contract is not historical/closed and end_date >= today
			alive_contracts = frappe.get_all(
				"Lease Contract",
				filters={
					"status": ["in", ["draft", "active"]],
					"end_date": [">=", today],
					"is_historical": 0,
					"closed_by_renewal_at": ["is", "not set"],
				},
				fields=["name"],
			)
			alive_contract_names = [c.name for c in alive_contracts]
			if alive_contract_names:
				charged_alive = frappe.db.exists(
					"Contract Charge",
					{
						"due_type": name,
						"parenttype": "Lease Contract",
						"parent": ["in", alive_contract_names],
					},
				)
				if charged_alive:
					frappe.throw(
						frappe._("لا يمكن تعطيل نوع الالتزام لأنه مستخدم في عقد قائم أو مسودة."),
						frappe.ValidationError,
					)

	doc.is_active = int(is_active)
	doc.save(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def delete_due_type(name):
	"""Delete a custom due type. System types cannot be deleted.

	Source: ``DELETE /api/settings/due-types/[id]`` (due-types/[id]/route.ts:71-101).
	- Cannot delete if used in any due or contract charge.
	"""
	from rental.rental.services.due_generation_service import ensure_system_due_types
	ensure_system_due_types()

	doc = frappe.get_doc("Rental Due Type", name)
	if not is_system_manager():
		doc.check_permission("delete")

	if doc.is_system:
		frappe.throw(frappe._("لا يمكن حذف أنواع النظام الثابتة"), frappe.PermissionError)

	# Check not used in any contract charge or due
	used_in_charges = frappe.db.count("Contract Charge", {"due_type": name})
	used_in_dues = frappe.db.count("Rental Due", {"due_type": name})
	if used_in_charges or used_in_dues:
		frappe.throw(
			frappe._(
				"لا يمكن حذف نوع الالتزام لأنه مستخدم في عقود أو التزامات سابقة. "
				"يمكنك تعطيله إذا لم يعد مستخدمًا في عقد قائم."
			),
			frappe.ValidationError,
		)

	frappe.delete_doc("Rental Due Type", name, ignore_permissions=is_system_manager())
	return {"success": True}
