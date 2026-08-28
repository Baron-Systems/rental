"""Contract validation, overlap detection, unit status engine, and expiration.

Ported from ``src/services/contract-validation.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import (
	to_calendar_day,
	get_contract_period_status,
)


# ---------------------------------------------------------------------------
# Contract date validation  (source: validateContractDates)
# ---------------------------------------------------------------------------


def validate_contract_dates(start_date, end_date) -> str | None:
	"""Return Arabic error string if start >= end, otherwise None.

	Source: ``validateContractDates`` (contract-validation.ts:65-73).
	"""
	if to_calendar_day(start_date) >= to_calendar_day(end_date):
		return "تاريخ النهاية يجب أن يكون بعد تاريخ البداية"
	return None


# ---------------------------------------------------------------------------
# Rent amount validation  (source: validateRentAmount)
# ---------------------------------------------------------------------------


def validate_rent_amount(amount) -> str | None:
	"""Return Arabic error string if amount is NaN or <= 0, otherwise None.

	Source: ``validateRentAmount`` (contract-validation.ts:93-98).
	"""
	try:
		val = float(amount)
	except (TypeError, ValueError):
		val = float("nan")
	if val != val or val <= 0:  # NaN check (val != val is True for NaN)
		return "قيمة الإيجار يجب أن تكون أكبر من صفر"
	return None


# ---------------------------------------------------------------------------
# Basic data validation  (source: validateContractBasicData)
# ---------------------------------------------------------------------------


def validate_contract_basic_data(contract_doc) -> None:
	"""Validate dates, rent > 0, and that tenant/building/unit exist.

	Also enforces account isolation: all referenced documents must belong
	to the same ``rental_account`` as the contract (source: §4 Account Isolation).
	"""
	# 1. Dates (source: contract-validation.ts:129-138)
	start_date = to_calendar_day(contract_doc.start_date)
	end_date = to_calendar_day(contract_doc.end_date)
	dates_error = validate_contract_dates(start_date, end_date)
	if dates_error:
		frappe.throw(frappe._(dates_error))

	# 2. Rent amount (source: contract-validation.ts:140-144)
	rent_error = validate_rent_amount(contract_doc.rent_amount)
	if rent_error:
		frappe.throw(frappe._(rent_error))

	# 3. Existence checks (source: contract-validation.ts:146-154)
	account = contract_doc.rental_account

	if not frappe.db.exists("Rental Tenant", contract_doc.tenant):
		frappe.throw(frappe._("المستأجر غير موجود"))
	if account:
		tenant_account = frappe.db.get_value("Rental Tenant", contract_doc.tenant, "rental_account")
		if tenant_account and tenant_account != account:
			frappe.throw(frappe._("المستأجر لا ينتمي إلى هذا الحساب"))

	if not frappe.db.exists("Rental Building", contract_doc.building):
		frappe.throw(frappe._("العقار غير موجود"))
	if account:
		building_account = frappe.db.get_value("Rental Building", contract_doc.building, "rental_account")
		if building_account and building_account != account:
			frappe.throw(frappe._("العقار لا ينتمي إلى هذا الحساب"))

	if not frappe.db.exists("Rental Unit", contract_doc.unit):
		frappe.throw(frappe._("الوحدة غير موجودة"))
	if account:
		unit_account = frappe.db.get_value("Rental Unit", contract_doc.unit, "rental_account")
		if unit_account and unit_account != account:
			frappe.throw(frappe._("الوحدة لا تنتمي إلى هذا الحساب"))


# ---------------------------------------------------------------------------
# Draft unit validation  (source: validateContractDraftUnit)
# ---------------------------------------------------------------------------


def validate_contract_draft_unit(contract_doc) -> None:
	"""Validate that the unit is active, building is active, and unit is not unavailable.

	Source: ``validateContractDraftUnit`` (contract-validation.ts:159-192).
	Order of checks (must match original):
	  1. Unit exists → 'الوحدة غير موجودة'
	  2. Unit is active → 'الوحدة معطلة ولا يمكن اختيارها'
	  3. Building is active (or missing) → 'العقار معطل ولا يمكن اختيار وحدته'
	  4. Unit status != unavailable → 'الوحدة غير متاحة ولا يمكن اختيارها'
	  5. Unit belongs to specified building → 'الوحدة لا تنتمي إلى العقار المحدد'
	  6. Unit belongs to specified floor → 'الوحدة لا تنتمي إلى الطابق المحدد'
	"""
	unit = frappe.db.get_value(
		"Rental Unit", contract_doc.unit,
		["is_active", "status", "building", "floor", "rental_account"],
		as_dict=True,
	)
	if not unit:
		frappe.throw(frappe._("الوحدة غير موجودة"))

	if not unit.is_active:
		frappe.throw(frappe._("الوحدة معطلة ولا يمكن اختيارها"))

	# Building active check — in the original, a missing building also produces
	# the "معطل" message (unit.building?.isActive is undefined → falsy).
	# Source: contract-validation.ts:174-176
	building = None
	if unit.building:
		building = frappe.db.get_value(
			"Rental Building", unit.building,
			["is_active", "rental_account"],
			as_dict=True,
		)
	if not building or not building.is_active:
		frappe.throw(frappe._("العقار معطل ولا يمكن اختيار وحدته"))

	if unit.status == "unavailable":
		frappe.throw(frappe._("الوحدة غير متاحة ولا يمكن اختيارها"))

	# Unit must belong to the same building
	# Source: contract-validation.ts:180-182
	if contract_doc.building and unit.building != contract_doc.building:
		frappe.throw(frappe._("الوحدة لا تنتمي إلى العقار المحدد"))

	# Floor check: if floor is specified on the contract, the unit's floor
	# must match. Source: contract-validation.ts:183-189
	if hasattr(contract_doc, "floor"):
		unit_floor = unit.get("floor") or ""
		requested_floor = contract_doc.floor or ""
		if unit_floor != requested_floor:
			frappe.throw(frappe._("الوحدة لا تنتمي إلى الطابق المحدد"))


# ---------------------------------------------------------------------------
# Contract date validation for approval  (source: validateContractDateForApproval)
# ---------------------------------------------------------------------------


def validate_contract_date_for_approval(contract_doc) -> None:
	"""Contract date must not be in the future when approving."""
	if contract_doc.contract_date:
		contract_date = to_calendar_day(contract_doc.contract_date)
		today = to_calendar_day(frappe.utils.today())
		if contract_date > today:
			frappe.throw(frappe._("لا يمكن اعتماد عقد بتاريخ عقد مستقبلي"))


# ---------------------------------------------------------------------------
# Full approval validation  (source: validateContractForApproval)
# ---------------------------------------------------------------------------


def validate_contract_for_approval(contract_doc) -> None:
	"""Full pre-approval validation including renewals, overlaps, occupancy.

	Source: ``validateContractForApproval`` (contract-validation.ts:194-324).
	Order of checks (must match original):
	  1. Basic data validation (dates, rent, tenant/building/unit existence)
	  2. Re-fetch unit + building; check exists and active (approval-specific messages)
	  3. Renewal validation (if renewed_from_contract)
	  4. Operational occupancy checks (expired, cancelled)
	  5. Temporal overlap check
	"""
	# 1. Basic data validation (always re-validate from current data)
	validate_contract_basic_data(contract_doc)

	today = to_calendar_day(frappe.utils.today())

	# 2. Re-fetch unit with building and check active status (approval-specific)
	# Source: contract-validation.ts:211-219
	unit = frappe.db.get_value(
		"Rental Unit", contract_doc.unit,
		["name", "is_active", "building", "status"],
		as_dict=True,
	)
	if not unit:
		frappe.throw(frappe._("الوحدة غير موجودة"))

	building = None
	if unit.building:
		building = frappe.db.get_value(
			"Rental Building", unit.building,
			["name", "is_active"],
			as_dict=True,
		)
	if not building:
		frappe.throw(frappe._("العقار غير موجود"))
	if not unit.is_active:
		frappe.throw(frappe._("الوحدة معطلة ولا يمكن اعتماد عقود جديدة فيها"))
	if not building.is_active:
		frappe.throw(frappe._("العقار معطل ولا يمكن اعتماد عقود جديدة فيه"))

	# 3. Renewal validation
	# Source: contract-validation.ts:222-278
	previous = None
	if contract_doc.renewed_from_contract:
		from rental.rental.services.renewal_service import (
			get_renewal_first_due_date,
			get_started_renewal,
		)

		# Account isolation: previous contract must belong to same account
		prev_account = frappe.db.get_value("Lease Contract", contract_doc.renewed_from_contract, "rental_account")
		if prev_account and prev_account != contract_doc.rental_account:
			frappe.throw(frappe._("العقد السابق لا ينتمي إلى هذا الحساب"))

		# Previous must exist and be eligible for renewal
		previous = frappe.db.get_value(
			"Lease Contract", contract_doc.renewed_from_contract,
			["name", "status", "is_historical", "is_archived", "start_date", "end_date"],
			as_dict=True,
		)
		if not previous:
			frappe.throw(frappe._("العقد السابق غير موجود"))

		# Attach renewals for in-memory checks (source: contract-validation.ts:224-227)
		previous["renewals"] = frappe.get_all(
			"Lease Contract",
			filters={"renewed_from_contract": contract_doc.renewed_from_contract},
			fields=["name", "status", "start_date", "end_date"],
		)

		# Previous must be eligible for renewal
		if previous.is_historical or previous.is_archived:
			frappe.throw(frappe._("العقد السابق غير صالح للتجديد"))
		if previous.status in ("evicted", "cancelled"):
			frappe.throw(frappe._("العقد السابق غير صالح للتجديد"))
		if previous.status == "active":
			period = get_contract_period_status(previous.start_date, previous.end_date)
			if period != "current":
				frappe.throw(frappe._("العقد السابق غير صالح للتجديد"))
		elif previous.status == "expired":
			# expired is eligible as long as it is not closed by another approved started renewal
			started_renewal = get_started_renewal(previous, today)
			if started_renewal and started_renewal.get("name") != contract_doc.name:
				frappe.throw(frappe._("العقد السابق مغلق بالفعل بتجديد آخر"))
		else:
			frappe.throw(frappe._("العقد السابق غير صالح للتجديد"))

		# At most one non-cancelled/non-evicted renewal at a time
		# Source: contract-validation.ts:256-261
		duplicate_renewal = any(
			r.get("name") != contract_doc.name
			and r.get("status") not in ("cancelled", "evicted")
			for r in previous["renewals"]
		)
		if duplicate_renewal:
			frappe.throw(frappe._("يوجد تجديد آخر غير ملغى لهذا العقد"))

		# Validate first due date == previous.endDate + 1 (calendar day only)
		# Source: contract-validation.ts:263-277
		if not contract_doc.first_due_date:
			frappe.throw(frappe._("تاريخ أول استحقاق التجديد مطلوب"))

		expected_first = to_calendar_day(get_renewal_first_due_date(contract_doc.renewed_from_contract))
		actual_first = to_calendar_day(contract_doc.first_due_date)
		actual_start = to_calendar_day(contract_doc.start_date)

		if actual_start != actual_first:
			frappe.throw(frappe._("تاريخ بداية التجديد وتاريخ أول استحقاقه يجب أن يكونا متطابقين"))

		if actual_first != expected_first:
			frappe.throw(frappe._("تاريخ أول استحقاق التجديد يجب أن يكون اليوم التالي لنهاية العقد السابق"))

	# 4. Operational occupancy checks
	# Excluded IDs: the current contract and the previous contract (if renewal).
	# Source: contract-validation.ts:281.
	excluded_ids = [contract_doc.name]
	if previous and previous.get("name"):
		excluded_ids.append(previous["name"])

	# Operational occupancy check 1: ANY expired contract (not historical, not
	# closed-by-renewal, startDate <= today) on the unit → block.
	# Source: contract-validation.ts:283-296.
	expired_contract = frappe.get_all(
		"Lease Contract",
		filters={
			"unit": contract_doc.unit,
			"status": "expired",
			"is_historical": 0,
			"closed_by_renewal_at": ["is", "not set"],
			"start_date": ["<=", today],
			"name": ["not in", excluded_ids],
		},
		fields=["name"],
		limit=1,
	)
	if expired_contract:
		frappe.throw(frappe._("الوحدة مؤجرة (عقد منتهي لم يُخلاً بعد) ولا يمكن اعتماد عقد جديد عليها"))

	# Operational occupancy check 2: most recent cancelled contract with
	# cancelledAt >= its own startDate on the unit → block.
	# Source: contract-validation.ts:298-315 — findFirst with orderBy cancelledAt desc.
	cancelled_contract = frappe.get_all(
		"Lease Contract",
		filters={
			"unit": contract_doc.unit,
			"status": "cancelled",
			"cancelled_at": ["is", "set"],
			"name": ["not in", excluded_ids],
		},
		fields=["name", "start_date", "cancelled_at"],
		order_by="cancelled_at desc",
		limit=1,
	)
	if cancelled_contract:
		cc = cancelled_contract[0]
		cc_cancelled_at = to_calendar_day(cc.cancelled_at)
		cc_start = to_calendar_day(cc.start_date)
		if cc_cancelled_at >= cc_start:
			frappe.throw(frappe._("الوحدة مؤجرة (عقد ملغي لم يُخلاً بعد) ولا يمكن اعتماد عقد جديد عليها"))

	# 5. Temporal overlap check
	# Source: contract-validation.ts:318-321
	overlap = check_contract_overlap(contract_doc.unit, contract_doc.start_date, contract_doc.end_date, exclude=contract_doc.name)
	if overlap:
		_raise_overlap_error(overlap)


# ---------------------------------------------------------------------------
# Overlap detection  (source: checkContractOverlap)
# ---------------------------------------------------------------------------


def _raise_overlap_error(overlap_contract: dict) -> None:
	"""Raise the appropriate Arabic overlap error based on the conflicting contract's status."""
	# Source: contract-validation.ts:319-321 — single unified overlap message.
	frappe.throw(frappe._("يوجد عقد متداخل مع نفس الوحدة في الفترة المحددة"))


