"""Contract charge validation, generation, and meter logic.

Ported from ``src/services/contract-charge.service.ts``.
"""

from __future__ import annotations

import frappe

from rental.rental.utils.date_utils import (
	to_calendar_day,
	build_fixed_periodic_schedule,
	round_money,
	calendar_day_diff,
	FIXED_PERIODIC_FREQUENCIES,
)


# Metered due type codes
METERED_DUE_TYPES = ["electricity", "water"]

# System due type codes (source: system-due-types.ts:14-18)
SYSTEM_DUE_TYPE_CODES = {"rent", "electricity", "water"}


def is_system_due_type_code(code: str | None) -> bool:
	"""Source: ``isSystemDueTypeCode`` (system-due-types.ts:23-26)."""
	return bool(code) and code in SYSTEM_DUE_TYPE_CODES


# ---------------------------------------------------------------------------
# Constants  (source: contract-charge.service.ts:16-82)
# ---------------------------------------------------------------------------

RESPONSIBILITIES = {"landlord": "landlord", "tenant": "tenant", "included": "included"}
CALCULATION_METHODS = {"metered": "metered", "fixed_periodic": "fixed_periodic", "actual_bill": "actual_bill", "on_demand": "on_demand"}
PAYMENT_BY = {"landlord": "landlord", "tenant": "tenant"}

PAYMENT_BY_LABELS = {"landlord": "المؤجر", "tenant": "المستأجر (مباشر)"}
RESPONSIBILITY_LABELS = {"landlord": "على المؤجر", "tenant": "على المستأجر", "included": "مشمول بالإيجار"}
CALCULATION_METHOD_LABELS = {
	"metered": "حسب الاستهلاك بالعداد",
	"fixed_periodic": "مبلغ ثابت دوري",
	"actual_bill": "حسب الفاتورة الفعلية",
	"on_demand": "حسب الحاجة",
}
COMMITMENT_TIMING = {"start": "start", "end": "end"}
LAST_PERIOD_HANDLING = {"none": "none", "prorated": "prorated", "manual": "manual"}

COMMITMENT_TIMING_LABELS = {"start": "بداية كل دورة", "end": "نهاية كل دورة"}
LAST_PERIOD_HANDLING_LABELS = {"none": "لا يتم احتسابها", "prorated": "احتساب نسبي", "manual": "تسوية يدوية"}


# ---------------------------------------------------------------------------
# Type helpers  (source: contract-charge.service.ts:115-222)
# ---------------------------------------------------------------------------


def is_metered_due_type_code(code: str | None) -> bool:
	"""Source: ``isMeteredDueTypeCode``."""
	return bool(code) and code in METERED_DUE_TYPES


def get_meter_field(code: str | None) -> str | None:
	"""Source: ``getMeterField``."""
	if code == "electricity":
		return "current_electricity_meter_reading"
	if code == "water":
		return "current_water_meter_reading"
	return None


def is_allowed_responsibility(value: str) -> bool:
	return value in RESPONSIBILITIES.values()


def is_allowed_calculation_method(value: str) -> bool:
	return value in CALCULATION_METHODS.values()


def is_allowed_payment_by(value: str | None) -> bool:
	return bool(value) and value in PAYMENT_BY.values()


def is_allowed_calculation_method_for_due_type(code: str | None, method: str) -> bool:
	"""Source: ``isAllowedCalculationMethodForDueType``."""
	if not is_allowed_calculation_method(method):
		return False
	if is_metered_due_type_code(code):
		return method != CALCULATION_METHODS["on_demand"]
	return method != CALCULATION_METHODS["metered"]


def get_default_responsibility_for_due_type(_code: str | None) -> str:
	"""Source: ``getDefaultResponsibilityForDueType``."""
	return RESPONSIBILITIES["landlord"]


def get_default_payment_by_for_responsibility(responsibility: str) -> str | None:
	"""Source: ``getDefaultPaymentByForResponsibility``."""
	if responsibility == RESPONSIBILITIES["tenant"]:
		return PAYMENT_BY["landlord"]
	return None


def get_default_calculation_method_for_due_type(code: str | None, responsibility: str, payment_by: str | None = None) -> str | None:
	"""Source: ``getDefaultCalculationMethodForDueType``."""
	if responsibility != RESPONSIBILITIES["tenant"]:
		return None
	if payment_by == PAYMENT_BY["tenant"]:
		return None
	return CALCULATION_METHODS["metered"] if is_metered_due_type_code(code) else CALCULATION_METHODS["fixed_periodic"]


