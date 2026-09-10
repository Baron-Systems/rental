"""Account-level configuration for Unit Type Attributes.

Each row represents an Attribute selected for a (rental_account, unit_type).
Row presence = Attribute is in the account's list for that Unit Type.
Row absence  = Attribute is not used by that account for that Unit Type.

There is no ``user`` dimension — all users in the same Rental Account share
the same configuration. There is no ``is_active`` — presence/absence is the
membership signal.
"""

from __future__ import annotations

import frappe
from frappe.model.document import Document


class AccountUnitTypeAttribute(Document):
	# ------------------------------------------------------------------
	# Validation
	# ------------------------------------------------------------------
	def validate(self) -> None:
		self._validate_unit_type_is_system()
		self._validate_attribute_is_system()
		self._validate_uniqueness()

	# ------------------------------------------------------------------
	# Hooks
	# ------------------------------------------------------------------
	def before_insert(self) -> None:
		# Enforce account isolation at the DB level — the current user must
		# belong to the same Rental Account set on this row.
		self._validate_account_membership()

	# ------------------------------------------------------------------
	# Internal helpers
	# ------------------------------------------------------------------
	def _validate_unit_type_is_system(self) -> None:
		if not self.unit_type:
			return
		is_system = frappe.db.get_value("Unit Type", self.unit_type, "is_system")
		if not is_system:
			frappe.throw(
				frappe._("Customization is only supported on System Unit Types."),
				frappe.ValidationError,
			)

	def _validate_attribute_is_system(self) -> None:
		if not self.attribute:
			return
		is_system = frappe.db.get_value("Unit Attribute", self.attribute, "is_system")
		if not is_system:
			frappe.throw(
				frappe._("Only System Attributes can be used in Account configuration."),
				frappe.ValidationError,
			)

	def _validate_uniqueness(self) -> None:
		if not (self.rental_account and self.unit_type and self.attribute):
			return
		filters = {
			"rental_account": self.rental_account,
			"unit_type": self.unit_type,
			"attribute": self.attribute,
		}
		if self.name:
			filters["name"] = ["!=", self.name]
		if frappe.db.exists("Account Unit Type Attribute", filters):
			frappe.throw(
				frappe._(
					"Duplicate Account Unit Type Attribute for account {0}, unit type {1}, attribute {2}."
				).format(self.rental_account, self.unit_type, self.attribute),
				frappe.ValidationError,
			)

	def _validate_account_membership(self) -> None:
		"""The current user must belong to the Rental Account on this row.

		System Manager bypasses this check.
		"""
		if frappe.flags.in_patch or frappe.flags.in_migrate:
			return
		if frappe.has_permission("Rental Account", "read", self.rental_account):
			return
		# Fall back to owner_user check for non-System-Manager callers
		owner_user = frappe.db.get_value("Rental Account", self.rental_account, "owner_user")
		current_user = frappe.session.user
		if current_user != "Administrator" and current_user != owner_user:
			frappe.throw(
				frappe._("You do not have permission to configure this Rental Account."),
				frappe.PermissionError,
			)
