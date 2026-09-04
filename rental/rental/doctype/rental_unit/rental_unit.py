import frappe

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.unit_service import derive_unit_status, update_building_counts


class RentalUnit(frappe.model.document.Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		if self.building:
			building_account = frappe.db.get_value("Rental Building", self.building, "rental_account")
			if building_account != self.rental_account:
				frappe.throw(
					frappe._("Building must belong to the same Rental Account.")
				)

			if self.is_new():
				is_active = frappe.db.get_value("Rental Building", self.building, "is_active")
				if not is_active:
					frappe.throw(
						frappe._("Cannot add unit to a disabled building.")
					)

		if self.floor:
			floor_building = frappe.db.get_value("Rental Floor", self.floor, "building")
			floor_account = frappe.db.get_value("Rental Floor", self.floor, "rental_account")
			if floor_building != self.building:
				frappe.throw(
					frappe._("Floor must belong to the same building as the unit.")
				)
			if floor_account != self.rental_account:
				frappe.throw(
					frappe._("Floor must belong to the same Rental Account.")
				)

		existing = frappe.db.exists(
			"Rental Unit",
			{
				"building": self.building,
				"unit_number": self.unit_number,
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(
				frappe._("لا يمكن حفظ الوحدة، رقم الوحدة مستخدم مسبقًا في هذا العقار. يرجى إدخال رقم وحدة مختلف.")
			)

		self.status = derive_unit_status(self)

	def after_insert(self):
		update_building_counts(self.building)

	def on_trash(self):
		# Safety net: matches old app canDelete check
		# (contracts, evictions, dues, receipts)
		has_history = False
		if frappe.db.exists("DocType", "Lease Contract"):
			if frappe.db.count("Lease Contract", {"unit": self.name}):
				has_history = True
		if not has_history and frappe.db.exists("DocType", "Eviction"):
			if frappe.db.count("Eviction", {"unit": self.name}):
				has_history = True
		if not has_history and frappe.db.exists("DocType", "Rental Due"):
			if frappe.db.count("Rental Due", {"unit": self.name}):
				has_history = True
		if not has_history and frappe.db.exists("DocType", "Rental Receipt"):
			if frappe.db.count("Rental Receipt", {"unit": self.name}):
				has_history = True
		if has_history:
			frappe.throw(
				frappe._("لا يمكن حذف وحدة تحتوي على سجلات استخدام (عقود، إخلاء، مستحقات، أو تحصيلات)")
			)

		# Unit Attribute Values are owned/dependent data of the unit.
		# Delete them here (before Frappe's check_if_doc_is_linked runs)
		# so that attribute values don't block unit deletion.
		# This runs AFTER the business-dependency checks above, so if the
		# unit has contracts/dues/receipts/evictions, we throw before
		# touching any attribute values — no partial delete.
		attr_values = frappe.db.get_all(
			"Unit Attribute Value",
			filters={"unit": self.name},
			pluck="name",
		)
		for val_name in attr_values:
			frappe.delete_doc(
				"Unit Attribute Value", val_name,
				ignore_permissions=True, force=True,
			)

	def after_delete(self):
		update_building_counts(self.building)
