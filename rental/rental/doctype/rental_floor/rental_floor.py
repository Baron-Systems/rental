import frappe

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager
from rental.rental.services.unit_service import update_building_counts


class RentalFloor(frappe.model.document.Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		# Floor data is read-only after creation (matches old app: PUT /api/floors/[id] → 403 always)
		if not self.is_new():
			frappe.throw(
				frappe._("تعديل بيانات الطابق غير مسموح به. يمكنك حذف الطابق إذا لم يُستخدم."),
				frappe.PermissionError,
			)

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
						frappe._("Cannot add floor to a disabled building.")
					)

		existing = frappe.db.exists(
			"Rental Floor",
			{
				"building": self.building,
				"floor_name": self.floor_name,
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(
				frappe._("اسم الطابق مستخدم مسبقًا في هذا العقار. يرجى إدخال اسم طابق مختلف.")
			)

	def after_insert(self):
		update_building_counts(self.building)

	def on_trash(self):
		# Order matches old app: rented units → contracts on floor's units → any units
		rented_units = frappe.db.count("Rental Unit", {"floor": self.name, "status": "rented"})
		if rented_units:
			frappe.throw(
				frappe._("لا يمكن حذف طابق يحتوي على وحدات مؤجرة")
			)

		if frappe.db.exists("DocType", "Lease Contract"):
			contract_count = frappe.db.count(
				"Lease Contract",
				{"floor": self.name},
			)
			if not contract_count:
				# Also check contracts via unit.floor (units linked to this floor)
				unit_names = frappe.get_all("Rental Unit", {"floor": self.name}, pluck="name")
				if unit_names:
					contract_count = frappe.db.count(
						"Lease Contract",
						{"unit": ["in", unit_names]},
					)
			if contract_count:
				frappe.throw(
					frappe._("لا يمكن حذف طابق يحتوي على وحدات مؤجرة")
				)

		any_units = frappe.db.count("Rental Unit", {"floor": self.name})
		if any_units:
			frappe.throw(
				frappe._("لا يمكن حذف طابق يحتوي على وحدات")
			)

	def after_delete(self):
		update_building_counts(self.building)
