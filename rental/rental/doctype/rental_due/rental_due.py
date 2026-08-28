import frappe
from frappe.model.document import Document

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.utils.date_utils import to_calendar_day, round_money


class RentalDue(Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		# Auto-contract dues cannot be edited individually
		if self.source_type == "auto_contract" and not self.is_new() and not self.flags.from_generation:
			original = frappe.db.get_value("Rental Due", self.name, "source_type")
			if original == "auto_contract":
				frappe.throw(frappe._("Auto-contract dues cannot be edited individually."))

		# Metered due: compute consumption and amount on validate
		if self.calculation_method == "metered" and self.current_meter_reading is not None:
			prev = float(self.previous_meter_reading or 0)
			curr = float(self.current_meter_reading)
			if curr < prev:
				frappe.throw(frappe._("القراءة الحالية يجب أن تكون أكبر من أو تساوي القراءة السابقة"))
			self.meter_consumption = round_money(curr - prev)
			if self.unit_price:
				self.amount = round_money(self.meter_consumption * float(self.unit_price))

	def on_submit(self):
		"""On approval (submit): generate due_number if not set, update unit meter."""
		if not self.due_number:
			from rental.rental.doctype.rental_settings.rental_settings import generate_due_number
			self.due_number = generate_due_number(self.rental_account)
			self.db_set("due_number", self.due_number)

		# Update unit meter reading for metered dues
		if self.calculation_method == "metered" and self.current_meter_reading is not None:
			self._update_unit_meter()

	def on_cancel(self):
		"""On cancellation: record cancellation metadata, rollback meter if metered."""
		if not self.cancellation_reason:
			frappe.throw(frappe._("سبب الإلغاء مطلوب"))

		self.cancelled_by = frappe.session.user
		self.cancelled_at = frappe.utils.now()

		# Rollback meter for metered dues
		if self.calculation_method == "metered":
			self._rollback_unit_meter()

	def _update_unit_meter(self):
		"""Update the unit's current meter reading to this due's current reading."""
		from rental.rental.services.contract_charge_service import get_meter_field

		dt_code = frappe.db.get_value("Rental Due Type", self.due_type, "due_type_code")
		field = get_meter_field(dt_code)
		if field and self.unit:
			frappe.db.set_value(
				"Rental Unit", self.unit, field,
				self.current_meter_reading, update_modified=False,
			)

	def _rollback_unit_meter(self):
		"""Rollback the unit meter to the previous reading."""
		from rental.rental.services.contract_charge_service import get_meter_field

		dt_code = frappe.db.get_value("Rental Due Type", self.due_type, "due_type_code")
		field = get_meter_field(dt_code)
		if field and self.unit:
			# Only rollback if the current unit reading matches this due's reading
			current_unit_reading = frappe.db.get_value("Rental Unit", self.unit, field)
			if current_unit_reading is not None and float(current_unit_reading) == float(self.current_meter_reading):
				frappe.db.set_value(
					"Rental Unit", self.unit, field,
					self.previous_meter_reading or 0, update_modified=False,
				)
