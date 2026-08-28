"""Balance computation service.

Ported from ``src/services/balance.service.ts``.

Balance = effective approved dues (dueDate <= today) - active waivers
          - all approved receipts (no receiptDate filter).

All balances are derived (computed), never stored.

Statement logic is in ``statement_service.py`` per TENANTS_MIGRATION_SPEC §21.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import to_calendar_day, round_money


def _db_sum(doctype: str, filters: dict, fieldname: str = "amount") -> float:
	"""Compute SUM(fieldname) for matching records.

	Frappe's ``frappe.db.sum`` is not available in all versions, so we
	fall back to fetching the values and summing in Python.
	"""
	try:
		values = frappe.get_all(doctype, filters=filters, pluck=fieldname)
	except Exception:
		values = []
	return float(sum(float(v or 0) for v in values))


def _today():
	"""Calendar-day today (date object)."""
	return to_calendar_day(frappe.utils.today())


# ---------------------------------------------------------------------------
# Effective due total  (source: getEffectiveDueTotal)
# ---------------------------------------------------------------------------


def get_effective_due_total(filters: dict | None = None) -> float:
	"""Sum of approved dues (dueDate <= today by default) minus active waivers.

	Source: ``getEffectiveDueTotal``.

	The ``dueDate <= today`` filter is applied **unless** the caller already
	provides a ``due_date`` filter (e.g. a date range for the statement).
	"""
	due_filters = {"docstatus": 1}
	if filters:
		due_filters.update(filters)

	# Default: only dues whose dueDate <= today, unless caller overrode due_date
	if "due_date" not in due_filters:
		due_filters["due_date"] = ["<=", _today()]

	total_dues = _db_sum("Rental Due", due_filters, "amount")

	# Subtract active waivers linked to those dues
	waiver_filters = {"status": "active"}
	due_names = frappe.get_all("Rental Due", filters=due_filters, pluck="name")
	if due_names:
		waiver_filters["due"] = ["in", due_names]
	else:
		return 0.0

	total_waivers = _db_sum("Rental Due Waiver", waiver_filters, "amount")

	return round_money(float(total_dues) - float(total_waivers))


# ---------------------------------------------------------------------------
# Approved receipt total  (source: getApprovedReceiptTotal)
# ---------------------------------------------------------------------------


def get_approved_receipt_total(filters: dict | None = None) -> float:
	"""Sum of approved (submitted) receipts.

	Source: ``getApprovedReceiptTotal``.

	**No ``receiptDate`` filter is applied** — all approved receipts are
	counted regardless of date. This is intentional and matches the source
	of truth (INV-TEN-018).
	"""
	receipt_filters = {"docstatus": 1}
	if filters:
		receipt_filters.update(filters)

	total = _db_sum("Rental Receipt", receipt_filters, "amount")
	return round_money(float(total))


# ---------------------------------------------------------------------------
# Tenant balance  (source: getTenantBalance)
# ---------------------------------------------------------------------------


def get_tenant_balance(tenant_name: str) -> dict:
	"""Return {totalDues, totalReceipts, balance} for a tenant.

	Source: ``getTenantBalance``.
	- totalDues = effective approved dues with dueDate <= today (minus waivers)
	- totalReceipts = all approved receipts (no receiptDate filter)
	- balance = totalDues - totalReceipts
	"""
	total_dues = get_effective_due_total({"tenant": tenant_name})
	total_receipts = get_approved_receipt_total({"tenant": tenant_name})
	return {
		"tenant": tenant_name,
		"totalDues": total_dues,
		"totalReceipts": total_receipts,
		"balance": round_money(total_dues - total_receipts),
	}


# ---------------------------------------------------------------------------
# Contract balance  (source: getContractBalance)
# ---------------------------------------------------------------------------


def get_contract_balance(contract_name: str) -> dict:
	"""Return balance for a contract."""
	total_dues = get_effective_due_total({"contract": contract_name})
	total_receipts = get_approved_receipt_total({"contract": contract_name})
	return {
		"contract": contract_name,
		"totalDues": total_dues,
		"totalReceipts": total_receipts,
		"balance": round_money(total_dues - total_receipts),
	}


# ---------------------------------------------------------------------------
# Building balance  (source: getBuildingBalance)
# ---------------------------------------------------------------------------


def get_building_balance(building_name: str) -> dict:
	"""Return balance for a building."""
	total_dues = get_effective_due_total({"building": building_name})
	total_receipts = get_approved_receipt_total({"building": building_name})
	return {
		"building": building_name,
		"totalDues": total_dues,
		"totalReceipts": total_receipts,
		"balance": round_money(total_dues - total_receipts),
	}


# ---------------------------------------------------------------------------
# Tenant balance stats  (source: getTenantBalanceStats)
# ---------------------------------------------------------------------------


def get_tenant_balance_stats(where: dict | None = None) -> dict:
	"""Return stats: {total, debt, credit, zero} for a tenant filter.

	Source: ``getTenantBalanceStats``.
	"""
	where = where or {}
	tenants = frappe.get_all("Rental Tenant", filters=where, pluck="name")

	total = len(tenants)
	with_debt = 0
	with_credit = 0
	zero = 0

	for t in tenants:
		bal = get_tenant_balance(t)["balance"]
		if bal > 0:
			with_debt += 1
		elif bal < 0:
			with_credit += 1
		else:
			zero += 1

	return {
		"total": total,
		"debt": with_debt,
		"credit": with_credit,
		"zero": zero,
	}


# ---------------------------------------------------------------------------
# Bulk balance helpers  (source: getAllTenantBalances, getTenantBalances,
# getContractBalances, getBuildingBalances)
# ---------------------------------------------------------------------------


def get_all_tenant_balances() -> list[dict]:
	"""Return balances for all active tenants.

	Source: ``getAllTenantBalances`` (balance.service.ts:300-311).
	"""
	tenants = frappe.get_all("Rental Tenant", filters={"is_active": 1}, pluck="name")
	return [get_tenant_balance(t) for t in tenants]


def get_tenant_balances(tenant_names: list[str]) -> dict:
	"""Return a map {tenant_name: balance_dict} for the given tenants.

	Source: ``getTenantBalances`` (balance.service.ts:334-391).
	Uses bulk queries for performance.
	"""
	result = {}
	if not tenant_names:
		return result

	today = _today()

	# Bulk dues
	dues = frappe.get_all(
		"Rental Due",
		filters={
			"docstatus": 1,
			"due_date": ["<=", today],
			"tenant": ["in", tenant_names],
		},
		fields=["tenant", "amount"],
	)
	dues_map = {}
	for d in dues:
		dues_map[d.tenant] = dues_map.get(d.tenant, 0) + float(d.amount or 0)

	# Bulk receipts
	receipts = frappe.get_all(
		"Rental Receipt",
		filters={
			"docstatus": 1,
			"tenant": ["in", tenant_names],
		},
		fields=["tenant", "amount"],
	)
	receipts_map = {}
	for r in receipts:
		receipts_map[r.tenant] = receipts_map.get(r.tenant, 0) + float(r.amount or 0)

	# Bulk waivers (via due names)
	due_names = [d.name for d in frappe.get_all(
		"Rental Due",
		filters={
			"docstatus": 1,
			"due_date": ["<=", today],
			"tenant": ["in", tenant_names],
		},
		fields=["name", "tenant"],
	)]
	waivers_map = {}
	if due_names:
		waivers = frappe.db.sql(
			"""
			SELECT w.amount, d.tenant
			FROM `tabRental Due Waiver` w
			JOIN `tabRental Due` d ON w.due = d.name
			WHERE w.status = 'active' AND w.due IN %s
			""",
			[tuple(due_names)],
			as_dict=True,
		)
		for w in waivers:
			waivers_map[w.tenant] = waivers_map.get(w.tenant, 0) + float(w.amount or 0)

	for tenant_name in tenant_names:
		total_dues = round_money(dues_map.get(tenant_name, 0) - waivers_map.get(tenant_name, 0))
		total_receipts = round_money(receipts_map.get(tenant_name, 0))
		result[tenant_name] = {
			"tenant": tenant_name,
			"totalDues": total_dues,
			"totalReceipts": total_receipts,
			"balance": round_money(total_dues - total_receipts),
		}

	return result


def get_contract_balances(contract_names: list[str]) -> dict:
	"""Return a map {contract_name: balance_dict} for the given contracts.

	Source: ``getContractBalances`` (balance.service.ts:393-454).
	Uses bulk queries for performance.
	"""
	result = {}
	if not contract_names:
		return result

	today = _today()

	dues = frappe.get_all(
		"Rental Due",
		filters={
			"docstatus": 1,
			"due_date": ["<=", today],
			"contract": ["in", contract_names],
		},
		fields=["contract", "amount", "name"],
	)
	dues_map = {}
	due_names_by_contract = {}
	for d in dues:
		dues_map[d.contract] = dues_map.get(d.contract, 0) + float(d.amount or 0)
		due_names_by_contract.setdefault(d.contract, []).append(d.name)

	receipts = frappe.get_all(
		"Rental Receipt",
		filters={
			"docstatus": 1,
			"contract": ["in", contract_names],
		},
		fields=["contract", "amount"],
	)
	receipts_map = {}
	for r in receipts:
		if r.contract:
			receipts_map[r.contract] = receipts_map.get(r.contract, 0) + float(r.amount or 0)

	# Bulk waivers
	all_due_names = [n for names in due_names_by_contract.values() for n in names]
	waivers_map = {}
	if all_due_names:
		waivers = frappe.db.sql(
			"""
			SELECT w.amount, d.contract
			FROM `tabRental Due Waiver` w
			JOIN `tabRental Due` d ON w.due = d.name
			WHERE w.status = 'active' AND w.due IN %s
			""",
			[tuple(all_due_names)],
			as_dict=True,
		)
		for w in waivers:
			if w.contract:
				waivers_map[w.contract] = waivers_map.get(w.contract, 0) + float(w.amount or 0)

	for contract_name in contract_names:
		total_dues = round_money(dues_map.get(contract_name, 0) - waivers_map.get(contract_name, 0))
		total_receipts = round_money(receipts_map.get(contract_name, 0))
		result[contract_name] = {
			"contract": contract_name,
			"totalDues": total_dues,
			"totalReceipts": total_receipts,
			"balance": round_money(total_dues - total_receipts),
		}

	return result


def get_building_balances(building_names: list[str]) -> dict:
	"""Return a map {building_name: balance_dict} for the given buildings.

	Source: ``getBuildingBalances`` (balance.service.ts:463-524).
	Uses bulk queries for performance.
	"""
	result = {}
	if not building_names:
		return result

	today = _today()

	dues = frappe.get_all(
		"Rental Due",
		filters={
			"docstatus": 1,
			"due_date": ["<=", today],
			"building": ["in", building_names],
		},
		fields=["building", "amount", "name"],
	)
	dues_map = {}
	due_names_by_building = {}
	for d in dues:
		if d.building:
			dues_map[d.building] = dues_map.get(d.building, 0) + float(d.amount or 0)
			due_names_by_building.setdefault(d.building, []).append(d.name)

	receipts = frappe.get_all(
		"Rental Receipt",
		filters={
			"docstatus": 1,
			"building": ["in", building_names],
		},
		fields=["building", "amount"],
	)
	receipts_map = {}
	for r in receipts:
		if r.building:
			receipts_map[r.building] = receipts_map.get(r.building, 0) + float(r.amount or 0)

	# Bulk waivers
	all_due_names = [n for names in due_names_by_building.values() for n in names]
	waivers_map = {}
	if all_due_names:
		waivers = frappe.db.sql(
			"""
			SELECT w.amount, d.building
			FROM `tabRental Due Waiver` w
			JOIN `tabRental Due` d ON w.due = d.name
			WHERE w.status = 'active' AND w.due IN %s
			""",
			[tuple(all_due_names)],
			as_dict=True,
		)
		for w in waivers:
			if w.building:
				waivers_map[w.building] = waivers_map.get(w.building, 0) + float(w.amount or 0)

	for building_name in building_names:
		total_dues = round_money(dues_map.get(building_name, 0) - waivers_map.get(building_name, 0))
		total_receipts = round_money(receipts_map.get(building_name, 0))
		result[building_name] = {
			"building": building_name,
			"totalDues": total_dues,
			"totalReceipts": total_receipts,
			"balance": round_money(total_dues - total_receipts),
		}

	return result
