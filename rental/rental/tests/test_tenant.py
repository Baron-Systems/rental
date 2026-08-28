"""Tests for Rental Tenant CRUD, validation, and delete rules.

Source: TENANTS_MIGRATION_SPEC §37.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTenant(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_tenants = []
		cls._created_users = []
		cls._created_accounts = []

		cls.admin_user = "Administrator"
		cls.owner_a = cls._create_test_user("tenant_owner_a@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Tenant Test Account A", cls.owner_a)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for tenant_name in cls._created_tenants:
			if frappe.db.exists("Rental Tenant", tenant_name):
				frappe.delete_doc("Rental Tenant", tenant_name, force=True)

		for account_name in cls._created_accounts:
			if frappe.db.exists("Rental Account", account_name):
				frappe.delete_doc("Rental Account", account_name, force=True)

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
			"first_name": "Test",
			"last_name": "Owner",
			"roles": [{"role": role}],
			"send_welcome_email": 0,
		})
		user.insert(ignore_permissions=True)
		cls._created_users.append(email)
		return email

	@classmethod
	def _create_test_account(cls, name, owner):
		if frappe.db.exists("Rental Account", name):
			frappe.delete_doc("Rental Account", name, force=True)
		account = frappe.get_doc({
			"doctype": "Rental Account",
			"account_name": name,
			"owner_user": owner,
			"is_active": 1,
		})
		account.insert(ignore_permissions=True)
		cls._created_accounts.append(name)
		return name

	def _create_tenant(self, full_name="Test Tenant", national_id=None, phone=None):
		"""Create a tenant as owner_a."""
		frappe.set_user(self.owner_a)
		doc = frappe.get_doc({
			"doctype": "Rental Tenant",
			"full_name": full_name,
			"national_id": national_id,
			"phone": phone,
		})
		doc.insert(ignore_permissions=True)
		self._created_tenants.append(doc.name)
		return doc

	# ---- TEN-BE-001: full_name required ----

	def test_create_tenant_without_full_name_fails(self):
		"""TEN-BE-001: full_name is required."""
		frappe.set_user(self.owner_a)
		doc = frappe.get_doc({
			"doctype": "Rental Tenant",
			"national_id": "12345",
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	# ---- TEN-BE-001: full_name max 100 ----

	def test_create_tenant_full_name_exceeds_100_fails(self):
		"""TEN-BE-001: full_name cannot exceed 100 characters."""
		frappe.set_user(self.owner_a)
		doc = frappe.get_doc({
			"doctype": "Rental Tenant",
			"full_name": "A" * 101,
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	# ---- TEN-BE-002: national_id optional ----

	def test_create_tenant_without_national_id_allowed(self):
		"""TEN-BE-002: national_id is optional."""
		doc = self._create_tenant(full_name="No ID Tenant")
		self.assertTrue(doc.name)
		self.assertIsNone(doc.national_id)

	# ---- TEN-BE-002: national_id max 50 ----

	def test_create_tenant_national_id_exceeds_50_fails(self):
		"""TEN-BE-002: national_id cannot exceed 50 characters."""
		frappe.set_user(self.owner_a)
		doc = frappe.get_doc({
			"doctype": "Rental Tenant",
			"full_name": "Long ID Tenant",
			"national_id": "1" * 51,
		})
		self.assertRaises(frappe.ValidationError, doc.insert)

	# ---- TEN-BE-002: no uniqueness on national_id ----

	def test_duplicate_national_id_allowed(self):
		"""TEN-BE-002: duplicate national_id in same account is allowed."""
		t1 = self._create_tenant(full_name="Tenant One", national_id="ID999")
		t2 = self._create_tenant(full_name="Tenant Two", national_id="ID999")
		self.assertTrue(t1.name)
		self.assertTrue(t2.name)
		self.assertNotEqual(t1.name, t2.name)

	# ---- TEN-BE-003: full_name immutable ----

	def test_update_full_name_rejected(self):
		"""TEN-BE-003: full_name cannot be changed after creation."""
		doc = self._create_tenant(full_name="Original Name")
		doc.full_name = "Changed Name"
		self.assertRaises(frappe.ValidationError, doc.save)

	# ---- TEN-BE-003: national_id immutable ----

	def test_update_national_id_rejected(self):
		"""TEN-BE-003: national_id cannot be changed after creation."""
		doc = self._create_tenant(full_name="ID Test", national_id="ORIG123")
		doc.national_id = "CHANGED456"
		self.assertRaises(frappe.ValidationError, doc.save)

	# ---- TEN-UX-008: phone/workplace/guarantor editable ----

	def test_update_phone_allowed(self):
		"""TEN-UX-008: phone is editable."""
		doc = self._create_tenant(full_name="Phone Test", phone="0512345678")
		doc.phone = "0598765432"
		doc.save()
		self.assertEqual(doc.phone, "0598765432")

	def test_update_workplace_allowed(self):
		"""TEN-UX-008: workplace is editable."""
		doc = self._create_tenant(full_name="Workplace Test", workplace="Old Job")
		doc.workplace = "New Job"
		doc.save()
		self.assertEqual(doc.workplace, "New Job")

	# ---- TEN-BE-006: is_active default ----

	def test_is_active_defaults_to_true(self):
		"""TEN-BE-006: is_active defaults to 1."""
		doc = self._create_tenant(full_name="Active Default Test")
		self.assertEqual(int(doc.is_active), 1)

	# ---- TEN-BE-006: is_active immutable via validate ----

	def test_is_active_cannot_be_changed(self):
		"""TEN-BE-006: is_active cannot be changed after creation."""
		doc = self._create_tenant(full_name="Active Lock Test")
		doc.is_active = 0
		self.assertRaises(frappe.ValidationError, doc.save)

	# ---- TEN-ARCH-001: rental_account server-set ----

	def test_rental_account_set_automatically(self):
		"""TEN-ARCH-001: rental_account is set automatically on insert."""
		doc = self._create_tenant(full_name="Account Test")
		self.assertEqual(doc.rental_account, self.account_a)

	# ---- TEN-BE-004: delete unused tenant allowed ----

	def test_delete_unused_tenant_allowed(self):
		"""TEN-BE-004: tenant with no dependents can be deleted."""
		doc = self._create_tenant(full_name="Delete Me")
		name = doc.name
		frappe.delete_doc("Rental Tenant", name)
		self.assertFalse(frappe.db.exists("Rental Tenant", name))
		if name in self._created_tenants:
			self._created_tenants.remove(name)

	# ---- TEN-BE-015: search ----

	def test_search_by_full_name(self):
		"""TEN-BE-015: search contains on full_name."""
		self._create_tenant(full_name="UniqueSearchName XYZ")
		from rental.rental.api.tenant import get_tenants
		frappe.set_user(self.owner_a)
		result = get_tenants(search="UniqueSearchName")
		names = [t["name"] for t in result["tenants"]]
		self.assertTrue(any("UniqueSearchName" in t for t in [frappe.db.get_value("Rental Tenant", n, "full_name") for n in names]))

	def test_search_by_national_id(self):
		"""TEN-BE-015: search contains on national_id."""
		self._create_tenant(full_name="ID Search Test", national_id="SEARCHID123")
		from rental.rental.api.tenant import get_tenants
		frappe.set_user(self.owner_a)
		result = get_tenants(search="SEARCHID123")
		self.assertTrue(len(result["tenants"]) > 0)

	def test_search_by_phone(self):
		"""TEN-BE-015: search contains on phone."""
		self._create_tenant(full_name="Phone Search Test", phone="0555998877")
		from rental.rental.api.tenant import get_tenants
		frappe.set_user(self.owner_a)
		result = get_tenants(search="0555998877")
		self.assertTrue(len(result["tenants"]) > 0)

	# ---- Simple mode ----

	def test_simple_mode_returns_limited_fields(self):
		"""TEN-UX-018: simple mode returns name, full_name, national_id, phone only."""
		self._create_tenant(full_name="Simple Mode Test", national_id="SIMPLE1", phone="0511111111")
		from rental.rental.api.tenant import get_tenants
		frappe.set_user(self.owner_a)
		result = get_tenants(simple=1, limit=20)
		self.assertTrue(isinstance(result, list))
		if result:
			# Should not have balance fields
			self.assertNotIn("totalDues", result[0])
			self.assertNotIn("balance", result[0])

	# ---- Print mode ----

	def test_print_mode_ignores_pagination(self):
		"""TEN-UX-017: print mode returns all tenants without pagination."""
		self._create_tenant(full_name="Print Mode Test 1")
		self._create_tenant(full_name="Print Mode Test 2")
		from rental.rental.api.tenant import get_tenants
		frappe.set_user(self.owner_a)
		result = get_tenants(print=1)
		self.assertNotIn("pagination", result)
		self.assertIn("tenants", result)
		self.assertIn("total", result)