def get_available_responsibilities() -> list[dict]:
	"""Source: ``getAvailableResponsibilities``."""
	return [{"value": r, "label": RESPONSIBILITY_LABELS[r]} for r in RESPONSIBILITIES.values()]


def get_available_calculation_methods_for_due_type(code: str | None, payment_by: str | None = None) -> list[dict]:
	"""Source: ``getAvailableCalculationMethodsForDueType``."""
	if payment_by == PAYMENT_BY["tenant"]:
		return []
	if is_metered_due_type_code(code):
		methods = ["metered", "fixed_periodic", "actual_bill"]
	else:
		methods = ["fixed_periodic", "actual_bill", "on_demand"]
	return [{"value": m, "label": CALCULATION_METHOD_LABELS[m]} for m in methods]


def get_available_calculation_methods_for_due_type_after_responsibility(
	code: str | None, responsibility: str, payment_by: str | None = None
) -> list[dict]:
	"""Source: ``getAvailableCalculationMethodsForDueTypeAfterResponsibility``."""
	if responsibility != RESPONSIBILITIES["tenant"]:
		return []
	return get_available_calculation_methods_for_due_type(code, payment_by)


def parse_decimal_amount(value) -> float | None:
	"""Source: ``parseDecimalAmount``."""
	if value is None or value == "":
		return None
	try:
		num = float(str(value).replace(",", ""))
	except (ValueError, TypeError):
		return None
	return num


def parse_date(value):
	"""Source: ``parseDate``."""
	if not value:
		return None
	return to_calendar_day(value)


def normalize_meter_reading(value) -> str | None:
	"""Source: ``normalizeMeterReading``."""
	if value is None or value == "":
		return None
	str_val = str(value).strip()
	if str_val == "":
		return None
	try:
		num = float(str_val)
	except ValueError:
		return None
	return str(num)


def is_valid_commitment_timing(value: str | None) -> bool:
	return bool(value) and value in COMMITMENT_TIMING.values()


def is_valid_last_period_handling(value: str | None) -> bool:
	return bool(value) and value in LAST_PERIOD_HANDLING.values()


# ---------------------------------------------------------------------------
# Validation  (source: validateContractCharges)
# ---------------------------------------------------------------------------