def check_contract_overlap(unit_name, start_date, end_date, exclude=None) -> dict | None:
	"""Detect any active/expired-not-closed/cancelled contract overlapping dates on same unit.

	Excludes draft and evicted contracts.
	Source: ``checkContractOverlap`` (contract-validation.ts:15-63).

	The original uses three separate OR conditions in the Prisma query:
	  - active: date overlap only
	  - expired: isHistorical=false, closedByRenewalAt=null, date overlap
	  - cancelled: cancelledAt not null, date overlap
	For cancelled, an additional post-check excludes contracts cancelled before
	their own start date (tenant never moved in).
	"""
	start = to_calendar_day(start_date)
	end = to_calendar_day(end_date)

	filters = {
		"unit": unit_name,
		"status": ["in", ["active", "expired", "cancelled"]],
	}

	if exclude:
		filters["name"] = ["!=", exclude]

	contracts = frappe.get_all(
		"Lease Contract",
		filters=filters,
		fields=["name", "contract_number", "status", "start_date", "end_date",
				"cancelled_at", "is_historical", "closed_by_renewal_at"],
	)

	for c in contracts:
		c_start = to_calendar_day(c.start_date)
		c_end = to_calendar_day(c.end_date)

		# Per-status filters (matching the original's OR conditions)
		if c.status == "expired":
			# expired: must not be historical and not closed by renewal
			if c.is_historical:
				continue
			if c.closed_by_renewal_at:
				continue
		elif c.status == "cancelled":
			# cancelled: must have cancelledAt set
			if not c.cancelled_at:
				continue
			# A cancelled contract only counts as overlapping if the tenant
			# was already occupying the unit: cancelledAt >= contractStart.
			# Source: contract-validation.ts:56-60
			cancelled_at = to_calendar_day(c.cancelled_at)
			if cancelled_at < c_start:
				continue
		# active: no additional filters

		# Check date overlap: [start, end] ∩ [c_start, c_end]
		if start <= c_end and end >= c_start:
			return c

	return None


