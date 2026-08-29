import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account
from rental.rental.utils.date_utils import generate_number


class RentalSettings(Document):
	def validate(self):
		self._validate_account_access()
		self._validate_currency_lock()

	def _validate_account_access(self):
		account = get_current_rental_account()
		if account is None:
			return
		if self.rental_account != account:
			frappe.throw(
				frappe._("يمكنك الوصول فقط إلى إعدادات حسابك"),
				frappe.PermissionError,
			)

	def _validate_currency_lock(self):
		if self.currency_locked:
			original_currency = frappe.db.get_value(
				"Rental Settings", self.name, "currency"
			)
			if original_currency and self.currency != original_currency:
				frappe.throw(
					frappe._("العملة مقفولة ولا يمكن تغييرها"),
					frappe.ValidationError,
				)


# ---------------------------------------------------------------------------
# Settings helpers  (source: src/lib/settings.ts)
# ---------------------------------------------------------------------------


def get_settings_doc(account: str | None = None) -> Document | None:
	"""Return the ``Rental Settings`` doc for *account* (or current account)."""
	if account is None:
		account = get_current_rental_account()
		if account is None:
			return None
	name = frappe.db.get_value("Rental Settings", {"rental_account": account}, "name")
	if not name:
		return None
	return frappe.get_doc("Rental Settings", name)


def get_setting_value(account: str, field: str):
	"""Read a single setting field for *account*."""
	return frappe.db.get_value("Rental Settings", {"rental_account": account}, field)


def get_currency_lock_status(account: str | None = None) -> dict:
	"""Return ``{locked: bool}`` — locked when any approved contract/due/receipt exists.

	Source: ``getCurrencyLockStatus``.
	"""
	if account is None:
		account = get_current_rental_account()
		if account is None:
			return {"locked": False}

	locked = (
		frappe.db.exists("Lease Contract", {"rental_account": account, "status": ["!=", "draft"]})
		or frappe.db.exists("Rental Due", {"rental_account": account, "docstatus": 1})
		or frappe.db.exists("Rental Receipt", {"rental_account": account, "docstatus": 1})
	)
	return {"locked": bool(locked)}


# Legal-sensitive fields that require confirmation when approved contracts exist
LEGAL_SENSITIVE_FIELDS = {
	"landlord_name", "landlord_id", "landlord_phone", "landlord_address",
	"landlord_type", "logo", "landlord_signature", "landlord_stamp",
	"landlord_representative_name", "landlord_representative_id",
	"landlord_representative_title", "landlord_representative_phone",
}


def is_legal_sensitive_field(field: str) -> bool:
	return field in LEGAL_SENSITIVE_FIELDS


def get_lessor_data(account: str | None = None) -> dict:
	"""Return the lessor data dict for snapshot building.

	Source: ``getLessorData``.
	"""
	settings = get_settings_doc(account)
	if not settings:
		return {}
	return {
		"landlord_type": settings.landlord_type,
		"landlord_name": settings.landlord_name,
		"landlord_id": settings.landlord_id,
		"landlord_phone": settings.landlord_phone,
		"landlord_address": settings.landlord_address,
		"logo": settings.logo,
		"landlord_signature": settings.landlord_signature,
		"landlord_stamp": settings.landlord_stamp,
		"landlord_representative_name": settings.landlord_representative_name,
		"landlord_representative_id": settings.landlord_representative_id,
		"landlord_representative_title": settings.landlord_representative_title,
		"landlord_representative_phone": settings.landlord_representative_phone,
		"currency": settings.currency,
	}