def validate_contract_charges(
	charge_inputs: list[dict],
	account: str,
	contract_start_date=None,
	contract_end_date=None,
) -> list[dict]:
	"""Validate a list of charge input dicts.

	Returns a normalised validated list where fields are set to ``None``
	unless the calculation method requires them (source: ``validateContractCharges``
	contract-charge.service.ts:230-398).

	Rules:
	- No duplicate due type per contract.
	- Due type must exist and be active (or system, or system code).
	- landlord/included: no paymentBy/calculationMethod allowed.
	- tenant: paymentBy required.
	- paymentBy=tenant: no calculation method.
	- paymentBy=landlord: calculation method required.
	- fixed_periodic: amount, frequency, commitmentTiming required; firstDueDate
	  forced to contract.startDate; ≥2 cycles within contract period.
	- metered: openingMeterReading required.
	"""
	if not isinstance(charge_inputs, list):
		frappe.throw(frappe._("بيانات الالتزامات غير صالحة"))

	seen_due_types = set()
	validated = []

	for charge in charge_inputs:
		due_type_name = charge.get("due_type")
		if not due_type_name:
			frappe.throw(frappe._("نوع الالتزام مطلوب لكل خدمة"))

		# Check duplicate
		if due_type_name in seen_due_types:
			frappe.throw(frappe._("لا يمكن تكرار نوع الالتزام في نفس العقد"))
		seen_due_types.add(due_type_name)

		# Check due type exists
		dt = frappe.db.get_value(
			"Rental Due Type", due_type_name,
			["name", "due_type_code", "is_system", "is_active", "due_type_name"],
			as_dict=True,
		)
		if not dt:
			frappe.throw(frappe._("نوع الالتزام غير موجود"))

		# Use due_type_name field for messages (falls back to name)
		dt_display = dt.due_type_name or dt.name

		# Due type must be active (or system, or system code)
		# Source: contract-charge.service.ts:267 — !isActive && !isSystem && !isSystemDueTypeCode(code)
		if not dt.is_active and not dt.is_system and not is_system_due_type_code(dt.due_type_code):
			frappe.throw(frappe._("نوع الالتزام {0} غير فعال ولا يمكن استخدامه في العقد").format(dt_display))

		responsibility = charge.get("responsibility")
		if not is_allowed_responsibility(responsibility):
			frappe.throw(frappe._("المسؤولية المحددة لخدمة {0} غير صالحة").format(dt_display))

		# Parse values (source: contract-charge.service.ts:280-287)
		payment_by_value = charge.get("payment_by")
		payment_by_value = payment_by_value if payment_by_value != "" else None
		amount = parse_decimal_amount(charge.get("amount"))
		frequency = charge.get("frequency") or None
		first_due_date = parse_date(charge.get("first_due_date"))
		commitment_timing = charge.get("commitment_timing") if is_valid_commitment_timing(charge.get("commitment_timing")) else None
		last_period_handling = charge.get("last_period_handling") if is_valid_last_period_handling(charge.get("last_period_handling")) else None
		last_period_adjustment_amount = parse_decimal_amount(charge.get("last_period_adjustment_amount"))
		opening_meter_reading = normalize_meter_reading(charge.get("opening_meter_reading"))

		calculation_method: str | None = None
		payment_by: str | None = None

		if responsibility in (RESPONSIBILITIES["landlord"], RESPONSIBILITIES["included"]):
			# No paymentBy allowed (source: contract-charge.service.ts:293-299)
			if payment_by_value:
				frappe.throw(
					frappe._("خيار الدفع لا ينطبق على خدمة {0} عندما يكون المتحمل {1}").format(
						dt_display, RESPONSIBILITY_LABELS[responsibility]
					)
				)
			# No calculationMethod allowed (source: contract-charge.service.ts:300-306)
			input_calc_method = charge.get("calculation_method")
			if input_calc_method:
				frappe.throw(
					frappe._("طريقة الاحتساب غير مطلوبة لخدمة {0} عندما يكون المتحمل {1}").format(
						dt_display, RESPONSIBILITY_LABELS[responsibility]
					)
				)
		elif responsibility == RESPONSIBILITIES["tenant"]:
			if not is_allowed_payment_by(payment_by_value):
				frappe.throw(
					frappe._("يجب تحديد من يدفع قيمة خدمة {0} (المؤجر أو المستأجر مباشرة)").format(dt_display)
				)
			payment_by = payment_by_value

			input_calc_method = charge.get("calculation_method")
			if payment_by == PAYMENT_BY["tenant"]:
				# No calculation method — tenant pays directly
				if input_calc_method:
					frappe.throw(
						frappe._("لا توجد طريقة احتساب لخدمة {0} عندما يدفع المستأجر مباشرة للجهة المختصة").format(dt_display)
					)
			else:
				# paymentBy === landlord: calculation method required
				if not input_calc_method:
					frappe.throw(frappe._("طريقة الاحتساب مطلوبة لخدمة {0}").format(dt_display))

				if not is_allowed_calculation_method_for_due_type(dt.due_type_code, input_calc_method):
					frappe.throw(
						frappe._("طريقة الاحتساب {0} غير مسموح بها لخدمة {1}").format(
							CALCULATION_METHOD_LABELS.get(input_calc_method, input_calc_method), dt_display
						)
					)
				calculation_method = input_calc_method

				if calculation_method == CALCULATION_METHODS["fixed_periodic"]:
					if amount is None or amount <= 0:
						frappe.throw(frappe._("المبلغ مطلوب وأكبر من صفر لخدمة {0}").format(dt_display))
					if not frequency or frequency not in FIXED_PERIODIC_FREQUENCIES:
						frappe.throw(frappe._("الدورية مطلوبة أو غير صالحة لخدمة {0}").format(dt_display))
					if not commitment_timing:
						frappe.throw(frappe._("توقيت الاستحقاق مطلوب لخدمة {0}").format(dt_display))

					start_day = to_calendar_day(contract_start_date) if contract_start_date else None
					end_day = to_calendar_day(contract_end_date) if contract_end_date else None

					if start_day and end_day:
						schedule = build_fixed_periodic_schedule(
							{
								"amount": amount,
								"frequency": frequency,
								"first_due_date": start_day,
								"commitment_timing": commitment_timing,
								"last_period_handling": last_period_handling,
								"last_period_adjustment_amount": last_period_adjustment_amount,
							},
							end_day,
						)
						if len(schedule) < 2:
							frappe.throw(
								frappe._("الدورية المختارة لخدمة {0} لا تنتج دورتين كاملتين ضمن مدة العقد").format(dt_display)
							)

					first_due_date = start_day

				if calculation_method == CALCULATION_METHODS["metered"]:
					if not opening_meter_reading:
						frappe.throw(frappe._("قراءة بداية العداد مطلوبة لخدمة {0}").format(dt_display))

		# Build normalised validated object (source: contract-charge.service.ts:382-394)
		is_fixed = calculation_method == CALCULATION_METHODS["fixed_periodic"]
		is_metered = calculation_method == CALCULATION_METHODS["metered"]
		validated.append({
			"due_type": due_type_name,
			"responsibility": responsibility,
			"payment_by": payment_by,
			"calculation_method": calculation_method,
			"amount": amount if is_fixed else None,
			"frequency": frequency if is_fixed else None,
			"first_due_date": first_due_date if is_fixed else None,
			"commitment_timing": commitment_timing if is_fixed else None,
			"last_period_handling": last_period_handling if is_fixed else None,
			"last_period_adjustment_amount": last_period_adjustment_amount if is_fixed else None,
			"opening_meter_reading": opening_meter_reading if is_metered else None,
		})

	return validated


