import frappe
from frappe.model.document import Document


class UnitTypeAttribute(Document):
	def validate(self):
		# Uniqueness is checked at the parent level (UnitType.validate)
		pass