# ---------------------------------------------------------------------------
# Unit status helpers  (source: getUnitCurrentContract, getUnitUpcomingContract)
# ---------------------------------------------------------------------------


def get_unit_current_contract(unit_name: str) -> dict | None:
	"""Active contract whose period includes today (latest start_date)."""
	today = to_calendar_day(frappe.utils.today())
	contracts = frappe.get_all(
		"Lease Contract",
		filters={
			"unit": unit_name,
			"status": "active",
			"start_date": ["<=", today],
			"end_date": [">=", today],
		},
		fields=["name", "contract_number", "start_date", "end_date"],
		order_by="start_date desc",
		limit=1,
	)
	return contracts[0] if contracts else None


def get_unit_upcoming_contract(unit_name: str) -> dict | None:
	"""Active contract with start_date > today (earliest start_date)."""
	today = to_calendar_day(frappe.utils.today())
	contracts = frappe.get_all(
		"Lease Contract",
		filters={
			"unit": unit_name,
			"status": "active",
			"start_date": [">", today],
		},
		fields=["name", "contract_number", "start_date", "end_date"],
		order_by="start_date asc",
		limit=1,
	)
	return contracts[0] if contracts else None


# ---------------------------------------------------------------------------
# Unit status update  (source: updateUnitStatus)
# ---------------------------------------------------------------------------