# ---------------------------------------------------------------------------
# Save contract charges  (source: saveContractCharges)
# ---------------------------------------------------------------------------


def save_contract_charges(contract_doc, charge_inputs: list[dict], account: str) -> None:
	"""Validate and persist contract charges on *contract_doc*.

	Replaces existing charges with the new validated set.
	"""
	validated = validate_contract_charges(
		charge_inputs,
		account,
		contract_start_date=contract_doc.start_date,
		contract_end_date=contract_doc.end_date,
	)

	# Clear existing charges
	contract_doc.set("contract_charges", [])

	for charge in validated:
		contract_doc.append("contract_charges", {
			"due_type": charge.get("due_type"),
			"responsibility": charge.get("responsibility"),
			"calculation_method": charge.get("calculation_method"),
			"payment_by": charge.get("payment_by"),
			"amount": charge.get("amount"),
			"frequency": charge.get("frequency"),
			"first_due_date": charge.get("first_due_date"),
			"commitment_timing": charge.get("commitment_timing"),
			"last_period_handling": charge.get("last_period_handling"),
			"last_period_adjustment_amount": charge.get("last_period_adjustment_amount"),
			"opening_meter_reading": charge.get("opening_meter_reading"),
		})


# ---------------------------------------------------------------------------
# Get contract charges for contract  (source: getContractChargesForContract)
# ---------------------------------------------------------------------------


def get_contract_charges_for_contract(contract_name: str) -> list[dict]:
	"""Return all charges for a contract, ordered by creation ascending.

	Source: ``getContractChargesForContract`` (contract-charge.service.ts:798-805).
	"""
	return frappe.get_all(
		"Contract Charge",
		filters={"parent": contract_name, "parenttype": "Lease Contract"},
		fields=[
			"name",
			"due_type",
			"responsibility",
			"payment_by",
			"calculation_method",
			"amount",
			"frequency",
			"first_due_date",
			"commitment_timing",
			"last_period_handling",
			"last_period_adjustment_amount",
			"opening_meter_reading",
			"creation",
		],
		order_by="creation asc",
	)


# ---------------------------------------------------------------------------
# Fixed-periodic due generation  (source: generateFixedPeriodicDues)
# ---------------------------------------------------------------------------


