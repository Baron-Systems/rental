"""Date, period, and frequency utilities.

Ported from the source-of-truth ``src/lib/utils.ts`` and ``src/lib/constants.ts``.
All date comparisons use calendar-day granularity (UTC midnight) to avoid
timezone-shifting bugs.
"""

from __future__ import annotations

import calendar
import math
from datetime import date, datetime, timedelta
from typing import Sequence

import frappe

# ---------------------------------------------------------------------------
# Frequency constants  (source: src/lib/constants.ts)
# ---------------------------------------------------------------------------

PAYMENT_FREQUENCIES = ["once", "monthly", "bi_monthly", "quarterly", "semi_annual", "annual"]

FIXED_PERIODIC_FREQUENCIES = ["monthly", "bi_monthly", "quarterly", "semi_annual", "annual"]

FREQUENCY_MONTHS = {
	"monthly": 1,
	"bi_monthly": 2,
	"quarterly": 3,
	"semi_annual": 6,
	"annual": 12,
}

# Alias map for tolerant parsing (source: getFrequencyInterval aliases)
_FREQUENCY_ALIASES = {
	"one_time": "once",
	"bimonthly": "bi_monthly",
	"semiannual": "semi_annual",
	"semi-annual": "semi_annual",
	"semi_annual": "semi_annual",
	"weekly": "weekly",
}


def normalise_frequency(frequency: str | None) -> str:
	"""Return the canonical frequency string."""
	if not frequency:
		return "monthly"
	f = frequency.strip().lower()
	return _FREQUENCY_ALIASES.get(f, f)


def get_frequency_months(frequency: str) -> int:
	"""Number of calendar months in one cycle of *frequency*."""
	f = normalise_frequency(frequency)
	if f == "weekly":
		return 0  # weekly is day-based, not month-based
	if f == "once":
		return 0
	return FREQUENCY_MONTHS.get(f, 1)


def get_frequency_days(frequency: str) -> int:
	"""Approximate number of days in one cycle (used for weekly)."""
	f = normalise_frequency(frequency)
	if f == "weekly":
		return 7
	if f == "once":
		return 0
	return get_frequency_months(f) * 30  # rough approximation


# ---------------------------------------------------------------------------
# Calendar-day helpers  (source: src/lib/utils.ts → toCalendarDay etc.)
# ---------------------------------------------------------------------------


def to_calendar_day(value) -> date:
	"""Convert *value* to a ``datetime.date`` at calendar-day granularity.

	Accepts ``date``, ``datetime``, or ISO-8601 string (``YYYY-MM-DD`` or
	``YYYY-MM-DDTHH:MM:SS...``).
	"""
	if value is None:
		return date.today()
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	if isinstance(value, str):
		date_part = value.split("T")[0]
		year, month, day = (int(x) for x in date_part.split("-"))
		return date(year, month, day)
	# Fallback: let Python try
	return date.fromisoformat(str(value))


def add_days(d, days: int) -> date:
	"""Add *days* calendar days to *d*."""
	return to_calendar_day(d) + timedelta(days=days)


def previous_calendar_day(d) -> date:
	"""Return the calendar day before *d*."""
	return to_calendar_day(d) - timedelta(days=1)


def add_calendar_months(d, months: int, anchor_day: int | None = None) -> date:
	"""Add *months* calendar months to *d*, clamping the day to month end.

	If *anchor_day* is given, the result day is clamped to ``anchor_day`` (or
	month end if the month is shorter).
	"""
	base = to_calendar_day(d)
	if anchor_day is None:
		anchor_day = base.day

	total = base.year * 12 + base.month - 1 + months
	year, month_idx = divmod(total, 12)
	month = month_idx + 1
	last_day = calendar.monthrange(year, month)[1]
	day = min(anchor_day, last_day)
	return date(year, month, day)


def calendar_day_diff(a, b) -> int:
	"""Whole-day difference ``b - a`` (can be negative).

	Matches legacy ``calendarDayDiff(a, b) = b - a`` (days from *a* to *b*).
	"""
	return (to_calendar_day(b) - to_calendar_day(a)).days


