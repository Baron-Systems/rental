import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password


class TestProperties(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._created_users = []
		cls._created_accounts = []
		cls._created_buildings = []
		cls._created_floors = []
		cls._created_units = []

		cls.owner_a = cls._create_test_user("owner_a@test.com", "Rental Property Owner")
		cls.owner_b = cls._create_test_user("owner_b@test.com", "Rental Property Owner")

		cls.account_a = cls._create_test_account("Account A", cls.owner_a)
		cls.account_b = cls._create_test_account("Account B", cls.owner_b)

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for name in cls._created_units:
			if frappe.db.exists("Rental Unit", name):
				frappe.delete_doc("Rental Unit", name, force=True)

		for name in cls._created_floors:
			if frappe.db.exists("Rental Floor", name):
				frappe.delete_doc("Rental Floor", name, force=True)

		for name in cls._created_buildings:
			if frappe.db.exists("Rental Building", name):
				frappe.delete_doc("Rental Building", name, force=True)

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

	def _create_building(self, user, account, name="Test Building"):
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": account,
			"building_name": name,
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._created_buildings.append(building.name)
		return building.name

	def _create_floor(self, user, building, floor_name="Floor 1", sort_order=0):
		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building, "rental_account")
		floor = frappe.get_doc({
			"doctype": "Rental Floor",
			"rental_account": account,
			"building": building,
			"floor_name": floor_name,
			"sort_order": sort_order,
		})
		floor.insert(ignore_permissions=True)
		self._created_floors.append(floor.name)
		return floor.name

	def _create_unit(self, user, building, unit_number="U-1", floor=None, **kwargs):
		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building, "rental_account")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account,
			"building": building,
			"unit_number": unit_number,
			"floor": floor,
			**kwargs,
		})
		unit.insert(ignore_permissions=True)
		self._created_units.append(unit.name)
		return unit.name

	# --- Building CRUD ---

	def test_building_crud(self):
		name = self._create_building(self.owner_a, self.account_a, "CRUD Building")

		frappe.set_user(self.owner_a)
		building = frappe.get_doc("Rental Building", name)
		self.assertEqual(building.building_name, "CRUD Building")
		self.assertEqual(building.rental_account, self.account_a)

		building.building_name = "Updated Building"
		building.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Rental Building", name, "building_name"), "Updated Building")

		frappe.delete_doc("Rental Building", name, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Rental Building", name))

	# --- Floor CRUD ---

	def test_floor_crud(self):
		building = self._create_building(self.owner_a, self.account_a, "Floor Test Building")
		floor = self._create_floor(self.owner_a, building, "Ground Floor")

		frappe.set_user(self.owner_a)
		floor_doc = frappe.get_doc("Rental Floor", floor)
		self.assertEqual(floor_doc.floor_name, "Ground Floor")
		self.assertEqual(floor_doc.rental_account, self.account_a)

		floor_doc.floor_name = "Updated Floor"
		floor_doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Rental Floor", floor, "floor_name"), "Updated Floor")

		frappe.delete_doc("Rental Floor", floor, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Rental Floor", floor))

	# --- Unit CRUD ---

	def test_unit_crud(self):
		building = self._create_building(self.owner_a, self.account_a, "Unit Test Building")
		unit = self._create_unit(self.owner_a, building, "U-101", unit_type="apartment", area=80.0)

		frappe.set_user(self.owner_a)
		unit_doc = frappe.get_doc("Rental Unit", unit)
		self.assertEqual(unit_doc.unit_number, "U-101")
		self.assertEqual(unit_doc.rental_account, self.account_a)
		self.assertEqual(unit_doc.status, "empty")

		unit_doc.unit_type = "Office"
		unit_doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Rental Unit", unit, "unit_type"), "Office")

		frappe.delete_doc("Rental Unit", unit, ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Rental Unit", unit))

	# --- Account isolation: Resource API list ---

	def test_account_isolation_list(self):
		building_a = self._create_building(self.owner_a, self.account_a, "Building A")
		building_b = self._create_building(self.owner_b, self.account_b, "Building B")

		frappe.set_user(self.owner_a)
		buildings = frappe.get_list("Rental Building", fields=["name", "building_name"])
		names = [b["name"] for b in buildings]
		self.assertIn(building_a, names)
		self.assertNotIn(building_b, names)

	# --- Account isolation: direct document access ---

	def test_account_isolation_direct_access(self):
		building_b = self._create_building(self.owner_b, self.account_b, "Building B Isolated")

		frappe.set_user(self.owner_a)
		has_perm = frappe.has_permission("Rental Building", doc=building_b, user=self.owner_a)
		self.assertFalse(has_perm)

	# --- Account isolation: link search ---

	def test_account_isolation_link_search(self):
		building_a = self._create_building(self.owner_a, self.account_a, "Link Search A")
		building_b = self._create_building(self.owner_b, self.account_b, "Link Search B")

		frappe.set_user(self.owner_a)
		results = frappe.get_list("Rental Building", fields=["name"])
		names = [r["name"] for r in results]
		self.assertIn(building_a, names)
		self.assertNotIn(building_b, names)

	# --- Cross-account link rejection: Unit -> Building ---

	def test_cross_account_unit_building_rejected(self):
		building_b = self._create_building(self.owner_b, self.account_b, "Cross Account B")

		frappe.set_user("Administrator")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": self.account_a,
			"building": building_b,
			"unit_number": "X-1",
		})
		with self.assertRaises(frappe.ValidationError):
			unit.insert(ignore_permissions=True)

	# --- Cross-account link rejection: Floor -> Building ---

	def test_cross_account_floor_building_rejected(self):
		building_b = self._create_building(self.owner_b, self.account_b, "Floor Cross B")

		frappe.set_user("Administrator")
		floor = frappe.get_doc({
			"doctype": "Rental Floor",
			"rental_account": self.account_a,
			"building": building_b,
			"floor_name": "Test",
		})
		with self.assertRaises(frappe.ValidationError):
			floor.insert(ignore_permissions=True)

	# --- Unique floor name within building ---

	def test_unique_floor_name(self):
		building = self._create_building(self.owner_a, self.account_a, "Unique Floor Building")
		self._create_floor(self.owner_a, building, "First Floor")

		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building, "rental_account")
		floor = frappe.get_doc({
			"doctype": "Rental Floor",
			"rental_account": account,
			"building": building,
			"floor_name": "First Floor",
		})
		with self.assertRaises(frappe.ValidationError):
			floor.insert(ignore_permissions=True)

	# --- Unique unit number within building ---

	def test_unique_unit_number(self):
		building = self._create_building(self.owner_a, self.account_a, "Unique Unit Building")
		self._create_unit(self.owner_a, building, "U-1")

		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building, "rental_account")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account,
			"building": building,
			"unit_number": "U-1",
		})
		with self.assertRaises(frappe.ValidationError):
			unit.insert(ignore_permissions=True)

	# --- Optional floor ---

	def test_optional_floor(self):
		building = self._create_building(self.owner_a, self.account_a, "Optional Floor Building")
		unit = self._create_unit(self.owner_a, building, "U-NF", floor=None)

		frappe.set_user(self.owner_a)
		unit_doc = frappe.get_doc("Rental Unit", unit)
		self.assertIsNone(unit_doc.floor)
		self.assertEqual(unit_doc.status, "empty")

	# --- Floor-building mismatch ---

	def test_floor_building_mismatch(self):
		building1 = self._create_building(self.owner_a, self.account_a, "Mismatch B1")
		building2 = self._create_building(self.owner_a, self.account_a, "Mismatch B2")
		floor = self._create_floor(self.owner_a, building1, "Floor B1")

		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building2, "rental_account")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account,
			"building": building2,
			"floor": floor,
			"unit_number": "U-MM",
		})
		with self.assertRaises(frappe.ValidationError):
			unit.insert(ignore_permissions=True)

	# --- Deletion restrictions ---

	def test_cannot_delete_building_with_floors(self):
		building = self._create_building(self.owner_a, self.account_a, "Del Floor Building")
		self._create_floor(self.owner_a, building, "F1")

		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Rental Building", building, ignore_permissions=True)

	def test_cannot_delete_building_with_units(self):
		building = self._create_building(self.owner_a, self.account_a, "Del Unit Building")
		self._create_unit(self.owner_a, building, "U-D1")

		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Rental Building", building, ignore_permissions=True)

	def test_cannot_delete_floor_with_units(self):
		building = self._create_building(self.owner_a, self.account_a, "Del Floor Unit Building")
		floor = self._create_floor(self.owner_a, building, "F1")
		self._create_unit(self.owner_a, building, "U-F1", floor=floor)

		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("Rental Floor", floor, ignore_permissions=True)

	# --- Disabled building ---

	def test_disabled_building_rejects_new_floor(self):
		building = self._create_building(self.owner_a, self.account_a, "Disabled Building")

		frappe.set_user("Administrator")
		frappe.db.set_value("Rental Building", building, "is_active", 0)

		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building, "rental_account")
		floor = frappe.get_doc({
			"doctype": "Rental Floor",
			"rental_account": account,
			"building": building,
			"floor_name": "New Floor",
		})
		with self.assertRaises(frappe.ValidationError):
			floor.insert(ignore_permissions=True)

	def test_disabled_building_rejects_new_unit(self):
		building = self._create_building(self.owner_a, self.account_a, "Disabled Unit Building")

		frappe.set_user("Administrator")
		frappe.db.set_value("Rental Building", building, "is_active", 0)

		frappe.set_user("Administrator")
		account = frappe.db.get_value("Rental Building", building, "rental_account")
		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account,
			"building": building,
			"unit_number": "U-NEW",
		})
		with self.assertRaises(frappe.ValidationError):
			unit.insert(ignore_permissions=True)

	# --- Building counts ---

	def test_building_counts_updated_on_floor_insert(self):
		building = self._create_building(self.owner_a, self.account_a, "Counts Building")
		self._create_floor(self.owner_a, building, "F1")
		self._create_floor(self.owner_a, building, "F2")

		count = frappe.db.get_value("Rental Building", building, "floors_count")
		self.assertEqual(count, 2)

	def test_building_counts_updated_on_unit_insert(self):
		building = self._create_building(self.owner_a, self.account_a, "Unit Counts Building")
		self._create_unit(self.owner_a, building, "U-C1")
		self._create_unit(self.owner_a, building, "U-C2")

		count = frappe.db.get_value("Rental Building", building, "units_count")
		self.assertEqual(count, 2)

	def test_building_counts_updated_on_delete(self):
		building = self._create_building(self.owner_a, self.account_a, "Del Counts Building")
		floor = self._create_floor(self.owner_a, building, "F1")
		self._create_unit(self.owner_a, building, "U-DC1")

		frappe.set_user("Administrator")
		frappe.delete_doc("Rental Unit", self._created_units[-1], ignore_permissions=True)
		self._created_units.pop()

		unit_count = frappe.db.get_value("Rental Building", building, "units_count")
		self.assertEqual(unit_count, 0)

		frappe.delete_doc("Rental Floor", floor, ignore_permissions=True)
		self._created_floors.remove(floor)

		floor_count = frappe.db.get_value("Rental Building", building, "floors_count")
		self.assertEqual(floor_count, 0)

	# --- Unit status engine ---

	def test_unit_status_empty_by_default(self):
		building = self._create_building(self.owner_a, self.account_a, "Status Empty Building")
		unit = self._create_unit(self.owner_a, building, "U-S1")

		status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(status, "empty")

	def test_unit_status_unavailable_when_manually_set(self):
		building = self._create_building(self.owner_a, self.account_a, "Status Unavail Building")
		unit = self._create_unit(self.owner_a, building, "U-S2")

		frappe.set_user("Administrator")
		unit_doc = frappe.get_doc("Rental Unit", unit)
		unit_doc.is_manually_unavailable = 1
		unit_doc.save(ignore_permissions=True)

		status = frappe.db.get_value("Rental Unit", unit, "status")
		self.assertEqual(status, "unavailable")

	def test_unit_status_back_to_empty_when_unchecked(self):
		building = self._create_building(self.owner_a, self.account_a, "Status Back Building")
		unit = self._create_unit(self.owner_a, building, "U-S3")

		frappe.set_user("Administrator")
		unit_doc = frappe.get_doc("Rental Unit", unit)
		unit_doc.is_manually_unavailable = 1
		unit_doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Rental Unit", unit, "status"), "unavailable")

		unit_doc.is_manually_unavailable = 0
		unit_doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Rental Unit", unit, "status"), "empty")
