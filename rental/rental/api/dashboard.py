"""Dashboard and Notifications APIs.

Ported from ``src/app/api/dashboard/route.ts`` and ``src/app/api/notifications/route.ts``.
"""

from __future__ import annotations

import frappe
from datetime import date, timedelta

from rental.rental.utils.account import get_current_rental_account
from rental.rental.utils.date_utils import to_calendar_day
from rental.rental.services.balance_service import (
	get_effective_due_total,
	get_approved_receipt_total,
	get_tenant_balance,
)
from rental.rental.services.archive_service import get_archived_contract_names


# ---------------------------------------------------------------------------
# Dashboard  (source: GET /api/dashboard)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_dashboard():
	"""Aggregate high-level KPIs for the dashboard."""
	account = get_current_rental_account()

	base_filters = {"rental_account": account} if account else {}
	today = frappe.utils.today()
	end_of_day = today  # Frappe dates are already date-only

	# Building/unit counts
	buildings_count = frappe.db.count("Rental Building", base_filters)
	units = frappe.get_all(
		"Rental Unit",
		filters={**base_filters, "is_active": 1},
		fields=["status"],
	)
	units_count = len(units)
	rented = sum(1 for u in units if u.status == "rented")
	empty = sum(1 for u in units if u.status == "empty")
	reserved = sum(1 for u in units if u.status == "reserved")

	occupancy_rate = (rented / units_count * 100) if units_count > 0 else 0

	# Active contracts
	active_contracts = frappe.db.count("Lease Contract", {
		**base_filters,
		"status": "active",
		"start_date": ["<=", today],
		"end_date": [">=", today],
	}) if frappe.db.exists("DocType", "Lease Contract") else 0

	# Financial totals — current outstanding portfolio.
	# Exclude archived contracts: their balance is 0 by definition, and the
	# dashboard KPIs represent the active portfolio, not historical totals.
	due_filters = {"due_date": ["<=", end_of_day]}
	receipt_filters = {"receipt_date": ["<=", end_of_day]}
	if account:
		due_filters["rental_account"] = account
		receipt_filters["rental_account"] = account
	archived_contracts = get_archived_contract_names(account)
	if archived_contracts:
		due_filters["contract"] = ["not in", archived_contracts]
		receipt_filters["contract"] = ["not in", archived_contracts]
	total_dues = get_effective_due_total(due_filters)
	total_receipts = get_approved_receipt_total(receipt_filters)
	total_balance = total_dues - total_receipts

	# Tenants with balance
	tenants = frappe.get_all(
		"Rental Tenant",
		filters={**base_filters, "is_active": 1},
		pluck="name",
	)
	tenants_with_balance = 0
	for t in tenants:
		bal = get_tenant_balance(t)["balance"]
		if bal > 0:
			tenants_with_balance += 1

	stats = {
		"buildingsCount": buildings_count,
		"unitsCount": units_count,
		"rentedUnitsCount": rented,
		"emptyUnitsCount": empty,
		"reservedUnitsCount": reserved,
		"occupancyRate": round(occupancy_rate, 2),
		"activeContractsCount": active_contracts,
		"tenantsCount": len(tenants),
		"totalDues": total_dues,
		"totalReceipts": total_receipts,
		"totalBalance": total_balance,
		"tenantsWithBalanceCount": tenants_with_balance,
	}

	return {"stats": stats}