def update_unit_status(unit_name: str, status: str) -> None:
	"""Update the unit's status field directly in the database.

	Source: ``updateUnitStatus`` (contract-validation.ts:351-357).
	"""
	frappe.db.set_value("Rental Unit", unit_name, "status", status, update_modified=False)


# ---------------------------------------------------------------------------
# Unit status engine  (source: recalculateUnitStatus)
# ---------------------------------------------------------------------------


def recalculate_unit_status(unit_name: str) -> str:
	"""Recompute ``Unit.status`` from contracts.

	Algorithm (source: ``recalculateUnitStatus``):
	1. Current active contract (start <= today <= end) → rented
	2. Expired contract (not historical, not closed by renewal) → rented
	3. Cancelled contract with cancelledAt >= startDate → rented
	4. Upcoming active contract (start > today) → reserved
	5. Default → empty
	"""
	from rental.rental.services.unit_service import derive_unit_status

	unit_doc = frappe.get_doc("Rental Unit", unit_name)
	derived = derive_unit_status(unit_doc)
	frappe.db.set_value("Rental Unit", unit_name, "status", derived, update_modified=False)
	return derived


# ---------------------------------------------------------------------------
# Contract expiration  (source: expireContracts)
# ---------------------------------------------------------------------------


def expire_contracts() -> int:
	"""Flip active contracts with end_date < today to expired.

	Source: ``expireContracts``.
	"""
	today = to_calendar_day(frappe.utils.today())

	contracts = frappe.get_all(
		"Lease Contract",
		filters={"status": "active", "end_date": ["<", today]},
		fields=["name", "unit", "renewed_from_contract"],
	)

	count = 0
	for c in contracts:
		# Check for an approved started renewal
		started_renewal = frappe.db.exists(
			"Lease Contract",
			{
				"renewed_from_contract": c.name,
				"status": ["not in", ["draft", "cancelled", "evicted"]],
				"start_date": ["<=", today],
			},
		)

		if started_renewal:
			frappe.db.set_value("Lease Contract", c.name, {
				"status": "expired",
				"closed_by_renewal_at": frappe.utils.now(),
			}, update_modified=False)
		else:
			frappe.db.set_value("Lease Contract", c.name, "status", "expired", update_modified=False)

		# Recalculate unit status
		recalculate_unit_status(c.unit)
		count += 1

	# Close any previously expired contracts whose approved renewal has now started.
	# This is the single catch-up path for contracts that became expired before
	# their renewal was approved or before the renewal's start date arrived.
	# Source: contract-validation.ts:470-476
	from rental.rental.services.renewal_service import close_expired_contracts_by_renewal
	newly_closed = close_expired_contracts_by_renewal(today)
	for closed in newly_closed:
		recalculate_unit_status(closed["unit"])

	return count