def start_of_day(d) -> date:
	"""Same as :func:`to_calendar_day` — calendar day."""
	return to_calendar_day(d)


def validate_dates(start, end) -> bool:
	"""Return ``True`` when ``start < end`` (calendar comparison)."""
	return to_calendar_day(start) < to_calendar_day(end)


def get_contract_period_status(start, end, today=None) -> str:
	"""Return ``'past'``, ``'current'``, or ``'upcoming'``.

	Matches legacy ``getContractPeriodStatus`` (utils.ts:86-98) which uses
	``'upcoming'`` (not ``'future'``).
	"""
	t = to_calendar_day(today) if today else date.today()
	s = to_calendar_day(start)
	e = to_calendar_day(end)
	if e < t:
		return "past"
	if s > t:
		return "upcoming"
	return "current"


# ---------------------------------------------------------------------------
# Period / schedule builders
# ---------------------------------------------------------------------------


def get_period_label(start, frequency: str, index: int) -> str:
	"""Human-readable Arabic period label (source: getPeriodLabel)."""
	from datetime import date as _date

	f = normalise_frequency(frequency)
	s = to_calendar_day(start)

	if f == "once":
		return "دفعة واحدة"

	if f == "weekly":
		end_day = add_days(s, 6)
		return f"من {s.strftime('%Y-%m-%d')} إلى {end_day.strftime('%Y-%m-%d')}"

	# Monthly+ — Arabic month/year
	months_ar = [
		"يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
		"يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
	]
	return f"{months_ar[s.month - 1]} {s.year}"


def build_periodic_schedule(
	start_date,
	end_date,
	frequency: str,
	amount: float,
	commitment_timing: str = "start",
	first_due_date=None,
	max_count: int | None = None,
) -> list[dict]:
	"""Build the rent due schedule for a contract.

	Returns a list of dicts with keys:
	``index``, ``due_date``, ``period_start``, ``period_end``, ``amount``,
	``period_label``.

	Source: ``buildPeriodicSchedule`` in ``src/lib/utils.ts``.
	"""
	f = normalise_frequency(frequency)
	contract_start = to_calendar_day(start_date)
	contract_end = to_calendar_day(end_date)

	# The base date for scheduling (firstDueDate or startDate)
	base = to_calendar_day(first_due_date) if first_due_date else contract_start

	schedule: list[dict] = []
	index = 0

	if f == "once":
		due_date = base if commitment_timing == "start" else contract_end
		if due_date <= contract_end:
			schedule.append({
				"index": 0,
				"due_date": due_date,
				"period_start": base,
				"period_end": contract_end,
				"amount": float(amount),
				"period_label": get_period_label(base, f, 0),
			})
		return schedule

	if f == "weekly":
		period_start = base
		while True:
			period_end = add_days(period_start, 6)
			due_date = period_start if commitment_timing == "start" else period_end
			if due_date > contract_end:
				break
			schedule.append({
				"index": index,
				"due_date": due_date,
				"period_start": period_start,
				"period_end": period_end,
				"amount": float(amount),
				"period_label": get_period_label(period_start, f, index),
			})
			index += 1
			period_start = add_days(period_end, 1)
			if max_count and len(schedule) >= max_count:
				break
		return schedule

	# Monthly+
	months = get_frequency_months(f)
	anchor_day = base.day
	period_start = base

	while True:
		next_boundary = add_calendar_months(period_start, months, anchor_day=anchor_day)
		period_end = previous_calendar_day(next_boundary)

		if commitment_timing == "start":
			due_date = period_start
		else:
			due_date = period_end

		if due_date > contract_end:
			break

		# Legacy does NOT clamp period_end to contract_end (utils.ts:338).
		schedule.append({
			"index": index,
			"due_date": due_date,
			"period_start": period_start,
			"period_end": period_end,
			"amount": float(amount),
			"period_label": get_period_label(period_start, f, index),
		})

		index += 1
		period_start = next_boundary
		if max_count and len(schedule) >= max_count:
			break

	return schedule