def generate_fixed_periodic_dues(contract_doc, account: str) -> int:
	"""Create Due rows for fixed_periodic tenant charges paid by landlord.

	Source: ``generateFixedPeriodicDues`` (contract-charge.service.ts:488-580).
	Skips if a Due already exists for that due_type under this contract.
	Returns the number of dues created.
	"""
	from rental.rental.services.due_generation_service import create_due_from_schedule

	# Source: contract-charge.service.ts:501-503 — status must be active or expired
	if contract_doc.status not in ("active", "expired"):
		frappe.throw(frappe._("Contract must be active or expired"))

	# Filter fixed_periodic tenant charges paid by landlord (or null)
	# Source: contract-charge.service.ts:505-510
	fixed_charges = [
		c for c in contract_doc.contract_charges
		if (
			c.responsibility == "tenant"
			and c.payment_by in ("landlord", None)
			and c.calculation_method == "fixed_periodic"
		)
	]
	if not fixed_charges:
		return 0

	# Fetch existing auto dues for this contract (source: contract-charge.service.ts:520-524)
	existing_auto_dues = frappe.get_all(
		"Rental Due",
		filters={"contract": contract_doc.name, "source_type": "auto_contract"},
		pluck="due_type",
	)
	existing_due_type_names = set(existing_auto_dues)

	created = 0

	for charge in fixed_charges:
		# Source: contract-charge.service.ts:527 — skip if missing amount/frequency/firstDueDate
		if not charge.amount or not charge.frequency or not charge.first_due_date:
			continue

		# Source: contract-charge.service.ts:528 — skip if dues already exist for this due_type
		if charge.due_type in existing_due_type_names:
			continue

		# Source: contract-charge.service.ts:529-532 — skip if due type is inactive
		dt_active = frappe.db.get_value("Rental Due Type", charge.due_type, "is_active")
		if dt_active is False or dt_active == 0:
			frappe.msgprint(
				frappe._("تخطي الالتزامات الدورية الثابتة لنوع التزام غير فعال: {0}").format(charge.due_type)
			)
			continue

		schedule = build_fixed_periodic_schedule({
			"amount": charge.amount,
			"frequency": charge.frequency,
			"first_due_date": charge.first_due_date,
			"commitment_timing": charge.commitment_timing or "start",
			"last_period_handling": charge.last_period_handling or "none",
			"last_period_adjustment_amount": charge.last_period_adjustment_amount,
		}, contract_doc.end_date)

		for item in schedule:
			create_due_from_schedule(contract_doc, charge, item, account, calculation_method="fixed_periodic")
			created += 1

	return created


# ---------------------------------------------------------------------------
# Metered opening freeze  (source: freezeMeteredOpeningReadings)
# ---------------------------------------------------------------------------


def freeze_metered_opening_readings(contract_doc, account: str) -> None:
	"""On approval, copy metered charge openingMeterReading into Unit meter fields.

	Source: ``freezeMeteredOpeningReadings`` (contract-charge.service.ts:582-613).
	Only applies to tenant charges paid by landlord (or null) with metered method
	and a truthy openingMeterReading.
	"""
	# Filter metered tenant charges with truthy openingMeterReading
	# Source: contract-charge.service.ts:595-601
	metered_charges = [
		c for c in contract_doc.contract_charges
		if (
			c.calculation_method == "metered"
			and c.responsibility == "tenant"
			and c.payment_by in ("landlord", None)
			and c.opening_meter_reading  # truthy check (source: c.openingMeterReading)
		)
	]
	if not metered_charges:
		return

	for charge in metered_charges:
		dt_code = frappe.db.get_value("Rental Due Type", charge.due_type, "due_type_code")
		field = get_meter_field(dt_code)
		if not field:
			continue
		frappe.db.set_value(
			"Rental Unit", contract_doc.unit,
			field, charge.opening_meter_reading,
			update_modified=False,
		)


# ---------------------------------------------------------------------------
# Capture metered openings from unit  (source: captureMeteredOpeningsFromUnit)
# ---------------------------------------------------------------------------


def capture_metered_openings_from_unit(contract_doc, account: str) -> None:
	"""On renewal start, copy current unit readings into new contract charge.

	Source: ``captureMeteredOpeningsFromUnit`` (contract-charge.service.ts:615-653).
	Only applies to tenant charges paid by landlord (or null) with metered method.
	Updates both the contract charge's openingMeterReading and the unit's meter field.
	"""
	# Source: contract-charge.service.ts:626 — if !contract || !contract.unit: return
	if not contract_doc.unit:
		return

	unit = frappe.db.get_value(
		"Rental Unit", contract_doc.unit,
		["current_electricity_meter_reading", "current_water_meter_reading"],
		as_dict=True,
	)
	if not unit:
		return

	# Filter metered tenant charges (source: contract-charge.service.ts:628-633)
	metered_charges = [
		c for c in contract_doc.contract_charges
		if (
			c.calculation_method == "metered"
			and c.responsibility == "tenant"
			and c.payment_by in ("landlord", None)
		)
	]
	if not metered_charges:
		return

	for charge in metered_charges:
		dt_code = frappe.db.get_value("Rental Due Type", charge.due_type, "due_type_code")
		field = get_meter_field(dt_code)
		if not field:
			continue

		# Source: contract-charge.service.ts:640 — get currentReading from unit[field]
		current_reading = getattr(unit, field, None)
		# Source: contract-charge.service.ts:641 — if !currentReading: continue (truthy)
		if not current_reading:
			continue

		# Source: contract-charge.service.ts:643-646 — update contract charge openingMeterReading
		charge.opening_meter_reading = current_reading

		# Source: contract-charge.service.ts:648-651 — update unit field with currentReading
		frappe.db.set_value(
			"Rental Unit", contract_doc.unit,
			field, current_reading,
			update_modified=False,
		)


