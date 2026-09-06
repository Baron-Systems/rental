"""Tenant API: list, detail, create, update, delete, balance, statement.

Ported from ``src/app/api/tenants/**``.

Behaviour matches the source-of-truth document:
- Search across full_name / national_id / phone (OR, contains).
- contract_state / building / unit filters scope which tenants appear.
- List returns per-tenant balance, totalDues, totalReceipts,
  currentContractsCount, plus global stats (total/debt/credit/zero).
- print=true returns all matching tenants (no pagination) with a single
  representative live contract (currentContract) and balances.
- fullName and nationalId are immutable after creation.
- is_active cannot be changed through the API.
- Statement rejects a contractId that does not belong to the tenant (403).
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager


DEFAULT_PAGE_SIZE = 15
PAGE_SIZE = 15


# ---------------------------------------------------------------------------
# List tenants  (source: GET /api/tenants)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_tenants(
	search=None,
	limit=15,
	simple=0,
	include_inactive=0,
	print=0,
	page=1,
	contract_state=None,
	building=None,
	unit=None,
):
	"""List tenants with optional search, filtering, balance, and stats.

	Source: ``GET /api/tenants``.
	"""
	account = get_current_rental_account()
	today = frappe.utils.today()

	base_filters = {}
	if account:
		base_filters["rental_account"] = account
	if not int(include_inactive):
		base_filters["is_active"] = 1

	# ---- simple mode: limited fields, no balance ----
	if int(simple):
		filters = dict(base_filters)
		or_filters = _search_or_filters(search)
		tenants = frappe.get_all(
			"Rental Tenant",
			filters=filters,
			or_filters=or_filters,
			fields=["name", "full_name", "phone", "national_id"],
			order_by="creation desc, name asc",
			limit_page_length=min(int(limit), 100),
		)
		return {"tenants": tenants}

	# ---- Build the tenant filter, including contract_state/building/unit ----
	tenant_filters = dict(base_filters)
	or_filters = _search_or_filters(search)

	# contract_state / building / unit filter the tenants via their contracts
	contract_filter_present = contract_state in ("current", "upcoming", "none") or building or unit
	tenant_names_from_contracts = None
	if contract_filter_present:
		tenant_names_from_contracts = _tenants_matching_contract_filter(
			account, contract_state, building, unit, today, include_inactive=int(include_inactive)
		)
		if tenant_names_from_contracts is not None:
			# Intersect with base tenant filters
			if tenant_names_from_contracts:
				tenant_filters["name"] = ["in", tenant_names_from_contracts]
			else:
				# No tenant matches the contract filter → empty result
				return _empty_list_response(int(page), int(limit))

	# ---- Pagination ----
	page_size = 0 if int(print) else PAGE_SIZE
	start = (int(page) - 1) * PAGE_SIZE if not int(print) else 0

	tenants = frappe.get_all(
		"Rental Tenant",
		filters=tenant_filters,
		or_filters=or_filters,
		fields=[
			"name", "full_name", "national_id", "phone",
			"workplace", "guarantor_name", "guarantor_phone", "is_active",
			"creation",
		],
		order_by="creation desc, name asc",
		start=start,
		limit_page_length=page_size,
	)

	# ---- Enrich with balance + contract counts (+ currentContract in print) ----
	from rental.rental.services.balance_service import (
		get_tenant_balance,
		get_tenant_balance_stats,
	)

	for t in tenants:
		bal = get_tenant_balance(t["name"])
		t["totalDues"] = bal["totalDues"]
		t["totalReceipts"] = bal["totalReceipts"]
		t["totalRefunds"] = bal["totalRefunds"]
		t["balance"] = bal["balance"]
		t["currentContractsCount"] = _count_contracts(t["name"], today=today)

		if int(print):
			t["currentContract"] = _get_representative_current_contract(t["name"], today)

	# ---- Response ----
	if int(print):
		return {
			"tenants": tenants,
			"print": {"total": len(tenants)},
		}

	# ---- Global stats (active tenants only, non-print mode only) ----
	stats_where = dict(base_filters)
	if not int(include_inactive):
		stats_where["is_active"] = 1
	stats = get_tenant_balance_stats(stats_where)

	total = _count_tenants(tenant_filters, or_filters)
	pagination = {
		"page": int(page),
		"pageSize": PAGE_SIZE,
		"total": total,
		"totalPages": (total + PAGE_SIZE - 1) // PAGE_SIZE if PAGE_SIZE else 1,
	}

	return {"tenants": tenants, "pagination": pagination, "stats": stats}


def _count_tenants(filters: dict, or_filters: list) -> int:
	"""Count tenants honouring both filters and or_filters."""
	if not or_filters:
		return frappe.db.count("Rental Tenant", filters)
	# or_filters present: use get_all to count (count doesn't support or_filters)
	return len(frappe.get_all(
		"Rental Tenant",
		filters=filters,
		or_filters=or_filters,
		pluck="name",
	))


def _search_or_filters(search):
	"""Return Frappe ``or_filters`` for OR search across full_name / national_id / phone.

	Source: ``GET /api/tenants?search=...`` — contains on the three fields.
	Returns an empty list when no search term is given.
	"""
	if not search:
		return []
	return [
		["full_name", "like", f"%{search}%"],
		["national_id", "like", f"%{search}%"],
		["phone", "like", f"%{search}%"],
	]


def _empty_list_response(page, limit):
	return {
		"tenants": [],
		"pagination": {
			"page": page,
			"pageSize": limit,
			"total": 0,
			"totalPages": 0,
		},
		"stats": {"total": 0, "debt": 0, "credit": 0, "zero": 0},
	}


def _tenants_matching_contract_filter(
	account, contract_state, building, unit, today, include_inactive=0
):
	"""Return the set of tenant names that have contracts matching the filter.

	Returns ``None`` when no contract-level filter is active (caller should
	not restrict tenants by contract). Returns a (possibly empty) list
	otherwise.
	"""
	if not frappe.db.exists("DocType", "Lease Contract"):
		return [] if (contract_state in ("current", "upcoming", "none") or building or unit) else None

	contract_filters = {}
	if account:
		contract_filters["rental_account"] = account

	# Base "live" contract filter (active, not archived/historical/closed-by-renewal)
	live_base = {
		"status": "active",
		"is_archived": 0,
		"is_historical": 0,
		"closed_by_renewal_at": ["is", "not set"],
	}

	if building:
		contract_filters["building"] = building
	if unit:
		contract_filters["unit"] = unit

	if contract_state == "current":
		f = dict(contract_filters)
		f.update(live_base)
		f["start_date"] = ["<=", today]
		f["end_date"] = [">=", today]
		return frappe.get_all("Lease Contract", filters=f, pluck="tenant") or []

	if contract_state == "upcoming":
		f = dict(contract_filters)
		f.update(live_base)
		f["start_date"] = [">", today]
		return frappe.get_all("Lease Contract", filters=f, pluck="tenant") or []

	if contract_state == "none":
		# Tenants with NO live active contract
		f = dict(contract_filters)
		f.update(live_base)
		tenants_with_live = set(frappe.get_all("Lease Contract", filters=f, pluck="tenant") or [])
		all_tenant_filters = {}
		if account:
			all_tenant_filters["rental_account"] = account
		if not include_inactive:
			all_tenant_filters["is_active"] = 1
		all_tenants = set(frappe.get_all("Rental Tenant", filters=all_tenant_filters, pluck="name") or [])
		return list(all_tenants - tenants_with_live)

	# building/unit only (contract_state == all or None) → tenants with any matching contract
	if building or unit:
		return frappe.get_all("Lease Contract", filters=contract_filters, pluck="tenant") or []

	return None


def _count_contracts(tenant_name, today=None):
	"""Count current live contracts for a tenant.

	Source: list ``currentContractsCount`` — current active contracts only
	(start <= today <= end, not archived/historical/closed-by-renewal).
	"""
	if not frappe.db.exists("DocType", "Lease Contract"):
		return 0

	if today is None:
		today = frappe.utils.today()

	filters = {
		"tenant": tenant_name,
		"status": "active",
		"is_archived": 0,
		"is_historical": 0,
		"closed_by_renewal_at": ["is", "not set"],
		"start_date": ["<=", today],
		"end_date": [">=", today],
	}
	return frappe.db.count("Lease Contract", filters)


def _get_representative_current_contract(tenant_name, today):
	"""Return the first live contract (startDate asc) with building/unit.

	Source: print mode ``currentContract``.
	"""
	if not frappe.db.exists("DocType", "Lease Contract"):
		return None

	contracts = frappe.get_all(
		"Lease Contract",
		filters={
			"tenant": tenant_name,
			"status": "active",
			"is_archived": 0,
			"is_historical": 0,
			"closed_by_renewal_at": ["is", "not set"],
			"start_date": ["<=", today],
			"end_date": [">=", today],
		},
		fields=[
			"name", "contract_number", "status", "start_date", "end_date",
			"building", "unit",
		],
		order_by="start_date asc",
		limit=1,
	)
	if not contracts:
		return None
	c = contracts[0]
	if c.get("building"):
		c["building_name"] = frappe.db.get_value("Rental Building", c["building"], "building_name")
	if c.get("unit"):
		c["unit_number"] = frappe.db.get_value("Rental Unit", c["unit"], "unit_number")
	return c


# ---------------------------------------------------------------------------
# Get single tenant  (source: GET /api/tenants/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_tenant(name):
	"""Get a single tenant with all contracts, balance, and statement.

	Source: ``GET /api/tenants/[id]``.
	"""
	if not frappe.db.exists("Rental Tenant", name):
		frappe.throw(frappe._("المستأجر غير موجود"), frappe.DoesNotExistError)

	tenant = frappe.get_doc("Rental Tenant", name)
	tenant.check_permission("read")

	result = tenant.as_dict()

	# Add contracts with balances (all contracts, no status filter)
	if frappe.db.exists("DocType", "Lease Contract"):
		from rental.rental.services.balance_service import get_contract_balance

		contracts = frappe.get_all(
			"Lease Contract",
			filters={"tenant": name},
			fields=["name", "contract_number", "status", "start_date", "end_date",
					"rent_amount", "payment_frequency", "is_archived", "is_historical",
					"building", "unit"],
			order_by="start_date desc",
		)
		for c in contracts:
			bal = get_contract_balance(c["name"])
			c["totalDues"] = bal["totalDues"]
			c["totalReceipts"] = bal["totalReceipts"]
			c["balance"] = bal["balance"]
			if c.get("building"):
				c["building_name"] = frappe.db.get_value("Rental Building", c["building"], "building_name")
			if c.get("unit"):
				c["unit_number"] = frappe.db.get_value("Rental Unit", c["unit"], "unit_number")
		result["contracts"] = contracts
	else:
		result["contracts"] = []

	# Add balance and statement (default scope)
	from rental.rental.services.balance_service import get_tenant_balance
	from rental.rental.services.statement_service import get_tenant_statement

	result["balance"] = get_tenant_balance(name)
	result["statement"] = get_tenant_statement(name)

	return result


# ---------------------------------------------------------------------------
# Create tenant  (source: POST /api/tenants)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_tenant(**kwargs):
	"""Create a new tenant.

	Source: ``POST /api/tenants``.
	Required: full_name. is_active defaults to true. No uniqueness enforced.
	"""
	account = get_current_rental_account()

	if not kwargs.get("full_name"):
		frappe.throw(frappe._("الاسم الكامل مطلوب"))

	doc = frappe.get_doc({
		"doctype": "Rental Tenant",
		"rental_account": account,
		"full_name": kwargs.get("full_name"),
		"national_id": kwargs.get("national_id"),
		"phone": kwargs.get("phone"),
		"email": kwargs.get("email"),
		"address": kwargs.get("address"),
		"workplace": kwargs.get("workplace"),
		"guarantor_name": kwargs.get("guarantor_name"),
		"guarantor_phone": kwargs.get("guarantor_phone"),
		"notes": kwargs.get("notes"),
		"is_active": 1,
	})
	doc.insert(ignore_permissions=is_system_manager())
	return doc.name


# ---------------------------------------------------------------------------
# Update tenant  (source: PUT /api/tenants/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def update_tenant(name, **kwargs):
	"""Update a tenant. full_name and national_id are immutable.

	Source: ``PUT /api/tenants/[id]``.
	Editable API fields: phone, workplace, guarantor_name,
	guarantor_phone. is_active is NOT editable.
	"""
	if not frappe.db.exists("Rental Tenant", name):
		frappe.throw(frappe._("المستأجر غير موجود"), frappe.DoesNotExistError)

	doc = frappe.get_doc("Rental Tenant", name)
	doc.check_permission("write")

	# Only allow updating non-identity fields (is_active excluded)
	allowed = ["phone", "email", "address", "workplace", "guarantor_name",
			   "guarantor_phone", "notes"]
	for field in allowed:
		if field in kwargs and kwargs[field] is not None:
			doc.set(field, kwargs[field])

	doc.save(ignore_permissions=is_system_manager())
	return doc.name


# ---------------------------------------------------------------------------
# Delete tenant  (source: DELETE /api/tenants/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def delete_tenant(name):
	"""Delete a tenant if no history exists.

	Source: ``DELETE /api/tenants/[id]``.
	Deletion is blocked by the doctype ``on_trash`` hook (contracts, dues,
	receipts, evictions).
	"""
	if not frappe.db.exists("Rental Tenant", name):
		frappe.throw(frappe._("المستأجر غير موجود"), frappe.DoesNotExistError)

	frappe.delete_doc("Rental Tenant", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Tenant balance  (source: GET /api/tenants/[id]/balance)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_tenant_balance_api(name):
	"""Get tenant balance.

	Source: ``GET /api/tenants/[id]/balance``.
	"""
	if not frappe.db.exists("Rental Tenant", name):
		frappe.throw(frappe._("المستأجر غير موجود"), frappe.DoesNotExistError)

	from rental.rental.services.balance_service import get_tenant_balance
	bal = get_tenant_balance(name)
	return {
		"tenantId": name,
		"totalDues": bal["totalDues"],
		"totalReceipts": bal["totalReceipts"],
		"totalRefunds": bal["totalRefunds"],
		"balance": bal["balance"],
	}


# ---------------------------------------------------------------------------
# Tenant statement  (source: GET /api/tenants/[id]/statement)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_tenant_statement_api(
	name,
	start_date=None,
	end_date=None,
	building=None,
	unit=None,
	contract=None,
	due_type=None,
	page=1,
	print=0,
):
	"""Get tenant statement with dues, waivers, and receipts.

	Source: ``GET /api/tenants/[id]/statement``.
	Verifies that ``contract`` (if provided) belongs to the tenant (403).
	"""
	if not frappe.db.exists("Rental Tenant", name):
		frappe.throw(frappe._("المستأجر غير موجود"), frappe.DoesNotExistError)

	# Verify contract ownership (TEN-BE-016)
	from rental.rental.services.statement_service import get_tenant_statement, apply_contract_filter
	apply_contract_filter(name, contract)

	filters = {}
	if start_date:
		filters["start_date"] = start_date
	if end_date:
		filters["end_date"] = end_date
	if building:
		filters["building"] = building
	if unit:
		filters["unit"] = unit
	if contract:
		filters["contract"] = contract
	if due_type:
		filters["due_type"] = due_type

	return get_tenant_statement(name, filters=filters, page=int(page), print_mode=bool(int(print)))
