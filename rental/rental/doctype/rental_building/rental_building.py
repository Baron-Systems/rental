import frappe

from rental.rental.utils.account import get_current_rental_account, assert_account_access, is_system_manager


class RentalBuilding(frappe.model.document.Document):
	def before_validate(self):
		if not self.rental_account:
			account = get_current_rental_account()
			if account:
				self.rental_account = account

	def validate(self):
		if not self.rental_account and not is_system_manager():
			frappe.throw(frappe._("Rental Account is required."))
		assert_account_access(self)

		# Building name uniqueness per rental_account
		existing = frappe.db.exists(
			"Rental Building",
			{
				"building_name": self.building_name,
				"rental_account": self.rental_account,
				"name": ["!=", self.name or ""],
			},
		)
		if existing:
			frappe.throw(
				frappe._("اسم العقار مستخدم مسبقًا. يرجى إدخال اسم عقار مختلف.")
			)

		# Building data is read-only after creation (matches old app: PUT /api/buildings/[id] → 403)
		if not self.is_new():
			readonly_fields = ["building_name", "owner_name", "address", "latitude", "longitude"]
			for field in readonly_fields:
				if self.get(field) != self.get_db_value(field):
					frappe.throw(
						frappe._("تعديل بيانات العقار غير مسموح به. يمكنك تعطيل/تفعيل العقار أو حذفه إذا لم يُستخدم."),
						frappe.PermissionError,
					)

		# Block deactivation if any unit is active
		if not self.is_active:
			active_units = frappe.db.count(
				"Rental Unit",
				{"building": self.name, "is_active": 1},
			)
			if active_units:
				frappe.throw(
					frappe._("لا يمكن تعطيل العقار لأنه يحتوي على وحدات نشطة. قم بتعطيل الوحدات أولًا.")
				)

	def on_trash(self):
		# Order matches old app: contracts → dues → receipts → units
		# (floors are caught implicitly by FK restrict if no other data exists)
		if frappe.db.exists("DocType", "Lease Contract"):
			contract_count = frappe.db.count("Lease Contract", {"building": self.name})
			if contract_count:
				frappe.throw(
					frappe._("لا يمكن حذف عقار يحتوي على عقود. يمكنك تعطيله بدلاً من ذلك.")
				)

		if frappe.db.exists("DocType", "Rental Due"):
			dues_count = frappe.db.count("Rental Due", {"building": self.name})
			if dues_count:
				frappe.throw(
					frappe._("لا يمكن حذف عقار يحتوي على مستحقات. يمكنك تعطيله بدلاً من ذلك.")
				)

		if frappe.db.exists("DocType", "Rental Receipt"):
			receipts_count = frappe.db.count("Rental Receipt", {"building": self.name})
			if receipts_count:
				frappe.throw(
					frappe._("لا يمكن حذف عقار يحتوي على تحصيلات. يمكنك تعطيله بدلاً من ذلك.")
				)

		unit_count = frappe.db.count("Rental Unit", {"building": self.name})
		if unit_count:
			frappe.throw(
				frappe._("لا يمكن حذف عقار يحتوي على وحدات. يمكنك تعطيله بدلاً من ذلك.")
			)