# ---------------------------------------------------------------------------
# Previous meter reading  (source: getPreviousMeterReading)
# ---------------------------------------------------------------------------


def get_previous_meter_reading(contract_name: str, unit_name: str, due_type_name: str) -> str:
	"""Return the last approved meter reading, or contract charge opening, or '0'.

	Source: ``getPreviousMeterReading`` (contract-charge.service.ts:663-688).
	Orders by [transactionDate desc, createdAt desc] and returns a string.
	"""
	# 1. Last approved due with a current meter reading for this contract/unit/type
	# Source: contract-charge.service.ts:663-672 — filters include unitId.
	last_due = frappe.get_all(
		"Rental Due",
		filters={
			"contract": contract_name,
			"unit": unit_name,
			"due_type": due_type_name,
			"docstatus": 1,
			"current_meter_reading": ["is", "set"],
		},
		fields=["current_meter_reading"],
		order_by="transaction_date desc, creation desc",
		limit=1,
	)
	if last_due and last_due[0].current_meter_reading:
		return str(last_due[0].current_meter_reading)

	# 2. Contract charge opening meter reading
	# Source: contract-charge.service.ts:678-688 — filters: responsibility=tenant,
	# calculationMethod=metered, paymentBy != tenant.
	charge = frappe.db.get_value(
		"Contract Charge",
		{
			"parent": contract_name,
			"parenttype": "Lease Contract",
			"due_type": due_type_name,
			"responsibility": "tenant",
			"calculation_method": "metered",
			"payment_by": ["!=", "tenant"],
		},
		"opening_meter_reading",
	)
	# Source: contract-charge.service.ts:688 — `openingMeterReading || '0'` (truthy)
	return str(charge) if charge else "0"


# ---------------------------------------------------------------------------
# Can create meter due  (source: canCreateMeterDue)
# ---------------------------------------------------------------------------


def can_create_meter_due(contract_name: str, due_type_name: str) -> dict:
	"""Validate that a metered due can be created for a contract.

	Source: ``canCreateMeterDue`` (contract-charge.service.ts:691-731).
	Returns ``{"ok": bool, "error": str | None, "contract": dict | None, "charge": dict | None}``.

	Order of checks (must match original):
	1. Contract not found → 'العقد غير موجود'
	2. start > today → 'لا يمكن إنشاء التزام مترية قبل بدء العقد'
	3. Charge not metered tenant → 'الخدمة ليست مترية في العقد'
	4. Status not active/expired → 'العقد غير نشط'
	5. Return ok with contract and charge
	"""
	contract = frappe.db.get_value(
		"Lease Contract", contract_name,
		["name", "status", "start_date", "unit", "tenant", "building", "contract_number"],
		as_dict=True,
	)

	# 1. Contract not found
	if not contract:
		return {"ok": False, "error": frappe._("العقد غير موجود"), "contract": None, "charge": None}

	# 2. start > today
	today = to_calendar_day(frappe.utils.today())
	start = to_calendar_day(contract.start_date)
	if start > today:
		return {"ok": False, "error": frappe._("لا يمكن إنشاء التزام مترية قبل بدء العقد"), "contract": None, "charge": None}

	# 3. Charge must be tenant + (landlord or null) + metered
	charge = frappe.db.get_value(
		"Contract Charge",
		{
			"parent": contract_name,
			"parenttype": "Lease Contract",
			"due_type": due_type_name,
			"responsibility": "tenant",
			"payment_by": ["in", ["landlord", None]],
			"calculation_method": "metered",
		},
		["name", "due_type", "responsibility", "payment_by", "calculation_method", "opening_meter_reading"],
		as_dict=True,
	)
	if not charge:
		return {"ok": False, "error": frappe._("الخدمة ليست مترية في العقد"), "contract": None, "charge": None}

	# 4. Status must be active or expired
	if contract.status not in ("active", "expired"):
		return {"ok": False, "error": frappe._("العقد غير نشط"), "contract": None, "charge": None}

	# 5. OK
	return {"ok": True, "error": None, "contract": contract, "charge": charge}