# ---------------------------------------------------------------------------
# Contract action eligibility  (source: lib/utils.ts → canRenewContract etc.)
# ---------------------------------------------------------------------------


def can_renew_contract(contract_doc) -> bool:
	"""Eligible for renewal.

	Source: ``canRenewContract``.
	- Not archived, not historical, not closed by renewal.
	- No existing non-cancelled/non-evicted renewal.
	- Status must be active or expired.
	- If active: must be current (start <= today <= end) with ≤ alert_days left.
	- If expired: always eligible.
	"""
	if contract_doc.is_archived:
		return False
	if contract_doc.is_historical:
		return False
	if contract_doc.closed_by_renewal_at:
		return False
	if contract_doc.status not in ("active", "expired"):
		return False

	# A12: No existing non-cancelled/non-evicted renewal.
	# Source: canRenewContract (utils.ts:182).
	existing_renewal = frappe.db.exists(
		"Lease Contract",
		{
			"renewed_from_contract": contract_doc.name,
			"status": ["not in", ["cancelled", "evicted"]],
		},
	)
	if existing_renewal:
		return False

	if contract_doc.status == "active":
		today = to_calendar_day(frappe.utils.today())
		start = to_calendar_day(contract_doc.start_date)
		end = to_calendar_day(contract_doc.end_date)
		# Must be current (not upcoming)
		if start > today:
			return False
		# Must be within alert_days of end
		alert_days = _get_contract_alert_days(contract_doc)
		days_left = (end - today).days
		if days_left > alert_days:
			return False

	return True