def validate_lessor_data_for_contract(account: str | None = None) -> None:
	"""Validate that lessor data is complete enough for contract approval.

	Source: ``validateLessorDataForContract`` + ``setupCompleteSchema``.
	Required fields: landlord_name, landlord_id (4-20 digits), currency.
	For company lessor_type: representative_name, representative_id, representative_title.
	"""
	import re
	settings = get_settings_doc(account)
	if not settings:
		frappe.throw(frappe._("الإعدادات غير موجودة. يرجى إكمال الإعداد أولاً"))

	errors = []

	landlord_name = (settings.landlord_name or "").strip()
	if not landlord_name:
		errors.append(
			frappe._("اسم الشركة مطلوب") if settings.landlord_type == "company"
			else frappe._("اسم المؤجر مطلوب")
		)

	landlord_id = (str(settings.landlord_id or "")).strip()
	if not re.match(r"^\d{4,20}$", landlord_id):
		errors.append(frappe._("رقم الهوية أو التسجيل غير صالح"))

	if not settings.currency:
		errors.append(frappe._("العملة مطلوبة"))

	# Company-only required fields
	if settings.landlord_type == "company":
		if not (settings.landlord_representative_name or "").strip():
			errors.append(frappe._("اسم المفوض مطلوب"))
		if not (str(settings.landlord_representative_id or "")).strip():
			errors.append(frappe._("رقم هوية المفوض غير صالح"))
		if not (settings.landlord_representative_title or "").strip():
			errors.append(frappe._("صفة المفوض مطلوبة"))

	if errors:
		frappe.throw("، ".join(str(e) for e in errors))


def get_contract_lessor_data(contract_name: str) -> dict:
	"""Return lessor data for a specific contract.

	Source: ``getContractLessorData`` (settings.ts:86-97).
	Falls back to current settings if no snapshot stored.
	"""
	contract = frappe.db.get_value(
		"Lease Contract", contract_name,
		["lessor_snapshot", "rental_account"],
		as_dict=True,
	)
	if not contract:
		return {}

	if contract.lessor_snapshot:
		return parse_lessor_snapshot(contract.lessor_snapshot)

	return get_lessor_data(contract.rental_account)


def get_currency_label(currency: str) -> str:
	"""Return the Arabic label for a currency code.

	Source: ``getCurrencyLabel`` (settings.ts:125-132).
	"""
	labels = {"ILS": "شيكل", "JOD": "دينار أردني", "USD": "دولار"}
	return labels.get(currency, currency or "")


def get_currency_symbol(currency: str) -> str:
	"""Return the symbol for a currency code.

	Source: ``getCurrencySymbol`` (settings.ts:134-141).
	"""
	symbols = {"ILS": "₪", "JOD": "JD", "USD": "$"}
	return symbols.get(currency, "")


def has_legal_sensitive_changes(old_doc, new_doc) -> bool:
	"""Check if any legal-sensitive field changed between old and new settings.

	Source: ``hasLegalSensitiveChanges`` (settings.ts:161-168).
	"""
	for field in LEGAL_SENSITIVE_FIELDS:
		old_val = getattr(old_doc, field, None) if old_doc else None
		new_val = getattr(new_doc, field, None) if new_doc else None
		if old_val != new_val:
			return True
	return False


def get_approved_contract_count(account: str | None = None) -> int:
	"""Count approved contracts for an account.

	Source: ``getApprovedContractCount`` (settings.ts:170-179).
	"""
	if account is None:
		account = get_current_rental_account()
		if account is None:
			return 0
	return frappe.db.count("Lease Contract", {"rental_account": account, "status": ["!=", "draft"]})


def build_lessor_snapshot(account: str | None = None) -> str:
	"""Freeze lessor data as JSON string at contract approval time.

	Source: ``buildLessorSnapshot``.
	"""
	import json
	return json.dumps(get_lessor_data(account), ensure_ascii=False)


def parse_lessor_snapshot(snapshot_json: str | None) -> dict:
	"""Parse a stored lessor snapshot.

	Source: ``parseLessorSnapshot``.
	"""
	if not snapshot_json:
		return {}
	try:
		import json
		return json.loads(snapshot_json)
	except (ValueError, TypeError):
		return {}


# ---------------------------------------------------------------------------
# Number generation helpers  (source: generateNumber + counter settings)
# ---------------------------------------------------------------------------


