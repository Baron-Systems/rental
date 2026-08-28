"""Statement service layer.

Source: TENANTS_MIGRATION_SPEC §21.
Separated from balance_service per spec architecture.
"""

from __future__ import annotations

import frappe
from datetime import date

from rental.rental.utils.date_utils import to_calendar_day, round_money


STATEMENT_PAGE_SIZE = 15


def _today():
	"""Calendar-day today (date object)."""
	return to_calendar_day(frappe.utils.today())


def _contract_number(contract_name):
	"""Resolve a contract name to its contract_number (for statement lines)."""
	if not contract_name:
		return None
	return frappe.db.get_value("Lease Contract", contract_name, "contract_number") or None


def _unit_number(unit_name):
	"""Resolve a unit name to its unit_number (for statement lines)."""
	if not unit_name:
		return None
	return frappe.db.get_value("Rental Unit", unit_name, "unit_number") or None


def _building_name(building_name):
	"""Resolve a building name (ID) to its building_name (display)."""
	if not building_name:
		return None
	return frappe.db.get_value("Rental Building", building_name, "building_name") or None


def apply_contract_filter(tenant_name: str, contract: str | None) -> None:
	"""Verify that a contract belongs to the tenant.

	Source: TEN-BE-016.
	Raises PermissionError if contract is not owned by tenant.
	"""
	if contract:
		contract_tenant = frappe.db.get_value("Lease Contract", contract, "tenant")
		if contract_tenant != tenant_name:
			frappe.throw(frappe._("العقد غير تابع لهذا المستأجر"), frappe.PermissionError)


def build_statement_lines(dues: list, receipts: list, waivers: list, due_type_names: dict) -> list:
	"""Build statement entries from dues, receipts, and waivers.

	Source: TEN-BE-010, TEN-BE-011.
	"""
	entries = []

	for d in dues:
		due_date = to_calendar_day(d.get("due_date") or d.get("transaction_date"))
		due_type_label = due_type_names.get(d.get("due_type"), "")
		# Source: balance.service.ts — description uses sourceType check + dateStr
		date_str = ""
		if due_date:
			try:
				date_str = due_date.strftime("%B %Y")
			except Exception:
				date_str = ""
		if d.get("source_type") == "auto_contract":
			description = f"{due_type_label} - {date_str}" if due_type_label else date_str
		else:
			description = d.get("description") or due_type_label or ""
		entries.append({
			"type": "due",
			"id": d["name"],
			"date": due_date,
			"debit": float(d["amount"]),
			"credit": 0,
			"description": description,
			"reference": d.get("reference_number") or d.get("due_number") or "",
			"contract": d.get("contract"),
			"contractNumber": _contract_number(d.get("contract")),
			"building": _building_name(d.get("building")),
			"unit": _unit_number(d.get("unit")),
			"typeName": due_type_label or "",
			"due_type": d.get("due_type"),
			"creation": d.get("creation"),
		})

	# Build a lookup for parent dues (for waivers)
	dues_by_name = {d["name"]: d for d in dues}

	for w in waivers:
		parent_due = dues_by_name.get(w["due"])
		due_date = None
		parent_due_type = None
		parent_building = None
		parent_unit = None
		parent_contract = None
		parent_due_number = ""
		if parent_due:
			due_date = to_calendar_day(parent_due.get("due_date") or parent_due.get("transaction_date"))
			parent_due_type = parent_due.get("due_type")
			parent_building = parent_due.get("building")
			parent_unit = parent_due.get("unit")
			parent_contract = parent_due.get("contract")
			parent_due_number = parent_due.get("due_number") or ""
		due_type_label = due_type_names.get(parent_due_type, "")
		# Source: balance.service.ts — typeName and description logic
		if w.get("source_type") == "contract_cancellation":
			type_name = f"تسوية إلغاء العقد — {due_type_label}" if due_type_label else "تسوية إلغاء العقد"
			description = w.get("reason") or "تسوية إلغاء العقد"
		else:
			type_name = f"إعفاء — {due_type_label}" if due_type_label else "إعفاء"
			waiver_reason = w.get("reason") or ""
			description = f"إعفاء - {waiver_reason}"
		entries.append({
			"type": "waiver",
			"id": w["name"],
			"date": due_date,
			"debit": 0,
			"credit": float(w["amount"]),
			"description": description,
			"reference": parent_due_number,
			"contract": parent_contract,
			"contractNumber": _contract_number(parent_contract),
			"building": _building_name(parent_building),
			"unit": _unit_number(parent_unit),
			"typeName": type_name,
			"due_type": parent_due_type,
			"creation": w.get("creation"),
		})

	for r in receipts:
		entries.append({
			"type": "receipt",
			"id": r["name"],
			"date": to_calendar_day(r.get("receipt_date")),
			"debit": 0,
			"credit": float(r["amount"]),
			"description": "دفعة من المستأجر",
			"reference": r.get("receipt_number") or "",
			"contract": r.get("contract"),
			"contractNumber": _contract_number(r.get("contract")),
			"building": _building_name(r.get("building")),
			"unit": _unit_number(r.get("unit")),
			"typeName": "سند قبض",
			"due_type": None,
			"creation": r.get("creation"),
		})

	return entries