# ---------------------------------------------------------------------------
# Has active metered contract  (source: hasActiveMeteredContract)
# ---------------------------------------------------------------------------


def has_active_metered_contract(unit_name: str, due_type_code: str) -> bool:
	"""Whether an active current contract has a metered charge for electricity/water.

	Source: ``hasActiveMeteredContract`` (contract-charge.service.ts:733-762).
	Filters: responsibility===tenant && (paymentBy===landlord||null) &&
	calculationMethod===metered && dueType.code===code.
	"""
	today = to_calendar_day(frappe.utils.today())

	contracts = frappe.get_all(
		"Lease Contract",
		filters={
			"unit": unit_name,
			"status": "active",
			"start_date": ["<=", today],
			"end_date": [">=", today],
		},
		fields=["name"],
	)

	for c in contracts:
		charges = frappe.get_all(
			"Contract Charge",
			filters={
				"parent": c.name,
				"parenttype": "Lease Contract",
				"responsibility": "tenant",
				"payment_by": ["in", ["landlord", None]],
				"calculation_method": "metered",
			},
			fields=["due_type"],
		)
		for ch in charges:
			code = frappe.db.get_value("Rental Due Type", ch.due_type, "due_type_code")
			if code == due_type_code:
				return True

	return False


# ---------------------------------------------------------------------------
# Copy charges for renewal  (source: copyContractChargesForRenewal)
# ---------------------------------------------------------------------------


def copy_contract_charges_for_renewal(old_contract_doc, new_contract_doc, account: str) -> None:
	"""Copy charges from old contract to new renewal contract.

	Source: ``copyContractChargesForRenewal`` (contract-charge.service.ts:777-795).
	- amount = charge.amount only when responsibility == 'tenant', else None.
	- first_due_date = new contract start only when calculation_method == 'fixed_periodic', else None.
	- opening_meter_reading = None (reset for renewal).
	"""
	new_contract_doc.set("contract_charges", [])

	for charge in old_contract_doc.contract_charges:
		is_tenant = charge.responsibility == "tenant"
		is_fixed_periodic = charge.calculation_method == "fixed_periodic"
		new_contract_doc.append("contract_charges", {
			"due_type": charge.due_type,
			"responsibility": charge.responsibility,
			"calculation_method": charge.calculation_method,
			"payment_by": charge.payment_by,
			# A16: amount only for tenant charges (legacy line 785).
			"amount": charge.amount if is_tenant else None,
			"frequency": charge.frequency if is_fixed_periodic else None,
			# A16: first_due_date only for fixed_periodic (legacy line 787-788).
			"first_due_date": new_contract_doc.start_date if is_fixed_periodic else None,
			"commitment_timing": charge.commitment_timing,
			"last_period_handling": charge.last_period_handling,
			"last_period_adjustment_amount": charge.last_period_adjustment_amount,
			"opening_meter_reading": None,  # Reset for renewal
		})


# ---------------------------------------------------------------------------
# Build service clause text  (source: buildServiceClauseText)
# ---------------------------------------------------------------------------