def _fixed_periodic_label(period_start, period_end) -> str:
	"""Fixed-periodic due label: ``من {dd/mm/yyyy} إلى {dd/mm/yyyy}``.

	Source: ``analyzeFixedPeriodicCharge`` dues label (legacy utils.ts:527,545).
	"""
	return f"من {format_date(period_start)} إلى {format_date(period_end)}"


def build_fixed_periodic_schedule(charge, contract_end_date) -> list[dict]:
	"""Build the schedule for a fixed-periodic contract charge.

	*charge* is a dict-like with keys: ``amount``, ``frequency``,
	``first_due_date``, ``commitment_timing``, ``last_period_handling``,
	``last_period_adjustment_amount``.

	Source: ``buildFixedPeriodicSchedule`` in ``src/lib/utils.ts``.
	"""
	f = normalise_frequency(charge.get("frequency"))
	amount = float(charge.get("amount") or 0)
	start = to_calendar_day(charge.get("first_due_date"))
	contract_end = to_calendar_day(contract_end_date)
	commitment_timing = charge.get("commitment_timing") or "start"
	last_handling = charge.get("last_period_handling") or "none"
	last_adj = float(charge.get("last_period_adjustment_amount") or 0)

	months = get_frequency_months(f)
	anchor_day = start.day
	period_start = start
	schedule: list[dict] = []
	index = 0

	while True:
		next_boundary = add_calendar_months(period_start, months, anchor_day=anchor_day)
		period_end = previous_calendar_day(next_boundary)

		if period_start > contract_end:
			break

		if period_end <= contract_end:
			# Full cycle
			due_date = period_start if commitment_timing == "start" else period_end
			schedule.append({
				"index": index,
				"due_date": due_date,
				"period_start": period_start,
				"period_end": period_end,
				"amount": amount,
				"period_label": _fixed_periodic_label(period_start, period_end),
			})
		else:
			# Partial last period
			if last_handling == "none":
				pass  # skip
			elif last_handling == "prorated":
				# Legacy: fullPeriodDays = max(1, calendarDayDiff(partialStart, nextBoundary))
				#         partialDays   = max(0, calendarDayDiff(partialStart, end))
				# calendar_day_diff(a, b) = b - a, so:
				#   full_days   = nextBoundary - partialStart = (period_end + 1) - period_start
				#   partial_days = end - partialStart (exclusive of end, no +1)
				full_days = calendar_day_diff(period_start, period_end) + 1
				if full_days < 1:
					full_days = 1
				partial_days = calendar_day_diff(period_start, contract_end)
				if partial_days < 0:
					partial_days = 0
				prorated = round_money(amount * partial_days / full_days)
				due_date = period_start if commitment_timing == "start" else contract_end
				schedule.append({
					"index": index,
					"due_date": due_date,
					"period_start": period_start,
					"period_end": contract_end,
					"amount": prorated,
					"period_label": _fixed_periodic_label(period_start, contract_end),
				})
			elif last_handling == "manual":
				due_date = period_start if commitment_timing == "start" else contract_end
				schedule.append({
					"index": index,
					"due_date": due_date,
					"period_start": period_start,
					"period_end": contract_end,
					"amount": last_adj,
					"period_label": _fixed_periodic_label(period_start, contract_end),
				})
			break

		index += 1
		period_start = next_boundary

	return schedule


def calculate_contract_end_date(start_date, frequency: str, cycles: int) -> date:
	"""Calculate the end date given start, frequency and number of cycles.

	Source: ``calculateContractEndDate``.
	"""
	f = normalise_frequency(frequency)
	months = get_frequency_months(f)
	start = to_calendar_day(start_date)
	next_boundary = add_calendar_months(start, months * cycles, anchor_day=start.day)
	return previous_calendar_day(next_boundary)


# ---------------------------------------------------------------------------
# Money helpers
# ---------------------------------------------------------------------------


def round_money(value) -> float:
	"""Round to 2 decimal places (source: roundMoney)."""
	return round(float(value) + 1e-9, 2)


def format_currency(amount, currency: str | None = None) -> str:
	"""Format a monetary amount with 2 decimals and optional currency code."""
	formatted = f"{float(amount):,.2f}"
	if currency:
		return f"{formatted} {currency}"
	return formatted