def get_tenant_statement(
	tenant_name: str,
	filters: dict | None = None,
	page: int | None = None,
	print_mode: bool = False,
) -> dict:
	"""Full statement merging dues, waivers, and receipts.

	Source: ``getTenantStatement``.
	- Dues: debit = amount, date = dueDate
	- Waivers (active): credit = waiver.amount, date = parent due.dueDate
	- Receipts: credit = amount, date = receiptDate
	- Sorted by date asc → createdAt asc → id asc
	- Running balance (cumulative)
	- Opening balance is hard-coded 0
	- Default scope: dueDate <= today and receiptDate <= today
	"""
	filters = filters or {}
	today = _today()

	# ---- Collect dues ----
	due_filters = {"tenant": tenant_name, "docstatus": 1}

	if filters.get("start_date") and filters.get("end_date"):
		due_filters["due_date"] = ["between", [filters["start_date"], filters["end_date"]]]
	elif filters.get("start_date"):
		due_filters["due_date"] = [">=", filters["start_date"]]
	elif filters.get("end_date"):
		due_filters["due_date"] = ["<=", filters["end_date"]]
	else:
		due_filters["due_date"] = ["<=", today]

	if filters.get("building"):
		due_filters["building"] = filters["building"]
	if filters.get("unit"):
		due_filters["unit"] = filters["unit"]
	if filters.get("contract"):
		due_filters["contract"] = filters["contract"]
	if filters.get("due_type"):
		due_filters["due_type"] = filters["due_type"]

	dues = frappe.get_all(
		"Rental Due",
		filters=due_filters,
		fields=[
			"name", "due_number", "due_date", "transaction_date", "amount",
			"description", "due_type", "contract", "period_label",
			"building", "unit", "source_type", "creation",
		],
	)

	# Resolve due_type names for line descriptions
	due_type_names = {}
	dt_names = list({d["due_type"] for d in dues if d.get("due_type")})
	if dt_names:
		for dt_name in dt_names:
			due_type_names[dt_name] = frappe.db.get_value(
				"Rental Due Type", dt_name, "due_type_name"
			) or dt_name

	# ---- Collect active waivers for these dues ----
	due_names = [d["name"] for d in dues]
	waivers = []
	if due_names:
		waivers = frappe.get_all(
			"Rental Due Waiver",
			filters={"due": ["in", due_names], "status": "active"},
			fields=["name", "due", "amount", "reason", "source_type", "cancellation_reason", "creation"],
		)

	# ---- Collect receipts ----
	receipt_filters = {"tenant": tenant_name, "docstatus": 1}

	if filters.get("start_date") and filters.get("end_date"):
		receipt_filters["receipt_date"] = ["between", [filters["start_date"], filters["end_date"]]]
	elif filters.get("start_date"):
		receipt_filters["receipt_date"] = [">=", filters["start_date"]]
	elif filters.get("end_date"):
		receipt_filters["receipt_date"] = ["<=", filters["end_date"]]
	else:
		receipt_filters["receipt_date"] = ["<=", today]

	if filters.get("building"):
		receipt_filters["building"] = filters["building"]
	if filters.get("unit"):
		receipt_filters["unit"] = filters["unit"]
	if filters.get("contract"):
		receipt_filters["contract"] = filters["contract"]

	receipts = frappe.get_all(
		"Rental Receipt",
		filters=receipt_filters,
		fields=[
			"name", "receipt_number", "receipt_date", "amount",
			"payment_method", "contract", "building", "unit", "notes", "creation",
		],
	)

	# ---- Build statement entries ----
	entries = build_statement_lines(dues, receipts, waivers, due_type_names)

	# ---- Sort by date asc → createdAt asc → id asc ----
	entries.sort(key=lambda e: (
		e.get("date") or date.min,
		e.get("creation") or "",
		str(e.get("id") or ""),
	))

	# ---- Compute running balance ----
	running = 0.0
	for e in entries:
		running += e["debit"] - e["credit"]
		e["balance"] = round_money(running)

	total_dues = round_money(sum(e["debit"] for e in entries))
	total_receipts = round_money(sum(e["credit"] for e in entries))
	closing_balance = round_money(total_dues - total_receipts)

	# ---- Pagination ----
	total_entries = len(entries)
	requested_page = 1 if page is None else max(page, 1)
	if not print_mode and page is not None:
		start = (requested_page - 1) * STATEMENT_PAGE_SIZE
		end = start + STATEMENT_PAGE_SIZE
		entries = entries[start:end]

	pagination = None
	if page is not None or print_mode:
		pagination = {
			"page": 1 if print_mode else requested_page,
			"pageSize": STATEMENT_PAGE_SIZE,
			"total": total_entries,
			"totalPages": (total_entries + STATEMENT_PAGE_SIZE - 1) // STATEMENT_PAGE_SIZE,
		}

	return {
		"tenant": tenant_name,
		"lines": entries,
		"openingBalance": 0,
		"totalDues": total_dues,
		"totalReceipts": total_receipts,
		"closingBalance": closing_balance,
		"pagination": pagination,
	}