def build_service_clause_text(charge) -> str | None:
	"""Return Arabic contract clause text for a charge (for print).

	Source: ``buildServiceClauseText`` (contract-charge.service.ts:818-855).
	Returns ``None`` when the charge is invalid (e.g. tenant charge with a
	calculation method not allowed for the due type).
	"""
	dt = frappe.db.get_value(
		"Rental Due Type", charge.due_type,
		["due_type_name", "due_type_code"], as_dict=True,
	)
	if not dt:
		return None
	dt_name = dt.due_type_name
	dt_code = dt.due_type_code

	# Tenant charge with a calculation method not allowed for the due type → None.
	if charge.responsibility == "tenant" and charge.calculation_method:
		if not is_allowed_calculation_method_for_due_type(dt_code, charge.calculation_method):
			return None

	if charge.responsibility == "landlord":
		return f"يتحمل المؤجر التكاليف المتعلقة بـ {dt_name}، ولا يترتب على المستأجر أي التزام مالي مستقل بشأنها."
	if charge.responsibility == "included":
		return f"تُعد خدمة {dt_name} مشمولة في مبلغ الإيجار المتفق عليه، ولا يترتب على المستأجر أي مبلغ إضافي مستقل بشأنها."
	if charge.responsibility == "tenant":
		if charge.payment_by == "tenant":
			return f"يلتزم المستأجر بتسديد فواتير {dt_name} مباشرة للجهة المختصة، ولا يترتب على المؤجر أي التزام مالي مستقل بشأنها."
		method = charge.calculation_method
		if method == "fixed_periodic":
			if not charge.amount or not charge.frequency:
				return None
			freq_label = _get_frequency_label(charge.frequency)
			return f"يلتزم المستأجر بسداد مبلغ قدره {_format_currency(float(charge.amount))} {freq_label} بدل {dt_name} للمؤجر."
		if method == "metered":
			reading = charge.opening_meter_reading or "—"
			return f"يتحمل المستأجر تكاليف استهلاك {dt_name} حسب قراءة العداد، وتبلغ قراءة العداد عند بداية العقد {reading}، ويُحتسب الاستهلاك وفق سعر الوحدة المعتمد وقت تسجيل الاستهلاك، ويسدد المبلغ للمؤجر."
		if method == "actual_bill":
			return f"يتحمل المستأجر تكلفة {dt_name} وفق قيمة الفاتورة الفعلية المسجلة خلال مدة العقد، ويسددها للمؤجر."
		if method == "on_demand":
			return f"يتحمل المستأجر تكاليف {dt_name} عند الحاجة وفق المبالغ المستحقة والمسجلة خلال مدة العقد، ويسدها للمؤجر."
	return None


def _get_frequency_label(frequency: str) -> str:
	"""Source: getFrequencyLabel (contract-charge.service.ts:857-873)."""
	labels = {
		"once": "مرة واحدة",
		"monthly": "شهريًا",
		"bi_monthly": "كل شهرين",
		"quarterly": "ربع سنويًا",
		"semi_annual": "نصف سنويًا",
		"annual": "سنويًا",
	}
	return labels.get(frequency, frequency)


def _format_currency(amount: float) -> str:
	"""Source: formatCurrency (contract-charge.service.ts:876-878)."""
	return f"{amount:,.2f}"


# ---------------------------------------------------------------------------
# Default contract charges  (source: getDefaultContractCharges)
# ---------------------------------------------------------------------------


def get_default_contract_charges(account: str, unit_name: str | None = None) -> list[dict]:
	"""Return default charges for a new contract.

	Source: ``getDefaultContractCharges`` (contract-charge.service.ts:443-481).
	Returns ALL active due types EXCEPT rent, each with:
	- responsibility = 'landlord'
	- payment_by = None
	- calculation_method = None
	- amount, frequency, first_due_date, etc. = None
	- opening_meter_reading = None (meter readings are only relevant when
	  responsibility is tenant, which is not the default).

	System due types (rent excluded) are listed first (is_system desc).
	"""
	# Ensure system due types exist before listing defaults.
	from rental.rental.services.due_generation_service import ensure_system_due_types
	ensure_system_due_types()

	filters = {"is_active": 1}
	if account:
		# Include system due types (no account) + account-scoped due types.
		filters = {
			"is_active": 1,
			"or": [
				{"is_system": 1},
				{"rental_account": account},
			],
		}

	due_types = frappe.get_all(
		"Rental Due Type",
		filters=filters,
		fields=["name", "due_type_code", "due_type_name", "is_system"],
		order_by="is_system desc",
	)

	defaults = []
	for dt in due_types:
		# Exclude rent (handled by rent due generation).
		if dt.due_type_code == "rent":
			continue
		defaults.append({
			"due_type": dt.name,
			"responsibility": "landlord",
			"payment_by": None,
			"calculation_method": None,
			"amount": None,
			"frequency": None,
			"first_due_date": None,
			"commitment_timing": None,
			"last_period_handling": None,
			"last_period_adjustment_amount": None,
			"opening_meter_reading": None,
		})

	return defaults