def format_date(d) -> str:
	"""Format a date as ``dd/mm/yyyy`` (source: formatDate, en-GB)."""
	return to_calendar_day(d).strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Numbering helpers
# ---------------------------------------------------------------------------


def generate_number(prefix: str, counter: int) -> str:
	"""Generate a zero-padded number: ``prefix-0001``."""
	return f"{prefix}-{counter + 1:04d}"


# ---------------------------------------------------------------------------
# Frequency count  (source: getFrequencyCount)
# ---------------------------------------------------------------------------


def get_frequency_count(start_date, end_date, frequency: str, commitment_timing: str | None = "start") -> int:
	"""Return the number of dues generated for a periodic schedule.

	Source: ``getFrequencyCount`` (utils.ts:347-350).
	"""
	schedule = build_periodic_schedule({
		"start_date": start_date,
		"end_date": end_date,
		"frequency": frequency,
		"commitment_timing": commitment_timing or "start",
		"amount": 0,
	})
	return max(0, len(schedule))


# ---------------------------------------------------------------------------
# Partial period helpers  (source: getPartialPeriodInfo, hasPartialLastPeriod)
# ---------------------------------------------------------------------------


def get_partial_period_info(charge, contract_end_date) -> dict:
	"""Return ``{has_partial, start, end}`` for a fixed-periodic charge.

	Source: ``getPartialPeriodInfo`` (utils.ts:578-588).
	"""
	analysis = analyze_fixed_periodic_charge(charge, contract_end_date)
	partial = analysis.get("partial_period", {})
	return {
		"has_partial": bool(partial.get("exists")),
		"start": partial.get("start_date"),
		"end": partial.get("end_date"),
	}


def has_partial_last_period(charge, contract_end_date) -> bool:
	"""Return True if a fixed-periodic charge has a partial last period.

	Source: ``hasPartialLastPeriod`` (utils.ts:590-595).
	"""
	return bool(analyze_fixed_periodic_charge(charge, contract_end_date).get("partial_period", {}).get("exists"))