def generate_contract_number(account: str) -> str:
	"""Generate the next contract number (without incrementing the counter).

	Source: old program uses a single global ``contract_counter`` Setting
	(not per-account), so contract numbers are globally unique.

	The counter is incremented separately via ``increment_contract_counter``
	after the contract is successfully inserted, matching the old program's
	transactional behaviour (counter + create in one transaction).
	"""
	settings = get_settings_doc(account)
	if not settings:
		frappe.throw(frappe._("الإعدادات غير موجودة. يرجى إكمال الإعداد أولاً"))

	prefix = settings.contract_prefix or "CNT"

	# Source: old program — contract_counter is a single global counter.
	# In the new multi-tenant schema, each Rental Settings row has its own
	# contract_counter, but contract_number is globally unique. To match the
	# old behaviour, use the maximum counter across all accounts + 1.
	max_counter = frappe.db.sql(
		"SELECT MAX(contract_counter) FROM `tabRental Settings`", as_dict=False
	)[0][0] or 0
	number = generate_number(prefix, max_counter)

	# Safety: ensure the generated number does not collide with an existing one
	if frappe.db.exists("Lease Contract", {"contract_number": number}):
		# Fall back to max existing contract_number suffix + 1
		existing = frappe.db.sql(
			"""
			SELECT contract_number FROM `tabLease Contract`
			WHERE contract_number LIKE %s
			ORDER BY contract_number DESC
			""",
			(prefix + "-%"),
			as_dict=True,
		)
		max_suffix = 0
		for row in existing:
			parts = (row.contract_number or "").split("-")
			if len(parts) == 2:
				try:
					suffix = int(parts[1])
					if suffix > max_suffix:
						max_suffix = suffix
				except ValueError:
					pass
		number = generate_number(prefix, max_suffix)

	return number


def increment_contract_counter(account: str) -> None:
	"""Increment the contract counter after a contract is successfully created.

	Source: old program increments ``contract_counter`` inside the same
	transaction as ``leaseContract.create``. Here we call this after
	``contract.insert()`` succeeds.
	"""
	settings = get_settings_doc(account)
	if not settings:
		return

	# Keep all accounts in sync: set to max across all accounts + 1
	max_counter = frappe.db.sql(
		"SELECT MAX(contract_counter) FROM `tabRental Settings`", as_dict=False
	)[0][0] or 0
	settings.contract_counter = max_counter + 1
	settings.db_update()


def generate_due_number(account: str) -> str:
	"""Generate the next due number and increment the counter."""
	settings = get_settings_doc(account)
	if not settings:
		frappe.throw(frappe._("الإعدادات غير موجودة."))

	prefix = settings.due_prefix or "DUE"
	counter = settings.due_counter or 0
	# Source: contract-charge.service.ts:547 — no dash separator for due numbers
	number = generate_number(prefix, counter, separator="")

	settings.due_counter = counter + 1
	settings.db_update()
	return number


def generate_receipt_number(account: str) -> str:
	"""Generate the next receipt number and increment the counter.

	Source: ``generateReceiptNumber`` (receipts/[id]/approve/route.ts:7-39).
	Uses a retry loop (up to 100 attempts) to ensure uniqueness.
	"""
	settings = get_settings_doc(account)
	if not settings:
		frappe.throw(frappe._("الإعدادات غير موجودة."))

	prefix = settings.receipt_prefix or "REC"
	counter = settings.receipt_counter or 0

	# B6: retry loop for uniqueness (legacy lines 14-26).
	for _attempt in range(100):
		# Source: receipts/[id]/approve/route.ts:15 — no dash separator for receipt numbers
		number = generate_number(prefix, counter, separator="")
		if not frappe.db.exists("Rental Receipt", {"receipt_number": number}):
			break
		counter += 1
	else:
		frappe.throw(frappe._("تعذر توليد رقم سند قبض فريد. يرجى المحاولة مرة أخرى."))

	settings.receipt_counter = counter + 1
	settings.db_update()
	return number
