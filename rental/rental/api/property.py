"""Property API: buildings, floors, units CRUD + reorder-floors + move + permissions.

Ported from ``src/app/api/buildings/**``, ``src/app/api/floors/**``, ``src/app/api/units/**``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.account import get_current_rental_account, is_system_manager


# ---------------------------------------------------------------------------
# Buildings  (source: GET/POST/PUT/PATCH/DELETE /api/buildings, /api/buildings/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_buildings(search=None, is_active=None, page=1, limit=0, simple=0, include_inactive=0):
	"""List buildings for the current account.

	``simple=1`` returns only name/building_name (for dropdowns).
	``include_inactive=1`` includes inactive buildings (otherwise filtered out).
	"""
	account = get_current_rental_account()
	filters = {}
	if account:
		filters["rental_account"] = account
	if search:
		filters["building_name"] = ["like", f"%{search}%"]
	if is_active is not None:
		filters["is_active"] = is_active
	elif not int(include_inactive):
		filters["is_active"] = 1

	# Simple mode: just name + building_name
	if int(simple):
		buildings = frappe.get_all(
			"Rental Building",
			filters=filters,
			fields=["name", "building_name"],
			order_by="creation desc",
		)
		return buildings

	fields = [
		"name", "building_name", "owner_name", "address",
		"latitude", "longitude", "is_active", "rental_account",
	]

	start = (int(page) - 1) * int(limit) if int(limit) else 0
	buildings = frappe.get_all(
		"Rental Building",
		filters=filters,
		fields=fields,
		order_by="creation desc",
		start=start,
		limit_page_length=int(limit) if int(limit) else None,
	)

	# Enrich with floor and unit counts + balance + unit status counts
	from rental.rental.services.balance_service import get_building_balance

	for b in buildings:
		b["floors_count"] = frappe.db.count("Rental Floor", {"building": b["name"]})
		b["units_count"] = frappe.db.count("Rental Unit", {"building": b["name"]})
		b["rented_units"] = frappe.db.count("Rental Unit", {"building": b["name"], "status": "rented"})
		b["empty_units"] = frappe.db.count("Rental Unit", {"building": b["name"], "status": "empty"})
		b["reserved_units"] = frappe.db.count("Rental Unit", {"building": b["name"], "status": "reserved"})
		balance = get_building_balance(b["name"])
		b["total_dues"] = balance["totalDues"]
		b["total_receipts"] = balance["totalReceipts"]
		b["balance_due"] = balance["balance"]

	total = frappe.db.count("Rental Building", filters)

	return {
		"buildings": buildings,
		"pagination": {
			"page": int(page),
			"pageSize": int(limit) if int(limit) else total,
			"total": total,
			"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
		},
	}


@frappe.whitelist()
def get_building(name):
	"""Get a single building with floors, units, contracts, and tenants.

	Mirrors ``GET /api/buildings/[id]`` in the source app:
	- floors: list with id/name/sortOrder
	- units: list with floor as {id, name} object, contracts array (with tenant)
	- contracts: list with contractNumber, tenant {fullName, phone}, unit {unitNumber}
	- tenants: list with contracts filtered to this building
	- balance: totalDues, totalReceipts, balanceDue
	"""
	building = frappe.get_doc("Rental Building", name)
	building.check_permission("read")

	result = {
		"name": building.name,
		"building_name": building.building_name,
		"owner_name": building.owner_name,
		"address": building.address,
		"latitude": building.latitude,
		"longitude": building.longitude,
		"is_active": building.is_active,
		"rental_account": building.rental_account,
	}

	# Add floors
	floors = frappe.get_all(
		"Rental Floor",
		filters={"building": name},
		fields=["name", "floor_name", "sort_order", "building"],
		order_by="sort_order asc",
	)
	for f in floors:
		f["units_count"] = frappe.db.count("Rental Unit", {"floor": f["name"]})
	result["floors"] = floors

	# Add units with full details + floor object + contracts
	units = frappe.get_all(
		"Rental Unit",
		filters={"building": name},
		fields=["name", "unit_number", "unit_type", "floor", "area", "rooms_count",
				"bathrooms_count", "default_rent", "notes", "is_active",
				"status", "current_electricity_meter_reading", "current_water_meter_reading",
				"electricity_meter_number", "water_meter_number"],
		order_by="unit_number asc",
	)
	for u in units:
		# Floor as object {id, name}
		if u.get("floor"):
			floor_name = frappe.db.get_value("Rental Floor", u["floor"], "floor_name")
			u["floor"] = {"id": u["floor"], "name": floor_name}
		else:
			u["floor"] = None
		# Contracts for this unit (with tenant)
		unit_contracts = frappe.get_all(
			"Lease Contract",
			filters={"unit": u["name"]},
			fields=["name", "contract_number", "start_date", "end_date", "status", "tenant"],
			order_by="start_date desc",
		)
		for c in unit_contracts:
			c["tenant"] = {
				"full_name": frappe.db.get_value("Rental Tenant", c.tenant, "full_name") if c.tenant else "",
				"phone": frappe.db.get_value("Rental Tenant", c.tenant, "phone") if c.tenant else None,
			} if c.tenant else None
		u["contracts"] = unit_contracts
	result["units"] = units

	# Add unit counts
	result["units_count"] = len(units)
	result["rented_units"] = frappe.db.count("Rental Unit", {"building": name, "status": "rented"})
	result["empty_units"] = frappe.db.count("Rental Unit", {"building": name, "status": "empty"})
	result["reserved_units"] = frappe.db.count("Rental Unit", {"building": name, "status": "reserved"})

	# Add contracts (with contract_number, tenant, unit)
	contracts = frappe.get_all(
		"Lease Contract",
		filters={"building": name},
		fields=["name", "contract_number", "tenant", "unit", "start_date", "end_date", "status", "rent_amount"],
		order_by="creation desc",
		limit=100,
	)
	for c in contracts:
		c["tenant_name"] = frappe.db.get_value("Rental Tenant", c.tenant, "full_name") if c.tenant else ""
		c["tenant"] = {
			"full_name": frappe.db.get_value("Rental Tenant", c.tenant, "full_name") if c.tenant else "",
			"phone": frappe.db.get_value("Rental Tenant", c.tenant, "phone") if c.tenant else None,
		} if c.tenant else None
		c["unit"] = {"unit_number": frappe.db.get_value("Rental Unit", c.unit, "unit_number") if c.unit else ""} if c.unit else None
	result["contracts"] = contracts

	# Add tenants (unique tenants from contracts, with their contracts in this building)
	tenant_name_set = set()
	for c in contracts:
		# Get the raw tenant name from the DB (before we overwrote it above)
		raw_tenant = frappe.db.get_value("Lease Contract", c["name"], "tenant")
		if raw_tenant:
			tenant_name_set.add(raw_tenant)

	tenants = []
	for tname in tenant_name_set:
		t = frappe.db.get_value("Rental Tenant", tname, ["name", "full_name", "phone", "email"], as_dict=True)
		if t:
			# All contracts for this tenant in this building
			tenant_contracts = frappe.get_all(
				"Lease Contract",
				filters={"tenant": tname, "building": name},
				fields=["name", "status", "start_date", "end_date", "unit"],
				order_by="start_date desc",
			)
			for tc in tenant_contracts:
				tc["unit"] = {"unit_number": frappe.db.get_value("Rental Unit", tc.unit, "unit_number") if tc.unit else ""} if tc.unit else None
			t["contracts"] = tenant_contracts
			# Find current unit from active contract
			active_contract = frappe.db.get_value(
				"Lease Contract",
				{"tenant": tname, "building": name, "status": "active"},
				["unit", "status"],
				as_dict=True,
			)
			if active_contract and active_contract.unit:
				t["unit_number"] = frappe.db.get_value("Rental Unit", active_contract.unit, "unit_number")
				t["contract_status"] = active_contract.status
			else:
				t["unit_number"] = ""
				t["contract_status"] = ""
			tenants.append(t)
	# Sort tenants by full_name
	tenants.sort(key=lambda x: x.get("full_name", "") or "")
	result["tenants"] = tenants

	# Add building balance
	from rental.rental.services.balance_service import get_building_balance
	balance = get_building_balance(name)
	result["total_dues"] = balance["totalDues"]
	result["total_receipts"] = balance["totalReceipts"]
	result["balance_due"] = balance["balance"]

	return result


@frappe.whitelist()
def create_building(building_name, owner_name=None, address=None, latitude=None, longitude=None, is_active=1):
	account = get_current_rental_account()
	doc = frappe.get_doc({
		"doctype": "Rental Building",
		"rental_account": account,
		"building_name": building_name,
		"owner_name": owner_name,
		"address": address,
		"latitude": latitude,
		"longitude": longitude,
		"is_active": is_active,
	})
	doc.insert(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def update_building(name, is_active=None):
	"""Update building. Only is_active (toggle) is allowed; all other fields are read-only."""
	doc = frappe.get_doc("Rental Building", name)

	if is_active is not None:
		# Toggle active/inactive — validate cascade in doctype
		doc.is_active = is_active
		doc.save(ignore_permissions=is_system_manager())
		return doc.name

	# Any other field change is rejected (matches old app: PUT /api/buildings/[id] → 403)
	frappe.throw(
		frappe._("تعديل بيانات العقار غير مسموح به. يمكنك تعطيل/تفعيل العقار أو حذفه إذا لم يُستخدم."),
		frappe.PermissionError,
	)


@frappe.whitelist()
def toggle_building_active(name, is_active):
	"""Toggle building active/inactive.

	Source: ``PATCH /api/buildings/[id]``.
	Rule: A building can be disabled only if it has no active units.
	"""
	doc = frappe.get_doc("Rental Building", name)
	doc.check_permission("write")

	target = int(is_active)

	if target == 0:
		# Disable: check no active units
		active_units = frappe.db.count("Rental Unit", {"building": name, "is_active": 1})
		if active_units:
			frappe.throw(
				frappe._("لا يمكن تعطيل العقار لأنه يحتوي على وحدات نشطة. قم بتعطيل الوحدات أولًا.")
			)

	doc.is_active = target
	doc.save(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def delete_building(name):
	"""Delete a building. Fails if it has floors, contracts, dues, receipts, or units."""
	building = frappe.get_doc("Rental Building", name)
	building.check_permission("delete")

	# Check for any related data — order matches old app: contracts → dues → receipts → units
	# (floors are caught implicitly by FK restrict if no other data exists)
	contract_count = frappe.db.count("Lease Contract", {"building": name})
	if contract_count:
		frappe.throw(
			frappe._("لا يمكن حذف عقار يحتوي على عقود. يمكنك تعطيله بدلاً من ذلك.")
		)

	# Check no dues
	dues_count = frappe.db.count("Rental Due", {"building": name})
	if dues_count:
		frappe.throw(
			frappe._("لا يمكن حذف عقار يحتوي على مستحقات. يمكنك تعطيله بدلاً من ذلك.")
		)

	# Check no receipts
	receipts_count = frappe.db.count("Rental Receipt", {"building": name})
	if receipts_count:
		frappe.throw(
			frappe._("لا يمكن حذف عقار يحتوي على تحصيلات. يمكنك تعطيله بدلاً من ذلك.")
		)

	# Check no units
	unit_count = frappe.db.count("Rental Unit", {"building": name})
	if unit_count:
		frappe.throw(
			frappe._("لا يمكن حذف عقار يحتوي على وحدات. يمكنك تعطيله بدلاً من ذلك.")
		)

	frappe.delete_doc("Rental Building", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Floors  (source: GET/POST/PUT/DELETE /api/floors, /api/floors/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_floors(building=None, page=1, limit=0):
	"""List floors, optionally filtered by building."""
	account = get_current_rental_account()
	filters = {}
	if account:
		filters["rental_account"] = account
	if building:
		filters["building"] = building

	fields = ["name", "floor_name", "sort_order", "building", "rental_account"]

	start = (int(page) - 1) * int(limit) if int(limit) else 0
	floors = frappe.get_all(
		"Rental Floor",
		filters=filters,
		fields=fields,
		order_by="sort_order asc",
		start=start,
		limit_page_length=int(limit) if int(limit) else None,
	)

	for f in floors:
		f["units_count"] = frappe.db.count("Rental Unit", {"floor": f["name"]})
		if f.get("building"):
			f["building_name"] = frappe.db.get_value("Rental Building", f["building"], "building_name")

	total = frappe.db.count("Rental Floor", filters)

	return {
		"floors": floors,
		"pagination": {
			"page": int(page),
			"pageSize": int(limit) if int(limit) else total,
			"total": total,
			"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
		},
	}


@frappe.whitelist()
def get_floor(name):
	"""Get a single floor with its units."""
	floor = frappe.get_doc("Rental Floor", name)
	floor.check_permission("read")

	result = floor.as_dict()

	units = frappe.get_all(
		"Rental Unit",
		filters={"floor": name},
		fields=["name", "unit_number", "unit_type", "area", "rooms_count",
				"bathrooms_count", "default_rent", "is_active", "status"],
		order_by="unit_number asc",
	)
	result["units"] = units
	return result


@frappe.whitelist()
def create_floor(building, floor_name, sort_order=0):
	account = frappe.db.get_value("Rental Building", building, "rental_account")
	if not account:
		account = get_current_rental_account()
	doc = frappe.get_doc({
		"doctype": "Rental Floor",
		"rental_account": account,
		"building": building,
		"floor_name": floor_name,
		"sort_order": sort_order,
	})
	doc.insert(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def update_floor(name, sort_order=None):
	"""Update floor. Always rejected (matches old app: PUT /api/floors/[id] → 403 always)."""
	frappe.throw(
		frappe._("تعديل بيانات الطابق غير مسموح به. يمكنك حذف الطابق إذا لم يُستخدم."),
		frappe.PermissionError,
	)


@frappe.whitelist()
def delete_floor(name):
	"""Delete a floor. Fails if it has rented units, contracts, or any units (order matches old app)."""
	floor = frappe.get_doc("Rental Floor", name)
	floor.check_permission("delete")

	# 1. Rented units on this floor
	rented_units = frappe.db.count("Rental Unit", {"floor": name, "status": "rented"})
	if rented_units:
		frappe.throw(frappe._("لا يمكن حذف طابق يحتوي على وحدات مؤجرة"))

	# 2. Contracts on units in this floor
	if frappe.db.exists("DocType", "Lease Contract"):
		contract_count = frappe.db.count("Lease Contract", {"floor": name})
		if not contract_count:
			unit_names = frappe.get_all("Rental Unit", {"floor": name}, pluck="name")
			if unit_names:
				contract_count = frappe.db.count(
					"Lease Contract", {"unit": ["in", unit_names]}
				)
		if contract_count:
			frappe.throw(frappe._("لا يمكن حذف طابق يحتوي على وحدات مؤجرة"))

	# 3. Any units on this floor
	any_units = frappe.db.count("Rental Unit", {"floor": name})
	if any_units:
		frappe.throw(frappe._("لا يمكن حذف طابق يحتوي على وحدات"))

	frappe.delete_doc("Rental Floor", name, ignore_permissions=is_system_manager())
	return {"success": True}


# ---------------------------------------------------------------------------
# Reorder floors  (source: POST /api/buildings/[id]/reorder-floors)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def reorder_floors(building, floor_ids=None, floor_order=None):
	"""Reorder floors in a building by updating sort_order.

	Source: ``POST /api/buildings/[id]/reorder-floors`` (reorder-floors/route.ts:1-30).
	Accepts a list of floor names; sets sort_order to the 0-based index.

	Accepts either ``floor_ids`` or ``floor_order`` parameter (both are lists
	of floor names in the desired order).
	"""
	raw = floor_ids if floor_ids is not None else floor_order
	if raw is None:
		frappe.throw(frappe._("قائمة الطوابق مطلوبة"))

	if isinstance(raw, str):
		import json
		raw = json.loads(raw)

	for index, floor_name in enumerate(raw):
		# Validate floor belongs to building
		floor_building = frappe.db.get_value("Rental Floor", floor_name, "building")
		if floor_building != building:
			frappe.throw(frappe._("Floor {0} does not belong to building {1}").format(floor_name, building))
		frappe.db.set_value("Rental Floor", floor_name, "sort_order", index, update_modified=False)

	return {"success": True}


# ---------------------------------------------------------------------------
# Move unit  (source: POST /api/units/[id]/move)
# ---------------------------------------------------------------------------


@frappe.whitelist()
def move_unit(name=None, target_floor=None, unit=None):
	"""Move a unit to a different floor within the same building.

	Source: ``POST /api/units/[id]/move`` (units/[id]/move/route.ts:1-63).
	- Requires target_floor (floorId).
	- Blocks if unit has an active contract (status=active, within date range).
	- No-op if target floor is the same as current.
	- Blocks if unit has ANY contract history.
	- Blocks if target floor is in a different building.

	Accepts either ``name`` or ``unit`` parameter (both refer to the unit name).
	"""
	unit_name = name if name is not None else unit
	if not unit_name:
		frappe.throw(frappe._("معرف الطابق مطلوب"))

	if not target_floor:
		frappe.throw(frappe._("معرف الطابق مطلوب"))

	unit_doc = frappe.get_doc("Rental Unit", unit_name)
	unit_doc.check_permission("write")

	# Block if unit has an active contract (status=active, within date range)
	from datetime import date
	today = date.today()
	active_contract = frappe.db.exists(
		"Lease Contract",
		{
			"unit": unit_name,
			"status": "active",
			"start_date": ["<=", today],
			"end_date": [">=", today],
		},
	)
	if active_contract:
		frappe.throw(frappe._("لا يمكن نقل الوحدة لأنها تحتوي على عقد نشط"))

	# No-op if target floor is the same
	if unit_doc.floor == target_floor:
		return {"success": True}

	# Block if unit has ANY contract history
	any_contract = frappe.db.exists("Lease Contract", {"unit": unit_name})
	if any_contract:
		frappe.throw(frappe._("لا يمكن نقل وحدة لها سجل عقود"))

	# Validate target floor exists
	target_building = frappe.db.get_value("Rental Floor", target_floor, "building")
	if not target_building:
		frappe.throw(frappe._("الطابق غير موجود"))

	if target_building != unit_doc.building:
		frappe.throw(frappe._("لا يمكن نقل الوحدة إلى عقار مختلف"))

	frappe.db.set_value("Rental Unit", unit_name, "floor", target_floor, update_modified=False)
	return {"success": True}


# ---------------------------------------------------------------------------
# Units  (source: GET/POST/PUT/PATCH/DELETE /api/units, /api/units/[id])
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_units(building=None, floor=None, status=None, unit_type=None, search=None,
			  is_active=None, page=1, limit=0, available_only=0, simple=0, include_inactive=0):
	"""List units with filters.

	``simple=1`` returns only name/unit_number (for dropdowns).
	``include_inactive=1`` includes inactive units (otherwise filtered out).
	"""
	account = get_current_rental_account()
	filters = {}
	if account:
		filters["rental_account"] = account
	if building:
		filters["building"] = building
	if floor:
		filters["floor"] = floor
	if status:
		filters["status"] = status
	if unit_type:
		filters["unit_type"] = unit_type
	if is_active is not None:
		filters["is_active"] = is_active
	elif not int(include_inactive):
		filters["is_active"] = 1
	if search:
		filters["unit_number"] = ["like", f"%{search}%"]
	if int(available_only):
		filters["status"] = "available"

	# C15: simple mode returns only id and name (legacy units/route.ts:20-26).
	if int(simple):
		units = frappe.get_all(
			"Rental Unit",
			filters=filters,
			fields=["name", "unit_number"],
			order_by="unit_number asc",
		)
		return {"units": units}

	fields = [
		"name", "unit_number", "building", "floor", "unit_type",
		"area", "rooms_count", "bathrooms_count", "default_rent",
		"electricity_meter_number", "water_meter_number",
		"current_electricity_meter_reading", "current_water_meter_reading",
		"notes", "is_active", "status",
		"rental_account",
	]

	start = (int(page) - 1) * int(limit) if int(limit) else 0
	units = frappe.get_all(
		"Rental Unit",
		filters=filters,
		fields=fields,
		# C14: legacy orders by unitNumber asc (units/route.ts:67).
		order_by="unit_number asc",
		start=start,
		limit_page_length=int(limit) if int(limit) else None,
	)

	# Enrich
	for u in units:
		if u.get("building"):
			u["building_name"] = frappe.db.get_value("Rental Building", u["building"], "building_name")
		if u.get("floor"):
			u["floor_name"] = frappe.db.get_value("Rental Floor", u["floor"], "floor_name")
		# Active contract info
		active_contract = frappe.db.get_value(
			"Lease Contract",
			{"unit": u["name"], "status": "active"},
			["name", "tenant", "start_date", "end_date"],
			as_dict=True,
		)
		if active_contract:
			u["active_contract"] = active_contract
			u["tenant_name"] = frappe.db.get_value("Rental Tenant", active_contract.tenant, "full_name")
		else:
			u["active_contract"] = None

	total = frappe.db.count("Rental Unit", filters)

	return {
		"units": units,
		"pagination": {
			"page": int(page),
			"pageSize": int(limit) if int(limit) else total,
			"total": total,
			"totalPages": (total + int(limit) - 1) // int(limit) if int(limit) else 1,
		},
	}


@frappe.whitelist()
def get_unit(name):
	"""Get a single unit with contracts, active contract, and permissions.

	Mirrors ``GET /api/units/[id]`` in the source app:
	- contracts: full history with tenant {id, fullName}
	- permissions: editableFields, canEdit, canDisable, canDelete, canReactivate
	"""
	unit = frappe.get_doc("Rental Unit", name)
	unit.check_permission("read")

	result = {
		"name": unit.name,
		"unit_number": unit.unit_number,
		"unit_type": unit.unit_type,
		"building": unit.building,
		"floor": unit.floor,
		"area": unit.area,
		"rooms_count": unit.rooms_count,
		"bathrooms_count": unit.bathrooms_count,
		"default_rent": unit.default_rent,
		"electricity_meter_number": unit.electricity_meter_number,
		"water_meter_number": unit.water_meter_number,
		"current_electricity_meter_reading": unit.current_electricity_meter_reading,
		"current_water_meter_reading": unit.current_water_meter_reading,
		"status": unit.status,
		"notes": unit.notes,
		"is_active": unit.is_active,
	}

	# Building object
	if result.get("building"):
		result["building"] = {
			"id": unit.building,
			"name": frappe.db.get_value("Rental Building", unit.building, "building_name"),
		}
	# Floor object
	if result.get("floor"):
		result["floor"] = {
			"id": unit.floor,
			"name": frappe.db.get_value("Rental Floor", unit.floor, "floor_name"),
		}

	# All contracts for this unit (with tenant)
	contracts = frappe.get_all(
		"Lease Contract",
		filters={"unit": name},
		fields=["name", "contract_number", "start_date", "end_date", "status", "tenant"],
		order_by="start_date desc",
	)
	for c in contracts:
		c["tenant"] = {
			"id": c.tenant,
			"full_name": frappe.db.get_value("Rental Tenant", c.tenant, "full_name") if c.tenant else "",
		} if c.tenant else None
	result["contracts"] = contracts

	# Active contract (current or upcoming)
	active_contract = frappe.db.get_value(
		"Lease Contract",
		{"unit": name, "status": ["in", ["active", "draft"]]},
		["name", "tenant", "start_date", "end_date", "rent_amount", "status"],
		as_dict=True,
	)
	if active_contract:
		active_contract["tenant_name"] = frappe.db.get_value(
			"Rental Tenant", active_contract.tenant, "full_name"
		)
	result["active_contract"] = active_contract

	# Add permissions (matches old app: GET /api/units/[id] embeds permissions)
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions
	result["permissions"] = get_unit_action_permissions(name)

	return result


@frappe.whitelist()
def create_unit(building, unit_number, floor=None, unit_type=None, area=None, rooms_count=None,
				bathrooms_count=None, default_rent=None, notes=None, is_active=1,
				electricity_meter_number=None, water_meter_number=None,
				current_electricity_meter_reading=None, current_water_meter_reading=None):
	account = frappe.db.get_value("Rental Building", building, "rental_account")
	if not account:
		account = get_current_rental_account()
	doc = frappe.get_doc({
		"doctype": "Rental Unit",
		"rental_account": account,
		"building": building,
		"floor": floor or None,
		"unit_number": unit_number,
		"unit_type": unit_type,
		"area": area,
		"rooms_count": rooms_count,
		"bathrooms_count": bathrooms_count,
		"default_rent": default_rent,
		"electricity_meter_number": electricity_meter_number,
		"water_meter_number": water_meter_number,
		"current_electricity_meter_reading": current_electricity_meter_reading,
		"current_water_meter_reading": current_water_meter_reading,
		"notes": notes,
		"is_active": is_active,
	})
	doc.insert(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def update_unit(name, **kwargs):
	"""Update a unit. Enforces editableFields rules (matches old app)."""
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions, get_editable_fields

	doc = frappe.get_doc("Rental Unit", name)
	permissions = get_unit_action_permissions(name)
	editable_fields = get_editable_fields(name)

	# Always-editable descriptive fields
	always_editable = ["unit_type", "area", "rooms_count", "bathrooms_count", "notes"]

	# Identity fields (only editable when no contracts)
	identity_fields = ["unit_number", "building", "floor"]

	# Meter reading fields (blocked when active metered contract exists)
	meter_reading_fields = ["current_electricity_meter_reading", "current_water_meter_reading"]

	# Meter number fields (always editable — stored but not shown in UI per spec)
	meter_number_fields = ["electricity_meter_number", "water_meter_number"]

	for field in kwargs:
		if kwargs[field] is None:
			continue
		val = kwargs[field]
		if field == "floor" and (val == "" or val == "null"):
			val = None

		if field in always_editable or field in meter_number_fields:
			doc.set(field, val)
		elif field in identity_fields:
			if field not in editable_fields:
				if field == "unit_number":
					msg = frappe._("لا يمكن تغيير رقم الوحدة لأنها تحتوي على سجل عقود")
				elif field == "floor":
					msg = frappe._("لا يمكن تغيير الطابق لأن الوحدة تحتوي على سجل عقود")
				elif field == "building":
					msg = frappe._("لا يمكن تغيير العقار لأن الوحدة تحتوي على سجل عقود")
				else:
					msg = frappe._("لا يمكن تغيير '{0}' — الوحدة لها سجل عقود.").format(field)
				frappe.throw(msg, frappe.PermissionError)
			doc.set(field, val)
		elif field in meter_reading_fields:
			if field not in editable_fields:
				if field == "current_electricity_meter_reading":
					msg = frappe._("لا يمكن تعديل قراءة عداد الكهرباء لوجود عقد مترى نشط على الوحدة")
				elif field == "current_water_meter_reading":
					msg = frappe._("لا يمكن تعديل قراءة عداد المياه لوجود عقد مترى نشط على الوحدة")
				else:
					msg = frappe._("لا يمكن تغيير قراءة العداد — الوحدة لها عقد نشط بعداد.")
				frappe.throw(msg, frappe.PermissionError)
			doc.set(field, val)
		elif field in ["is_active", "is_manually_unavailable"]:
			doc.set(field, val)
		# status is NOT editable via API (derived from contracts)

	doc.save(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def toggle_unit_active(name, is_active):
	"""Toggle unit active/inactive.

	Source: ``PATCH /api/units/[id]``.
	Rules:
	- Disable: unit must be active, and no current/upcoming/expired-un-evicted/cancelled-after-start occupancy.
	- Reactivate: unit must be inactive and its building must be active.
	"""
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions

	doc = frappe.get_doc("Rental Unit", name)
	doc.check_permission("write")

	permissions = get_unit_action_permissions(name)
	target = int(is_active)

	if target == 0:
		# Disable
		if not permissions.get("can_disable"):
			reason = permissions.get("reasons", {}).get("disable") or "لا يمكن تعطيل الوحدة"
			frappe.throw(frappe._(reason), frappe.PermissionError)
	else:
		# Reactivate
		if not permissions.get("can_reactivate"):
			reason = permissions.get("reasons", {}).get("reactivate") or "لا يمكن تفعيل الوحدة"
			frappe.throw(frappe._(reason), frappe.PermissionError)

	doc.is_active = target
	doc.save(ignore_permissions=is_system_manager())
	return doc.name


@frappe.whitelist()
def delete_unit(name):
	"""Delete a unit. Fails if it has any contracts, dues, receipts, or evictions."""
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions

	unit = frappe.get_doc("Rental Unit", name)
	unit.check_permission("delete")

	permissions = get_unit_action_permissions(name)
	if not permissions.get("can_delete"):
		frappe.throw(
			frappe._("لا يمكن حذف وحدة تحتوي على سجلات استخدام (عقود، إخلاء، مستحقات، أو تحصيلات)"),
			frappe.PermissionError,
		)

	frappe.delete_doc("Rental Unit", name, ignore_permissions=is_system_manager())
	return {"success": True}


@frappe.whitelist()
def get_unit_permissions(name):
	"""Get unit permissions for the current user.

	Source: ``GET /api/units/:id/permissions``.
	"""
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions

	unit = frappe.get_doc("Rental Unit", name)
	unit.check_permission("read")

	return get_unit_action_permissions(name)