# ---------------------------------------------------------------------------
# Notifications  (source: GET /api/notifications)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_notifications():
	"""Derive alert list from settings + live data.

	Ported from ``src/app/api/notifications/route.ts``.
	Returns notifications with: id, type, title, message, link, createdAt, priority.
	"""
	account = get_current_rental_account()
	base_filters = {"rental_account": account} if account else {}

	# Get alert days setting (default 30 — matches original)
	from rental.rental.doctype.rental_settings.rental_settings import get_settings_doc
	settings = get_settings_doc(account)
	alert_days = 30
	if settings and settings.contract_alert_days:
		alert_days = int(settings.contract_alert_days)

	today = to_calendar_day(frappe.utils.today())
	alert_date = today + timedelta(days=alert_days)
	week_ahead = today + timedelta(days=7)
	notifications = []

	# --- Expired contracts still marked active (take 10 — matches original) ---
	if frappe.db.exists("DocType", "Lease Contract"):
		expired = frappe.get_all(
			"Lease Contract",
			filters={**base_filters, "status": "active", "end_date": ["<", today], "is_archived": 0},
			fields=["name", "contract_number", "tenant", "building", "unit", "end_date"],
			order_by="end_date asc",
			limit=10,
		)
		for c in expired:
			diff = (today - to_calendar_day(c.end_date)).days
			tenant_name = frappe.db.get_value("Rental Tenant", c.tenant, "full_name") if c.tenant else ""
			building_name = frappe.db.get_value("Rental Building", c.building, "building_name") if c.building else ""
			unit_number = frappe.db.get_value("Rental Unit", c.unit, "unit_number") if c.unit else ""
			notifications.append({
				"id": f"expired-contract-{c.name}",
				"type": "expired_contract",
				"title": "عقد منتهٍ",
				"message": f"عقد {tenant_name} في {building_name} - {unit_number} انتهى منذ {diff} يوم",
				"link": f"/contracts/{c.name}",
				"createdAt": str(c.end_date),
				"priority": "high",
			})

		# --- Nearing expiry contracts (take 20 — matches original) ---
		nearing = frappe.get_all(
			"Lease Contract",
			filters={
				**base_filters,
				"status": "active",
				"start_date": ["<=", today],
				"end_date": [">=", today],
				"end_date": ["<=", alert_date],
				"is_archived": 0,
			},
			fields=["name", "contract_number", "tenant", "building", "unit", "end_date"],
			order_by="end_date asc",
			limit=20,
		)
		for c in nearing:
			diff = (to_calendar_day(c.end_date) - today).days
			tenant_name = frappe.db.get_value("Rental Tenant", c.tenant, "full_name") if c.tenant else ""
			building_name = frappe.db.get_value("Rental Building", c.building, "building_name") if c.building else ""
			unit_number = frappe.db.get_value("Rental Unit", c.unit, "unit_number") if c.unit else ""
			notifications.append({
				"id": f"nearing-contract-{c.name}",
				"type": "nearing_contract",
				"title": "عقد على وشك الانتهاء",
				"message": f"عقد {tenant_name} في {building_name} - {unit_number} ينتهي خلال {diff} يوم",
				"link": f"/contracts/{c.name}",
				"createdAt": str(c.end_date),
				"priority": "high" if diff <= 7 else "medium",
			})

	# --- Upcoming dues within next 7 days (take 20 — matches original) ---
	if frappe.db.exists("DocType", "Rental Due"):
		upcoming_due_filters = {
			**base_filters,
			"docstatus": 1,
			"due_date": [">=", today],
			"due_date": ["<=", week_ahead],
		}
		# Exclude dues of archived contracts from operational notifications.
		archived_for_notif = get_archived_contract_names(account)
		if archived_for_notif:
			upcoming_due_filters["contract"] = ["not in", archived_for_notif]
		upcoming_dues = frappe.get_all(
			"Rental Due",
			filters=upcoming_due_filters,
			fields=["name", "due_number", "tenant", "due_type", "amount", "due_date"],
			order_by="due_date asc",
			limit=20,
		)
		for d in upcoming_dues:
			diff = (to_calendar_day(d.due_date) - today).days
			tenant_name = frappe.db.get_value("Rental Tenant", d.tenant, "full_name") if d.tenant else ""
			due_type_name = frappe.db.get_value("Rental Due Type", d.due_type, "due_type_name") if d.due_type else ""
			notifications.append({
				"id": f"upcoming-due-{d.name}",
				"type": "upcoming_due",
				"title": "استحقاق قادم",
				"message": f"{due_type_name} - {tenant_name} بمبلغ {d.amount} مستحق خلال {diff} يوم",
				"link": "/dues",
				"createdAt": str(d.due_date),
				"priority": "high" if diff <= 1 else "medium",
			})

	# Sort by createdAt ascending, limit 25 — matches original
	notifications.sort(key=lambda n: n.get("createdAt", ""))
	notifications = notifications[:25]

	return {"count": len(notifications), "notifications": notifications}
