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
def get_buildings(page=1, limit=0, simple=0, include_inactive=0):
	"""List buildings for the current account.

	``simple=1`` returns only name/building_name (for dropdowns).
	``include_inactive=1`` includes inactive buildings (otherwise filtered out).

	Source: ``GET /api/buildings``.
	"""
	account = get_current_rental_account()
	filters = {}
	if account:
		filters["rental_account"] = account
	if not int(include_inactive):
		filters["is_active"] = 1

	# Simple mode: just name + building_name (source: select { id, name } orderBy name asc)
	if int(simple):
		buildings = frappe.get_all(
			"Rental Building",
			filters=filters,
			fields=["name", "building_name"],
			order_by="building_name asc",
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
	# Source: units filter { isActive: true } — only active units are counted
	from rental.rental.services.balance_service import get_building_balance

	for b in buildings:
		b["floors_count"] = frappe.db.count("Rental Floor", {"building": b["name"]})
		b["units_count"] = frappe.db.count("Rental Unit", {"building": b["name"], "is_active": 1})
		b["rented_units"] = frappe.db.count("Rental Unit", {"building": b["name"], "is_active": 1, "status": "rented"})
		b["empty_units"] = frappe.db.count("Rental Unit", {"building": b["name"], "is_active": 1, "status": "empty"})
		b["reserved_units"] = frappe.db.count("Rental Unit", {"building": b["name"], "is_active": 1, "status": "reserved"})
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
		# Unit type display name
		if u.get("unit_type"):
			u["unit_type_name"] = frappe.db.get_value("Unit Type", u["unit_type"], "type_name") or ""
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

	# Add floors_count (source: Building model includes floorsCount field)
	result["floors_count"] = len(floors)
	# units_count from the building model (source: Building model includes unitsCount field)
	result["units_count"] = len(units)

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
def create_building(building_name, owner_name=None, address=None, latitude=None, longitude=None,
					floors_count=None, units_count=None, is_active=1):
	"""Create a building.

	Source: ``POST /api/buildings`` — passes floorsCount/unitsCount from schema (optional).
	"""
	account = get_current_rental_account()
	doc = frappe.get_doc({
		"doctype": "Rental Building",
		"rental_account": account,
		"building_name": building_name,
		"owner_name": owner_name,
		"address": address,
		"latitude": latitude,
		"longitude": longitude,
		"floors_count": int(floors_count) if floors_count is not None else 0,
		"units_count": int(units_count) if units_count is not None else 0,
		"is_active": int(is_active),
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
	"""List floors, optionally filtered by building.

	Source: ``GET /api/floors`` — includes building { name }, orderBy sortOrder asc.
	"""
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

	# Source: include: { building: { select: { name: true } } }
	# Frappe adaptation: keep building as link ID + add building_name for display
	for f in floors:
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
	"""Get a single floor with its units.

	Source: ``GET /api/floors/[id]`` — includes building { name } and units (all fields).
	"""
	floor = frappe.get_doc("Rental Floor", name)
	floor.check_permission("read")

	result = floor.as_dict()
	# Frappe adaptation: add building_name (source: building: { select: { name: true } })
	if result.get("building"):
		result["building_name"] = frappe.db.get_value("Rental Building", result["building"], "building_name")

	# Source: units: { orderBy: { unitNumber: 'asc' } } — no select, returns all fields
	units = frappe.get_all(
		"Rental Unit",
		filters={"floor": name},
		fields=["*"],
		order_by="unit_number asc",
	)
	# Enrich units with unit_type_name for display
	for u in units:
		if u.get("unit_type"):
			u["unit_type_name"] = frappe.db.get_value("Unit Type", u["unit_type"], "type_name") or ""
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
		"sort_order": int(sort_order) if sort_order is not None else 0,
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

	# 2. Contracts on units in this floor (source: leaseContract.count where unit.floorId == id)
	if frappe.db.exists("DocType", "Lease Contract"):
		unit_names = frappe.get_all("Rental Unit", {"floor": name}, pluck="name")
		contract_count = 0
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
	# Source: !Array.isArray(floorIds) || floorIds.length === 0
	if raw is None:
		frappe.throw(frappe._("قائمة الطوابق مطلوبة"))

	if isinstance(raw, str):
		import json
		raw = json.loads(raw)

	if not isinstance(raw, (list, tuple)) or len(raw) == 0:
		frappe.throw(frappe._("قائمة الطوابق مطلوبة"))

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
	from rental.rental.utils.date_utils import to_calendar_day
	today = to_calendar_day(frappe.utils.today())
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


def _batch_get_meter_capabilities(unit_names):
	"""Batch-load meter capability flags for a list of units.

	Returns ``{ unit_name: { "electricity_meter": bool, "water_meter": bool } }``.
	Uses a single query joining Unit Attribute Value with Unit Attribute to
	avoid N+1 queries when listing units.
	"""
	if not unit_names:
		return {}

	# Fetch all Check-type attribute values for these units that have a
	# capability_code set, in a single query.
	rows = frappe.db.sql(
		"""
		SELECT uav.unit, ua.capability_code, uav.value_check
		FROM `tabUnit Attribute Value` uav
		INNER JOIN `tabUnit Attribute` ua ON ua.name = uav.attribute
		WHERE uav.unit IN %(units)s
		  AND ua.data_type = 'Check'
		  AND ua.capability_code IN ('electricity_meter', 'water_meter')
		""",
		{"units": tuple(unit_names)},
		as_dict=True,
	)

	result = {name: {} for name in unit_names}
	for row in rows:
		result.setdefault(row.unit, {})[row.capability_code] = bool(row.value_check)
	return result


@frappe.whitelist()
def get_units(building=None, floor=None, status=None, tenant=None,
			  page=1, limit=0, simple=0, include_inactive=0):
	"""List units with filters.

	``simple=1`` returns only name/unit_number (for dropdowns).
	``include_inactive=1`` includes inactive units (otherwise filtered out).

	Source: ``GET /api/units``.
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
	if not int(include_inactive):
		filters["is_active"] = 1
	# tenant filter: units with active contract for this tenant (source: units/route.ts:27-36)
	if tenant:
		from rental.rental.utils.date_utils import to_calendar_day
		today = to_calendar_day(frappe.utils.today())
		tenant_unit_names = frappe.get_all(
			"Lease Contract",
			filters={
				"tenant": tenant,
				"status": "active",
				"start_date": ["<=", today],
				"end_date": [">=", today],
			},
			pluck="unit",
		)
		if tenant_unit_names:
			filters["name"] = ["in", tenant_unit_names]
		else:
			# No matching units for this tenant
			return {"units": []}

	# Simple mode: just name + unit_number (for dropdowns)
	if int(simple):
		units = frappe.get_all(
			"Rental Unit",
			filters=filters,
			fields=["name", "unit_number"],
			order_by="unit_number asc",
		)
		return {"units": units}

	# Source: units/route.ts:40-66 select fields
	fields = [
		"name", "unit_number", "building", "floor", "unit_type",
		"area", "default_rent",
		"electricity_meter_number", "water_meter_number",
		"current_electricity_meter_reading", "current_water_meter_reading",
		"is_active", "status",
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

	# Enrich — source: units/route.ts:38-68
	# building: { select: { name: true } }, floor: { select: { name: true } }
	# contracts: { where: active + date range, take: 1, include tenant fullName }
	from rental.rental.utils.date_utils import to_calendar_day
	today = to_calendar_day(frappe.utils.today())

	# Batch-load meter capabilities for all units in the result set.
	# Returns { unit_name: { "electricity_meter": bool, "water_meter": bool } }
	meter_caps = _batch_get_meter_capabilities([u["name"] for u in units])

	for u in units:
		if u.get("building"):
			u["building_name"] = frappe.db.get_value("Rental Building", u["building"], "building_name")
		if u.get("floor"):
			u["floor_name"] = frappe.db.get_value("Rental Floor", u["floor"], "floor_name")
		if u.get("unit_type"):
			u["unit_type_name"] = frappe.db.get_value("Unit Type", u["unit_type"], "type_name")
		# Meter capabilities from Unit Attribute Values
		caps = meter_caps.get(u["name"], {})
		u["electricity_meter"] = caps.get("electricity_meter", False)
		u["water_meter"] = caps.get("water_meter", False)
		# Current active contracts (filtered by date range, take 1)
		active_contracts = frappe.get_all(
			"Lease Contract",
			filters={
				"unit": u["name"],
				"status": "active",
				"start_date": ["<=", today],
				"end_date": [">=", today],
			},
			fields=["name", "start_date", "end_date", "status", "tenant"],
			order_by="start_date desc",
			limit=1,
		)
		for c in active_contracts:
			c["tenant"] = {"full_name": frappe.db.get_value("Rental Tenant", c["tenant"], "full_name") if c["tenant"] else None}
		u["contracts"] = active_contracts

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
	"""Get a single unit with contracts and permissions.

	Mirrors ``GET /api/units/[id]`` in the source app:
	- contracts: full history with tenant {id, fullName}
	- permissions: editableFields, canEdit, canDisable, canDelete, canReactivate
	"""
	unit = frappe.get_doc("Rental Unit", name)
	unit.check_permission("read")

	# Source: units/[id]/route.ts:13-40 select fields
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

	# Building object — source: building: { select: { id: true, name: true } }
	if result.get("building"):
		result["building"] = {
			"id": unit.building,
			"name": frappe.db.get_value("Rental Building", unit.building, "building_name"),
		}
	# Floor object — source: floor: { select: { name: true } } (no id)
	if result.get("floor"):
		result["floor"] = {
			"name": frappe.db.get_value("Rental Floor", unit.floor, "floor_name"),
		}

	# All contracts for this unit (with tenant) — source: contracts include tenant {id, fullName}
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

	# Add permissions (matches old app: GET /api/units/[id] embeds permissions)
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions
	result["permissions"] = get_unit_action_permissions(name)

	# Add unit type name for display
	if result.get("unit_type"):
		result["unit_type_name"] = frappe.db.get_value("Unit Type", result["unit_type"], "type_name")

	# Add dynamic attribute values
	attr_values = get_unit_attribute_values(name)
	result["attribute_values"] = attr_values["values"]

	# Add meter capability flags for convenience (used by contract charges UI)
	caps = _batch_get_meter_capabilities([name])
	result["electricity_meter"] = caps.get(name, {}).get("electricity_meter", False)
	result["water_meter"] = caps.get(name, {}).get("water_meter", False)

	# Add the unit type's assigned attributes (for rendering)
	if result.get("unit_type"):
		type_attrs = get_unit_type_attributes_for_unit(result["unit_type"])
		result["type_attributes"] = type_attrs["attributes"]
	else:
		result["type_attributes"] = []

	return result


@frappe.whitelist()
def create_unit(building, unit_number, floor=None, unit_type=None, area=None, rooms_count=None,
				bathrooms_count=None, default_rent=None, notes=None, is_active=1,
				current_electricity_meter_reading=None, current_water_meter_reading=None,
				electricity_meter_number=None, water_meter_number=None,
				attribute_values=None):
	"""Create a unit.

	Source: ``POST /api/units`` — unitSchema fields only (no meter numbers).
	Extended: accepts attribute_values (JSON) for dynamic Unit Attribute Values.
	"""
	import json

	account = frappe.db.get_value("Rental Building", building, "rental_account")
	if not account:
		account = get_current_rental_account()

	# Parse attribute_values if provided
	attr_values = {}
	if attribute_values:
		if isinstance(attribute_values, str):
			attr_values = json.loads(attribute_values)
		else:
			attr_values = attribute_values

	# Validate required attributes for the selected unit type
	if unit_type:
		_validate_required_attributes(unit_type, attr_values)

	doc = frappe.get_doc({
		"doctype": "Rental Unit",
		"rental_account": account,
		"building": building,
		"floor": floor or None,
		"unit_number": unit_number,
		"unit_type": unit_type,
		"area": float(area) if area else None,
		"rooms_count": int(rooms_count) if rooms_count is not None else None,
		"bathrooms_count": int(bathrooms_count) if bathrooms_count is not None else None,
		"default_rent": float(default_rent) if default_rent else None,
		"electricity_meter_number": electricity_meter_number or None,
		"water_meter_number": water_meter_number or None,
		"current_electricity_meter_reading": current_electricity_meter_reading,
		"current_water_meter_reading": current_water_meter_reading,
		"notes": notes,
		"is_active": int(is_active),
	})
	doc.insert(ignore_permissions=is_system_manager())

	# Save dynamic attribute values
	if attr_values:
		save_unit_attribute_values(doc.name, attr_values)

	return doc.name


@frappe.whitelist()
def update_unit(name, **kwargs):
	"""Update a unit. Enforces editableFields rules.

	Source: ``PUT /api/units/[id]``.
	Order of checks (must match original):
	  1. Get existing unit (404 if not found — handled by get_doc)
	  2. Get permissions
	  3. Check canEdit (403 if false — always true in practice)
	  4. unitNumber changed && !editableFields → 409
	  5. floor changed && !editableFields → 409
	  6. building changed && !editableFields → 409
	  7. currentElectricityMeterReading present && !editableFields → 409
	  8. currentWaterMeterReading present && !editableFields → 409
	  9. Build updateData and save

	Updatable fields (source: units/[id]/route.ts:103-114):
	  unitNumber, unitType, floorId, buildingId, area, roomsCount,
	  bathroomsCount, defaultRent, currentElectricityMeterReading,
	  currentWaterMeterReading, notes
	"""
	from rental.rental.services.unit_permissions_service import get_unit_action_permissions

	doc = frappe.get_doc("Rental Unit", name)
	doc.check_permission("write")

	permissions = get_unit_action_permissions(name)
	editable_fields = permissions.get("editable_fields", [])

	# 3. canEdit check (always true in the original, but kept for parity)
	if not permissions.get("can_edit"):
		reason = permissions.get("reasons", {}).get("edit") or "لا يمكن تعديل الوحدة"
		frappe.throw(frappe._(reason), frappe.PermissionError)

	# Map incoming kwargs (snake_case) to the original field checks
	# Original editableFields uses camelCase; Python uses snake_case
	# editable_fields from the service are already snake_case
	existing_unit_number = doc.unit_number
	existing_floor = doc.floor
	existing_building = doc.building

	unit_number_changed = kwargs.get("unit_number") is not None and kwargs.get("unit_number") != existing_unit_number
	floor_changed = "floor" in kwargs and kwargs.get("floor") != existing_floor
	building_changed = kwargs.get("building") is not None and kwargs.get("building") != existing_building

	# 4. unitNumber check
	if unit_number_changed and "unit_number" not in editable_fields:
		frappe.throw(frappe._("لا يمكن تغيير رقم الوحدة لأنها تحتوي على سجل عقود"), frappe.PermissionError)
	# 5. floor check
	if floor_changed and "floor" not in editable_fields:
		frappe.throw(frappe._("لا يمكن تغيير الطابق لأن الوحدة تحتوي على سجل عقود"), frappe.PermissionError)
	# 6. building check
	if building_changed and "building" not in editable_fields:
		frappe.throw(frappe._("لا يمكن تغيير العقار لأن الوحدة تحتوي على سجل عقود"), frappe.PermissionError)
	# 7. electricity meter reading check
	if kwargs.get("current_electricity_meter_reading") is not None and "current_electricity_meter_reading" not in editable_fields:
		frappe.throw(frappe._("لا يمكن تعديل قراءة عداد الكهرباء لوجود عقد مترى نشط على الوحدة"), frappe.PermissionError)
	# 8. water meter reading check
	if kwargs.get("current_water_meter_reading") is not None and "current_water_meter_reading" not in editable_fields:
		frappe.throw(frappe._("لا يمكن تعديل قراءة عداد المياه لوجود عقد مترى نشط على الوحدة"), frappe.PermissionError)

	# 9. Build updateData and save — only the fields in the original updateData
	if kwargs.get("unit_number") is not None:
		doc.unit_number = kwargs["unit_number"]
	if kwargs.get("unit_type") is not None:
		doc.unit_type = kwargs["unit_type"]
	if "floor" in kwargs:
		floor_val = kwargs["floor"]
		if floor_val == "" or floor_val == "null":
			floor_val = None
		doc.floor = floor_val
	if kwargs.get("building") is not None:
		doc.building = kwargs["building"]
	if kwargs.get("area") is not None:
		doc.area = float(kwargs["area"]) if kwargs["area"] else None
	if kwargs.get("rooms_count") is not None:
		doc.rooms_count = kwargs["rooms_count"]
	if kwargs.get("bathrooms_count") is not None:
		doc.bathrooms_count = kwargs["bathrooms_count"]
	if kwargs.get("default_rent") is not None:
		doc.default_rent = float(kwargs["default_rent"]) if kwargs["default_rent"] else None
	if kwargs.get("current_electricity_meter_reading") is not None:
		doc.current_electricity_meter_reading = kwargs["current_electricity_meter_reading"]
	if kwargs.get("current_water_meter_reading") is not None:
		doc.current_water_meter_reading = kwargs["current_water_meter_reading"]
	if kwargs.get("electricity_meter_number") is not None:
		doc.electricity_meter_number = kwargs["electricity_meter_number"] or None
	if kwargs.get("water_meter_number") is not None:
		doc.water_meter_number = kwargs["water_meter_number"] or None
	if kwargs.get("notes") is not None:
		doc.notes = kwargs["notes"]

	doc.save(ignore_permissions=is_system_manager())

	# Save dynamic attribute values (if provided)
	if kwargs.get("attribute_values"):
		save_unit_attribute_values(name, kwargs["attribute_values"])

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

	# Source: units/[id]/route.ts:146-158 — reactivate check first, then disable
	if target == 1:
		# Reactivate
		if not permissions.get("can_reactivate"):
			reason = permissions.get("reasons", {}).get("reactivate") or "لا يمكن تفعيل الوحدة"
			frappe.throw(frappe._(reason), frappe.PermissionError)
	else:
		# Disable
		if not permissions.get("can_disable"):
			reason = permissions.get("reasons", {}).get("disable") or "لا يمكن تعطيل الوحدة"
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


# ---------------------------------------------------------------------------
# Unit Type dropdown + Dynamic Unit Attribute Values
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_active_unit_types():
	"""Return active unit types for the current account (for dropdowns).

	Includes system types and the account's custom types.
	For edit forms, the unit's current type (even if disabled) should be
	included by the caller separately.
	"""
	from rental.rental.services.unit_type_service import ensure_system_unit_types
	ensure_system_unit_types()

	account = get_current_rental_account()
	or_filters = {}
	if account:
		or_filters = {"rental_account": account, "is_system": 1}

	types = frappe.get_all(
		"Unit Type",
		filters={"is_active": 1},
		or_filters=or_filters if or_filters else None,
		fields=["name", "type_name", "code", "is_system", "display_order"],
		order_by="is_system desc, display_order asc, type_name asc",
	)
	return {"unitTypes": types}


@frappe.whitelist()
def get_unit_type_attributes_for_unit(unit_type):
	"""Get active assigned attributes for a unit type, ordered by display_order.

	Returns attribute metadata needed by the frontend to render dynamic fields.
	Merged with User Unit Preference overrides if they exist.
	"""
	from rental.rental.api.unit_settings import _merge_attribute_override

	type_doc = frappe.get_doc("Unit Type", unit_type)
	result = []
	for row in type_doc.attributes:
		merged = _merge_attribute_override(unit_type, row.attribute, {
			"is_required": row.is_required,
			"is_active": row.is_active,
			"display_order": row.display_order,
		})
		if not merged["is_active"]:
			continue
		attr = frappe.db.get_value(
			"Unit Attribute", row.attribute,
			["name", "attribute_name", "code", "data_type", "options",
			 "is_system", "capability_code", "category", "is_active"],
			as_dict=True,
		)
		if not attr or not attr.is_active:
			continue
		result.append({
			"attribute": row.attribute,
			"attribute_name": attr.attribute_name,
			"attribute_code": attr.code,
			"data_type": attr.data_type,
			"options": attr.options or "",
			"is_system": attr.is_system,
			"capability_code": attr.capability_code or "",
			"category": attr.category or "",
			"is_required": merged["is_required"],
			"display_order": merged["display_order"],
			"has_override": merged["has_override"],
		})

	result.sort(key=lambda x: (x["display_order"], x["attribute_name"]))
	return {"attributes": result}


@frappe.whitelist()
def get_unit_attribute_values(unit_name):
	"""Get all stored Unit Attribute Values for a unit.

	Returns a dict keyed by attribute name, with the typed value.
	Preserves 0 and false correctly.
	"""
	values = frappe.get_all(
		"Unit Attribute Value",
		filters={"unit": unit_name},
		fields=["name", "attribute", "value_text", "value_integer",
				"value_decimal", "value_check", "value_date"],
	)

	result = {}
	for v in values:
		# Get the attribute's data_type to return the correct value
		attr = frappe.db.get_value(
			"Unit Attribute", v.attribute,
			["data_type", "capability_code", "code"], as_dict=True,
		)
		if not attr:
			continue

		val = None
		if attr.data_type == "Check":
			val = bool(v.value_check)
		elif attr.data_type == "Integer":
			val = v.value_integer if v.value_integer is not None else None
		elif attr.data_type == "Decimal":
			val = float(v.value_decimal) if v.value_decimal is not None else None
		elif attr.data_type == "Date":
			val = v.value_date
		else:  # Text, Select
			val = v.value_text

		result[v.attribute] = {
			"name": v.name,
			"value": val,
			"data_type": attr.data_type,
			"capability_code": attr.capability_code or "",
			"attribute_code": attr.code or "",
		}

	return {"values": result}


@frappe.whitelist()
def save_unit_attribute_values(unit_name, attribute_values):
	"""Save Unit Attribute Values for a unit.

	``attribute_values`` is a JSON string: { "attribute_name": value, ... }

	Rules:
	- Only creates/updates values for attributes in the provided dict
	- Does NOT delete values for attributes not in the dict (preserves hidden values)
	- Validates data_type consistency
	- Validates required attributes (called by create_unit/update_unit)
	- Capability removal protection is enforced by the DocType controller
	"""
	import json

	if isinstance(attribute_values, str):
		attribute_values = json.loads(attribute_values)

	account = frappe.db.get_value("Rental Unit", unit_name, "rental_account")
	if not account:
		account = get_current_rental_account()

	for attr_name, value in attribute_values.items():
		# Skip None values — don't create empty records, but don't delete existing
		if value is None:
			continue

		attr = frappe.db.get_value(
			"Unit Attribute", attr_name,
			["name", "data_type", "capability_code"], as_dict=True,
		)
		if not attr:
			continue

		# Find existing value record
		existing = frappe.db.get_value(
			"Unit Attribute Value",
			{"unit": unit_name, "attribute": attr_name},
			"name",
		)

		if existing:
			doc = frappe.get_doc("Unit Attribute Value", existing)
		else:
			doc = frappe.get_doc({
				"doctype": "Unit Attribute Value",
				"rental_account": account,
				"unit": unit_name,
				"attribute": attr_name,
			})

		# Set the correct value field based on data_type
		dt = attr.data_type
		if dt == "Check":
			doc.value_check = 1 if value else 0
		elif dt == "Integer":
			try:
				doc.value_integer = int(value)
			except (ValueError, TypeError):
				doc.value_integer = None
		elif dt == "Decimal":
			try:
				doc.value_decimal = float(value)
			except (ValueError, TypeError):
				doc.value_decimal = None
		elif dt == "Date":
			doc.value_date = value if value else None
		else:  # Text, Select
			doc.value_text = str(value) if value is not None else None

		doc.save(ignore_permissions=is_system_manager())

	return {"success": True}


def _validate_required_attributes(unit_type, attribute_values):
	"""Validate that all required attributes have non-empty values.

	Called by create_unit and update_unit.
	Respects User Unit Preference overrides for is_required and is_active.
	"""
	from rental.rental.api.unit_settings import _merge_attribute_override

	type_doc = frappe.get_doc("Unit Type", unit_type) if unit_type else None
	if not type_doc:
		return

	for row in type_doc.attributes:
		merged = _merge_attribute_override(unit_type, row.attribute, {
			"is_required": row.is_required,
			"is_active": row.is_active,
		})
		if not merged["is_active"] or not merged["is_required"]:
			continue
		attr_name = frappe.db.get_value("Unit Attribute", row.attribute, "attribute_name")
		val = attribute_values.get(row.attribute)
		if val is None or val == "" or val == 0:
			frappe.throw(
				frappe._("الخاصية '{0}' مطلوبة").format(attr_name),
				frappe.ValidationError,
			)
