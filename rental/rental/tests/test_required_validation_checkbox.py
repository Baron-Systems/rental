"""Tests for Required validation behavior, especially Check/Checkbox attributes."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestRequiredValidationCheckbox(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_configs = []
		cls._created_attrs = []

		cls.owner_a = cls._create_test_user("reqval@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("ReqVal A", cls.owner_a)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in cls._created_configs:
			if frappe.db.exists("Account Unit Type Attribute", name):
				frappe.delete_doc("Account Unit Type Attribute", name, force=True)
		for name in cls._created_attrs:
			if frappe.db.exists("Unit Attribute", name):
				frappe.delete_doc("Unit Attribute", name, force=True)
		for name in cls._created_accounts:
			if frappe.db.exists("Rental Account", name):
				frappe.delete_doc("Rental Account", name, force=True)
		for user in cls._created_users:
			if frappe.db.exists("User", user):
				frappe.delete_doc("User", user, force=True)
		super().tearDownClass()

	@classmethod
	def _create_test_user(cls, email, role):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"roles": [{"role": role}],
			"send_welcome_email": 0,
		})
		user.insert(ignore_permissions=True)
		update_password(user.name, "test12345")
		cls._created_users.append(email)
		return email

	@classmethod
	def _create_test_account(cls, name, owner_user):
		if frappe.db.exists("Rental Account", {"owner_user": owner_user}):
			frappe.delete_doc(
				"Rental Account",
				frappe.db.get_value("Rental Account", {"owner_user": owner_user}, "name"),
				force=True,
			)
		account = frappe.get_doc({
			"doctype": "Rental Account",
			"account_name": name,
			"owner_user": owner_user,
			"is_active": 1,
			"setup_completed": 1,
		})
		account.insert(ignore_permissions=True)
		cls._created_accounts.append(account.name)
		return account.name

	def _get_apartment(self):
		return frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name")

	def _create_test_attr(self, name, data_type):
		"""Create a test Unit Attribute (non-system)."""
		code = f"test_{frappe.utils.random_string(6).lower()}"
		doc = frappe.get_doc({
			"doctype": "Unit Attribute",
			"attribute_name": name,
			"code": code,
			"data_type": data_type,
			"is_system": 0,
			"is_active": 1,
		})
		doc.insert(ignore_permissions=True)
		self._created_attrs.append(doc.name)
		return doc.name

	def _set_account_config(self, account, unit_type, attrs):
		"""Replace account config with the given list of {attribute, is_required, display_order}."""
		for n in frappe.get_all("Account Unit Type Attribute",
			filters={"rental_account": account, "unit_type": unit_type}, pluck="name"):
			frappe.delete_doc("Account Unit Type Attribute", n, ignore_permissions=True)
		for idx, a in enumerate(attrs):
			doc = frappe.get_doc({
				"doctype": "Account Unit Type Attribute",
				"rental_account": account,
				"unit_type": unit_type,
				"attribute": a["attribute"],
				"is_required": a.get("is_required", 0),
				"display_order": idx,
			})
			doc.insert(ignore_permissions=True)
			self._created_configs.append(doc.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		for n in frappe.get_all("Account Unit Type Attribute",
			filters={"rental_account": self.account_a}, pluck="name"):
			frappe.delete_doc("Account Unit Type Attribute", n, ignore_permissions=True)

	def test_required_checkbox_value_1_passes(self):
		"""Required Check attribute with value 1 → PASS."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		check_attr = self._create_test_attr("مفروشة", "Check")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": check_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# Value = 1 (checked) should pass
		_validate_required_attributes(apartment, {check_attr: 1})

	def test_required_checkbox_value_0_passes(self):
		"""Required Check attribute with value 0 → PASS (0 is a valid choice)."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		check_attr = self._create_test_attr("مفروشة 2", "Check")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": check_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# Value = 0 (unchecked) should pass — 0 is a valid value for Check
		_validate_required_attributes(apartment, {check_attr: 0})

	def test_required_non_checkbox_missing_fails(self):
		"""Required Text attribute with no value → FAIL."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		text_attr = self._create_test_attr("ملاحظات", "Text")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": text_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# Missing value should fail
		with self.assertRaises(frappe.ValidationError):
			_validate_required_attributes(apartment, {})

	def test_required_non_checkbox_with_value_passes(self):
		"""Required Text attribute with a value → PASS."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		text_attr = self._create_test_attr("ملاحظات 2", "Text")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": text_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# Value present should pass
		_validate_required_attributes(apartment, {text_attr: "some value"})

	def test_required_integer_zero_fails(self):
		"""Required Integer attribute with value 0 → FAIL (0 is not a valid value for Integer)."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		int_attr = self._create_test_attr("عدد طوابق", "Integer")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": int_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# 0 for Integer should fail (0 is considered empty for non-Check types)
		with self.assertRaises(frappe.ValidationError):
			_validate_required_attributes(apartment, {int_attr: 0})

	def test_required_checkbox_missing_fails(self):
		"""Required Check attribute with no value at all → FAIL."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		check_attr = self._create_test_attr("مفروشة 3", "Check")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": check_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# Missing value (None) should fail
		with self.assertRaises(frappe.ValidationError):
			_validate_required_attributes(apartment, {})

	def test_required_checkbox_empty_string_fails(self):
		"""Required Check attribute with empty string → FAIL."""
		from rental.rental.api.property import _validate_required_attributes
		apartment = self._get_apartment()
		check_attr = self._create_test_attr("مفروشة 4", "Check")

		frappe.set_user("Administrator")
		self._set_account_config(self.account_a, apartment, [
			{"attribute": check_attr, "is_required": 1},
		])

		frappe.set_user(self.owner_a)
		# Empty string should fail
		with self.assertRaises(frappe.ValidationError):
			_validate_required_attributes(apartment, {check_attr: ""})
