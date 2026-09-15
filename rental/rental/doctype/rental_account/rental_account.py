import frappe
from frappe.model.document import Document
from frappe.model.docstatus import DocStatus


class RentalAccount(Document):
	def validate(self):
		self._validate_unique_owner_user()

	def _validate_unique_owner_user(self):
		existing = frappe.db.get_value(
			"Rental Account",
			{"owner_user": self.owner_user, "name": ["!=", self.name]},
			"name",
		)
		if existing:
			frappe.throw(
				frappe._("User {0} is already linked to Rental Account {1}").format(
					self.owner_user, existing
				),
				frappe.ValidationError,
			)

	def on_trash(self):
		"""Cascade delete all related data when Rental Account is deleted."""
		self._cascade_delete_related_data()

	def _cascade_delete_related_data(self):
		"""Delete all data related to this Rental Account in proper order."""
		# === المستوى 1: البيانات المالية (لا on_trash hooks) ===
		self._delete_docs_with_filter("Rental Receipt", {"rental_account": self.name})
		self._delete_docs_with_filter("Rental Due Waiver", {"rental_account": self.name})
		self._delete_docs_with_filter("Rental Due", {"rental_account": self.name})

		# === المستوى 2: بيانات العقود والتسويات (لا on_trash hooks) ===
		self._delete_docs_with_filter("Contract Cancellation Settlement", {"rental_account": self.name})
		self._delete_docs_with_filter("Rental Eviction", {"rental_account": self.name})

		# === المستوى 3: العقود (Protection-only) ===
		self._delete_docs_with_filter_and_flags("Lease Contract", {"rental_account": self.name})

		# === المستوى 4: المستأجرون (Protection-only) ===
		self._delete_docs_with_filter_and_flags("Rental Tenant", {"rental_account": self.name})

		# === المستوى 5: الوحدات (Protection + cleanup) ===
		# Rental Unit.on_trash سيحذف Unit Attribute Values تلقائياً
		# نحفظ قائمة الوحدات المحذوفة للـverification لاحقاً
		deleted_units = frappe.get_all("Rental Unit", {"rental_account": self.name}, pluck="name")
		self._delete_docs_with_filter_and_flags("Rental Unit", {"rental_account": self.name})

		# === المستوى 6: الطوابق والعقارات (Protection-only) ===
		self._delete_docs_with_filter_and_flags("Rental Floor", {"rental_account": self.name})
		self._delete_docs_with_filter_and_flags("Rental Building", {"rental_account": self.name})

		# === المستوى 7: التكوين المخصص للحساب ===
		if self.owner_user:
			self._delete_docs_with_filter("User Unit Preference", {"user": self.owner_user})

		# Verification: التأكد من عدم وجود orphan Unit Attribute Values
		# Rental Unit.on_trash مسؤول عن حذف القيم المرتبطة بالوحدة
		# نتحقق فقط من عدم وجود orphan records
		self._verify_no_orphan_unit_attribute_values(deleted_units)

		self._delete_docs_with_filter("Account Unit Type Attribute", {"rental_account": self.name})
		self._delete_docs_with_filter("Account Unit Type", {"rental_account": self.name})

		# === المستوى 8: Unit Types و Attributes (Protection-only) ===
		self._delete_docs_with_filter_and_flags("Unit Type", {"rental_account": self.name, "is_system": 0})
		self._delete_docs_with_filter_and_flags("Unit Attribute", {"rental_account": self.name, "is_system": 0})
		self._delete_docs_with_filter_and_flags("Rental Due Type", {"rental_account": self.name, "is_system": 0})

		# === المستوى 9: الإعدادات ===
		self._delete_docs_with_filter("Rental Settings", {"rental_account": self.name})

	def _delete_docs_with_filter(self, doctype, filters):
		"""Delete all documents matching the filter (for DocTypes without on_trash hooks)."""
		doc_names = frappe.get_all(doctype, filters=filters, pluck="name")
		for doc_name in doc_names:
			self._mark_cancelled_if_submitted(doctype, doc_name)
			frappe.delete_doc(
				doctype,
				doc_name,
				ignore_permissions=True,
				force=True
			)

	def _delete_docs_with_filter_and_flags(self, doctype, filters):
		"""Delete all documents with cascade delete flag (for DocTypes with on_trash hooks)."""
		doc_names = frappe.get_all(doctype, filters=filters, pluck="name")
		for doc_name in doc_names:
			self._mark_cancelled_if_submitted(doctype, doc_name)
			frappe.delete_doc(
				doctype,
				doc_name,
				ignore_permissions=True,
				force=True,
				flags={"cascade_delete_from_account": True}
			)

	def _mark_cancelled_if_submitted(self, doctype, doc_name):
		"""Mark a submitted document as cancelled so delete_doc can proceed.

		Only used inside the Rental Account cascade: the document is permanently
		deleted immediately after, so on_cancel business logic is not needed.
		Does not affect normal deletion of these documents outside the cascade.
		"""
		if frappe.get_meta(doctype).is_submittable and frappe.db.get_value(
			doctype, doc_name, "docstatus"
		) == DocStatus.SUBMITTED:
			frappe.db.set_value(
				doctype, doc_name, "docstatus", DocStatus.CANCELLED, update_modified=False
			)

	def _verify_no_orphan_unit_attribute_values(self, deleted_units):
		"""Verify that no orphan Unit Attribute Values exist after unit deletion."""
		if not deleted_units:
			return

		# التحقق من عدم وجود Unit Attribute Values تشير إلى الوحدات المحذوفة
		orphan_values = frappe.db.count(
			"Unit Attribute Value",
			{"unit": ["in", deleted_units]}
		)

		if orphan_values > 0:
			frappe.log_error(
				f"Found {orphan_values} orphan Unit Attribute Values after cascade delete of Rental Account {self.name}",
				"Rental Account Cascade Delete Verification"
			)