def analyze_fixed_periodic_charge(charge, contract_end_date) -> dict:
	"""Full analysis of a fixed-periodic charge.

	Source: ``analyzeFixedPeriodicCharge`` (utils.ts:423-563).
	Returns ``{full_cycles, partial_period, full_cycles_total,
	settlement_amount, total_amount, dues}``.
	"""
	empty = {
		"full_cycles": [],
		"partial_period": {"exists": False, "start_date": None, "end_date": None, "handling": "none", "amount": 0},
		"full_cycles_total": 0,
		"settlement_amount": 0,
		"total_amount": 0,
		"dues": [],
	}

	amount = float(charge.get("amount") or 0)
	frequency = charge.get("frequency")
	first_due_date = charge.get("first_due_date")
	if not amount or not frequency or not first_due_date or not contract_end_date:
		return empty
	if amount <= 0:
		return empty

	start = to_calendar_day(first_due_date)
	end = to_calendar_day(contract_end_date)
	if start > end:
		return empty

	f = normalise_frequency(frequency)
	months = get_frequency_months(f)
	handling = charge.get("last_period_handling") or "none"
	manual_amount = float(charge.get("last_period_adjustment_amount") or 0)
	is_end_timing = charge.get("commitment_timing") == "end"

	# Single-period services (once/weekly): single due at start or end
	if months == 0 and f not in ("monthly", "bi_monthly", "quarterly", "semi_annual", "annual"):
		due_date = end if is_end_timing else start
		return {
			"full_cycles": [],
			"partial_period": {"exists": False, "start_date": None, "end_date": None, "handling": handling, "amount": 0},
			"full_cycles_total": 0,
			"settlement_amount": 0,
			"total_amount": amount,
			"dues": [{
				"index": 0,
				"due_date": due_date,
				"period_start": start,
				"period_end": end,
				"amount": amount,
				"period_label": "دفعة واحدة",
			}],
		}

	anchor_day = start.day
	full_cycles = []
	period_start = start
	i = 0

	while i <= 1000:
		next_boundary = add_calendar_months(period_start, months, anchor_day=anchor_day)
		cycle_end = previous_calendar_day(next_boundary)
		if cycle_end > end:
			break
		due_date = period_start if not is_end_timing else cycle_end
		full_cycles.append({
			"start_date": period_start,
			"end_date": cycle_end,
			"due_date": due_date,
			"amount": amount,
		})
		i += 1
		period_start = next_boundary

	full_cycle_count = len(full_cycles)
	partial_start = add_calendar_months(start, months * full_cycle_count, anchor_day=anchor_day) if full_cycle_count else start
	# Recompute partial_start properly
	if full_cycle_count:
		partial_start = add_calendar_months(start, months * full_cycle_count, anchor_day=anchor_day)
	else:
		partial_start = start
	partial_exists = partial_start <= end and partial_start != start

	# Actually partial exists only if there's a remaining period after full cycles
	# that is shorter than a full cycle
	if full_cycle_count:
		last_full_end = full_cycles[-1]["end_date"]
		partial_start = add_calendar_months(last_full_end, 1, anchor_day=anchor_day)
		partial_exists = partial_start <= end
	else:
		partial_exists = False

	settlement_amount = 0
	if partial_exists:
		if handling == "prorated":
			next_boundary = add_calendar_months(partial_start, months, anchor_day=anchor_day)
			full_days = max(1, calendar_day_diff(partial_start, next_boundary))
			partial_days = max(0, calendar_day_diff(partial_start, end))
			settlement_amount = round_money(amount * partial_days / full_days)
		elif handling == "manual" and manual_amount >= 0:
			settlement_amount = manual_amount

	full_cycles_total = round_money(amount * full_cycle_count)
	total_amount = round_money(full_cycles_total + settlement_amount)

	dues = []
	for idx, cycle in enumerate(full_cycles):
		dues.append({
			"index": idx,
			"due_date": cycle["due_date"],
			"period_start": cycle["start_date"],
			"period_end": cycle["end_date"],
			"amount": cycle["amount"],
			"period_label": _fixed_periodic_label(cycle["start_date"], cycle["end_date"]),
		})

	if partial_exists and handling != "none":
		next_boundary = add_calendar_months(partial_start, months, anchor_day=anchor_day)
		last_day_of_partial = previous_calendar_day(next_boundary)
		partial_due_date = min(end, last_day_of_partial) if is_end_timing else partial_start
		dues.append({
			"index": full_cycle_count,
			"due_date": partial_due_date,
			"period_start": partial_start,
			"period_end": end,
			"amount": settlement_amount,
			"period_label": _fixed_periodic_label(partial_start, end),
		})

	return {
		"full_cycles": full_cycles,
		"partial_period": {
			"exists": partial_exists,
			"start_date": partial_start if partial_exists else None,
			"end_date": end if partial_exists else None,
			"handling": handling,
			"amount": settlement_amount,
		},
		"full_cycles_total": full_cycles_total,
		"settlement_amount": settlement_amount,
		"total_amount": total_amount,
		"dues": dues,
	}


# ---------------------------------------------------------------------------
# Available fixed-periodic frequencies  (source: getAvailableFixedPeriodicFrequencies)
# ---------------------------------------------------------------------------


FIXED_PERIODIC_FREQUENCIES = ["monthly", "bi_monthly", "quarterly", "semi_annual", "annual"]


def get_available_fixed_periodic_frequencies(
	start_date,
	end_date,
	commitment_timing: str | None = None,
	last_period_handling: str | None = None,
) -> list[str]:
	"""Return the list of frequencies that produce at least one due.

	Source: ``getAvailableFixedPeriodicFrequencies`` (utils.ts:396-415).
	"""
	available = []
	for frequency in FIXED_PERIODIC_FREQUENCIES:
		schedule = build_fixed_periodic_schedule(
			{
				"amount": 1,
				"frequency": frequency,
				"first_due_date": start_date,
				"commitment_timing": "start",
				"last_period_handling": "none",
			},
			end_date,
		)
		if len(schedule) >= 1:
			available.append(frequency)
	return available