def _get_contract_alert_days(contract_doc) -> int:
	"""Return the configured alert days (default 30)."""
	try:
		from rental.rental.doctype.rental_settings.rental_settings import get_setting_value
		val = get_setting_value(contract_doc.rental_account, "contract_alert_days")
		if val:
			return int(val)
	except Exception:
		pass
	return 30


def can_evict_contract(contract_doc) -> bool:
	"""Eligible for eviction.

	Source: ``canEvictContract`` (utils.ts:202-218).
	- Not archived, not historical, not closed by renewal.
	- No approved renewal (status not in draft/cancelled/evicted).
	- Status expired → eligible.
	- Status cancelled with cancelledAt >= startDate → eligible.
	"""
	if contract_doc.is_archived:
		return False
	if contract_doc.is_historical:
		return False
	if contract_doc.closed_by_renewal_at:
		return False

	# No approved renewal (draft/cancelled/evicted renewals don't block).
	has_approved_renewal = frappe.db.exists(
		"Lease Contract",
		{
			"renewed_from_contract": contract_doc.name,
			"status": ["not in", ["draft", "cancelled", "evicted"]],
		},
	)
	if has_approved_renewal:
		return False

	if contract_doc.status == "expired":
		return True
	if contract_doc.status == "cancelled" and contract_doc.cancelled_at:
		cancelled_at = to_calendar_day(contract_doc.cancelled_at)
		start_date = to_calendar_day(contract_doc.start_date)
		return cancelled_at >= start_date
	return False


def can_archive_contract_eligible(contract_doc) -> bool:
	"""Eligible for archive.

	Source: ``canArchiveContract`` (utils.ts:220-228).
	- Not archived
	- Evicted
	- Expired and (historical or closed by an approved started renewal)
	- Cancelled before start date (cancelledAt < startDate)
	"""
	if contract_doc.is_archived:
		return False

	if contract_doc.status == "evicted":
		return True

	if contract_doc.status == "expired" and (contract_doc.is_historical or contract_doc.closed_by_renewal_at):
		return True

	if contract_doc.status == "cancelled" and contract_doc.cancelled_at:
		cancelled_at = to_calendar_day(contract_doc.cancelled_at)
		start_date = to_calendar_day(contract_doc.start_date)
		if cancelled_at < start_date:
			return True

	return False


# ---------------------------------------------------------------------------
# Contract number uniqueness  (source: validateContractNumber)
# ---------------------------------------------------------------------------


def validate_contract_number(contract_number: str, exclude_name: str | None = None) -> None:
	"""Ensure contract_number is unique.

	Source: ``validateContractNumber`` (contract-validation.ts:100-107).
	Raises Arabic error if duplicate found.
	"""
	if not contract_number:
		return
	filters = {"contract_number": contract_number}
	if exclude_name:
		filters["name"] = ["!=", exclude_name]
	if frappe.db.exists("Lease Contract", filters):
		frappe.throw(frappe._("رقم العقد مستخدم مسبقاً"))


# ---------------------------------------------------------------------------
# Historical contract detection  (source: isHistoricalContract)
# ---------------------------------------------------------------------------


def is_historical_contract(start_date, end_date) -> bool:
	"""Return True if the contract period is in the past.

	Source: ``isHistoricalContract`` (contract-validation.ts:481-483).
	"""
	return get_contract_period_status(start_date, end_date) == "past"
