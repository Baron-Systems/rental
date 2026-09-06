"""Tests for the financial trend API (dashboard 'التدفقات المالية' chart).

Covers:
  - Last 6 calendar months are returned (no more, no less).
  - Months with no activity return 0 (never dropped from the series).
  - Approved dues (docstatus=1) counted; Draft/Cancelled excluded.
  - Active waivers subtracted from dues.
  - Approved receipts (docstatus=1) counted; Cancelled excluded.
  - Archived contracts excluded from both dues and receipts.
  - Current month capped at today (future dates in current month excluded).
  - Account/currency isolation: no cross-account aggregation.
  - Permission validation: regular user cannot query another account;
    System Manager must pass an explicit account.

Isolation strategy:
  FrappeTestCase commits the DB at setUpClass and only rolls back at
  tearDownClass — there is NO per-test rollback.  To prevent financial
  records from accumulating across tests (which would corrupt aggregate
  assertions), each test gets its own contract + per-test cleanup in
  tearDown that cancels and deletes every due/receipt/waiver/contract
  the test created.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password
from datetime import date, timedelta


class TestFinancialTrend(FrappeTestCase):
	# ---- Class-level setup: create users + accounts (shared, no financial data) ----

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._cls_users = []
		cls._cls_accounts = []

		cls.owner_a = cls._create_test_user("trend_owner_a@test.com", "Rental Property Owner")
		cls.account_a = cls._create_test_account("Trend Account A", cls.owner_a, "JOD")

		cls.owner_b = cls._create_test_user("trend_owner_b@test.com", "Rental Property Owner")
		cls.account_b = cls._create_test_account("Trend Account B", cls.owner_b, "ILS")

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")

		for name in cls._cls_accounts:
			if frappe.db.exists("Rental Account", name):
				try:
					frappe.delete_doc("Rental Account", name, force=True)
				except Exception:
					frappe.db.delete("Rental Account", name)

		for user in cls._cls_users:
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
		cls._cls_users.append(email)
		return email

	@classmethod
	def _create_test_account(cls, name, owner_user, currency="JOD"):
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
		cls._cls_accounts.append(account.name)

		if not frappe.db.exists("Rental Settings", {"rental_account": account.name}):
			settings = frappe.get_doc({
				"doctype": "Rental Settings",
				"rental_account": account.name,
				"landlord_type": "person",
				"landlord_name": "Trend Landlord",
				"landlord_id": "9999999999",
				"landlord_phone": "0555-000-000",
				"landlord_address": "Test Address",
				"currency": currency,
			})
			settings.insert(ignore_permissions=True)

		return account.name

	# ---- Per-test setup/teardown: full isolation ----

	def setUp(self):
		"""Reset per-test tracking lists. Each test creates its own contract."""
		frappe.set_user("Administrator")
		self._test_buildings = []
		self._test_units = []
		self._test_tenants = []
		self._test_contracts = []
		self._test_dues = []
		self._test_receipts = []
		self._test_waivers = []
		self._used_auto_dues = []

	def tearDown(self):
		"""Cancel and delete every financial record this test created.

		This is the critical isolation mechanism: FrappeTestCase does NOT
		rollback per-test, so without this cleanup, dues/receipts from
		one test would pollute the aggregate sums of subsequent tests.

		IMPORTANT: approve_contract(generate_dues=1) creates auto_contract
		dues that are NOT individually tracked in self._test_dues (only the
		ones adjusted by _create_due are).  So we must cancel/delete ALL
		dues/receipts/waivers belonging to the test contracts, not just the
		tracked ones.
		"""
		frappe.set_user("Administrator")

		# Gather ALL due names for the test contracts (tracked + untracked auto)
		all_due_names = set(self._test_dues)
		for contract in self._test_contracts:
			contract_dues = frappe.get_all(
				"Rental Due",
				filters={"contract": contract},
				pluck="name",
			)
			all_due_names.update(contract_dues)

		# Waivers first (depend on dues) — all waivers on those dues
		waiver_names = set(self._test_waivers)
		if all_due_names:
			linked_waivers = frappe.get_all(
				"Rental Due Waiver",
				filters={"due": ["in", list(all_due_names)]},
				pluck="name",
			)
			waiver_names.update(linked_waivers)

		for name in waiver_names:
			if frappe.db.exists("Rental Due Waiver", name):
				try:
					frappe.delete_doc("Rental Due Waiver", name, force=True)
				except Exception:
					frappe.db.delete("Rental Due Waiver", name)

		# Receipts for test contracts (tracked + untracked)
		all_receipt_names = set(self._test_receipts)
		for contract in self._test_contracts:
			contract_receipts = frappe.get_all(
				"Rental Receipt",
				filters={"contract": contract},
				pluck="name",
			)
			all_receipt_names.update(contract_receipts)

		for name in all_receipt_names:
			if frappe.db.exists("Rental Receipt", name):
				try:
					doc = frappe.get_doc("Rental Receipt", name)
					if doc.docstatus == 1:
						doc.cancellation_reason = "Test cleanup"
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Receipt", name, force=True)
				except Exception:
					pass

		# Dues (all for test contracts, not just tracked ones)
		for name in all_due_names:
			if frappe.db.exists("Rental Due", name):
				try:
					doc = frappe.get_doc("Rental Due", name)
					if doc.docstatus == 1:
						doc.cancellation_reason = "Test cleanup"
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Rental Due", name, force=True)
				except Exception:
					pass

		# Contracts (clear archive flag first so cancel works)
		for name in self._test_contracts:
			if frappe.db.exists("Lease Contract", name):
				try:
					frappe.db.set_value("Lease Contract", name, "is_archived", 0, update_modified=False)
					doc = frappe.get_doc("Lease Contract", name)
					if doc.docstatus == 1:
						doc.cancel()
				except Exception:
					pass
				try:
					frappe.delete_doc("Lease Contract", name, force=True)
				except Exception:
					frappe.db.delete("Lease Contract", name)

		# Tenants
		for name in self._test_tenants:
			if frappe.db.exists("Rental Tenant", name):
				try:
					frappe.delete_doc("Rental Tenant", name, force=True)
				except Exception:
					frappe.db.delete("Rental Tenant", name)

		# Units
		for name in self._test_units:
			if frappe.db.exists("Rental Unit", name):
				try:
					frappe.delete_doc("Rental Unit", name, force=True)
				except Exception:
					frappe.db.delete("Rental Unit", name)

		# Buildings
		for name in self._test_buildings:
			if frappe.db.exists("Rental Building", name):
				try:
					frappe.delete_doc("Rental Building", name, force=True)
				except Exception:
					frappe.db.delete("Rental Building", name)

	# ---- Helpers (create docs, track in per-test lists) ----

	def _setup_contract(self, account, rent=500, start_offset=-60, end_offset=30):
		"""Create building, unit, tenant, and approved contract for the given account.

		Uses generate_dues=1 so auto_contract dues exist for _create_due to reuse.
		"""
		frappe.set_user("Administrator")
		building = frappe.get_doc({
			"doctype": "Rental Building",
			"rental_account": account,
			"building_name": f"Trend Bldg {frappe.utils.random_string(5)}",
			"address": "Test Address",
		})
		building.insert(ignore_permissions=True)
		self._test_buildings.append(building.name)

		unit = frappe.get_doc({
			"doctype": "Rental Unit",
			"rental_account": account,
			"building": building.name,
			"unit_number": f"U-{frappe.utils.random_string(4)}",
			"unit_type": frappe.db.get_value("Unit Type", {"code": "apartment", "is_system": 1}, "name"),
		})
		unit.insert(ignore_permissions=True)
		self._test_units.append(unit.name)

		tenant = frappe.get_doc({
			"doctype": "Rental Tenant",
			"rental_account": account,
			"full_name": f"Trend Tenant {frappe.utils.random_string(5)}",
			"phone": "12345678",
		})
		tenant.insert(ignore_permissions=True)
		self._test_tenants.append(tenant.name)

		start = frappe.utils.add_days(frappe.utils.today(), start_offset)
		end = frappe.utils.add_days(frappe.utils.today(), end_offset)
		contract = frappe.get_doc({
			"doctype": "Lease Contract",
			"rental_account": account,
			"tenant": tenant.name,
			"building": building.name,
			"unit": unit.name,
			"start_date": start,
			"end_date": end,
			"rent_amount": rent,
			"payment_frequency": "monthly",
			"commitment_timing": "start",
			"status": "draft",
		})
		contract.insert(ignore_permissions=True)
		self._test_contracts.append(contract.name)

		from rental.rental.api.contract import approve_contract
		approve_contract(contract.name, generate_dues=1)

		return {
			"building": building.name,
			"unit": unit.name,
			"tenant": tenant.name,
			"contract": contract.name,
		}

	def _get_auto_due(self, contract, skip=None):
		"""Return the next unused auto-generated approved due for a contract."""
		filters = {"contract": contract, "docstatus": 1, "source_type": "auto_contract"}
		if skip:
			filters["name"] = ["not in", skip]
		due = frappe.get_all(
			"Rental Due",
			filters=filters,
			fields=["name"],
			order_by="due_date asc",
			limit=1,
		)
		return due[0]["name"] if due else None

	def _create_due(self, account, contract, tenant, amount, due_date):
		"""Adjust an auto-generated due to the requested amount/due_date.

		Rental Due of type 'rent' cannot be created manually (business rule),
		so we reuse an auto_contract due and set its amount/date directly
		via db.set_value (bypassing the 'auto_contract cannot be edited' guard).
		Returns the due name.
		"""
		frappe.set_user("Administrator")
		due_name = self._get_auto_due(contract, skip=self._used_auto_dues)
		if not due_name:
			# No unused auto due — create another contract to get one
			ctx2 = self._setup_contract(account, rent=amount)
			due_name = self._get_auto_due(ctx2["contract"])
		self._used_auto_dues.append(due_name)
		frappe.db.set_value("Rental Due", due_name, {
			"due_date": due_date,
			"transaction_date": due_date,
			"amount": amount,
		}, update_modified=False)
		self._test_dues.append(due_name)
		return due_name

	def _create_draft_due(self, account, contract, tenant, amount, due_date):
		"""Create a Rental Due but leave it as Draft (docstatus=0).

		Uses a non-rent due type (additional) which CAN be created manually.
		"""
		frappe.set_user("Administrator")
		# Find a non-rent, active due type
		dt = frappe.db.get_value(
			"Rental Due Type",
			{"is_active": 1, "due_type_code": ["!=", "rent"]},
			"name",
		)
		if not dt:
			self.skipTest("No non-rent due type available for draft test")
		due = frappe.get_doc({
			"doctype": "Rental Due",
			"rental_account": account,
			"contract": contract,
			"tenant": tenant,
			"due_type": dt,
			"transaction_date": due_date,
			"due_date": due_date,
			"amount": amount,
			"source_type": "manual_contract",
		})
		due.insert(ignore_permissions=True)
		self._test_dues.append(due.name)
		return due.name

	def _create_receipt(self, account, contract, tenant, amount, receipt_date):
		"""Create and submit a Rental Receipt with an explicit receipt_date."""
		frappe.set_user("Administrator")
		receipt = frappe.get_doc({
			"doctype": "Rental Receipt",
			"rental_account": account,
			"contract": contract,
			"tenant": tenant,
			"receipt_date": receipt_date,
			"amount": amount,
			"payment_method": "cash",
		})
		receipt.insert(ignore_permissions=True)
		receipt.submit()
		self._test_receipts.append(receipt.name)
		return receipt.name

	def _create_waiver(self, due_name, amount):
		"""Create an active waiver on a due."""
		frappe.set_user("Administrator")
		waiver = frappe.get_doc({
			"doctype": "Rental Due Waiver",
			"due": due_name,
			"amount": amount,
			"reason": "Test waiver",
			"status": "active",
		})
		waiver.insert(ignore_permissions=True)
		self._test_waivers.append(waiver.name)
		return waiver.name

	def _current_month_label(self):
		today = frappe.utils.today()
		m = int(today.split("-")[1])
		months_ar = [
			"يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
			"يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
		]
		return months_ar[m - 1]

	def _current_month_row(self, result):
		"""Extract the current-month row from a trend result."""
		label = self._current_month_label()
		rows = [m for m in result["months"] if m["name"] == label]
		self.assertTrue(rows, f"Current month '{label}' not found in trend")
		return rows[0]

	# ---- Tests ----

	def test_returns_exactly_six_months(self):
		"""The trend must always return exactly 6 months, even with no data."""
		from rental.rental.api.dashboard import get_financial_trend
		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		self.assertEqual(len(result["months"]), 6)
		self.assertEqual(result["account"], self.account_a)
		self.assertEqual(result["currency"], "JOD")

	def test_zero_months_return_zero_not_dropped(self):
		"""Months with no activity must show dues=0 and receipts=0, not be omitted."""
		from rental.rental.api.dashboard import get_financial_trend
		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		for m in result["months"]:
			self.assertIn("dues", m)
			self.assertIn("receipts", m)
			self.assertEqual(m["dues"], 0)
			self.assertEqual(m["receipts"], 0)

	def test_approved_dues_counted_by_due_date(self):
		"""An approved due in the current month appears in that month's dues."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 1000, frappe.utils.today())

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 1000)

	def test_draft_dues_excluded(self):
		"""Draft dues (docstatus=0) must not be counted."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		self._create_draft_due(self.account_a, ctx["contract"], ctx["tenant"], 999, frappe.utils.today())
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 500, frappe.utils.today())

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		# Only the approved 500 counts, not the draft 999
		self.assertEqual(current["dues"], 500)

	def test_cancelled_dues_excluded(self):
		"""Cancelled dues (docstatus=2) must not be counted."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		due_name = self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 800, frappe.utils.today())
		# Cancel it (requires cancellation_reason)
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Rental Due", due_name)
		doc.cancellation_reason = "Test cancel"
		doc.cancel()

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 0)

	def test_active_waivers_subtracted(self):
		"""Active waivers reduce the net dues for the month."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		due_name = self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 1000, frappe.utils.today())
		self._create_waiver(due_name, 300)

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 700)  # 1000 - 300

	def test_approved_receipts_counted_by_receipt_date(self):
		"""An approved receipt in the current month appears in that month's receipts."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 1000, frappe.utils.today())
		self._create_receipt(self.account_a, ctx["contract"], ctx["tenant"], 600, frappe.utils.today())

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["receipts"], 600)

	def test_cancelled_receipts_excluded(self):
		"""Cancelled receipts (docstatus=2) must not be counted."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 1000, frappe.utils.today())
		rcpt_name = self._create_receipt(self.account_a, ctx["contract"], ctx["tenant"], 500, frappe.utils.today())
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Rental Receipt", rcpt_name)
		doc.cancellation_reason = "Test cancel"
		doc.cancel()

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["receipts"], 0)

	def test_archived_contracts_excluded(self):
		"""Dues and receipts of archived contracts must be excluded."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 1000, frappe.utils.today())
		self._create_receipt(self.account_a, ctx["contract"], ctx["tenant"], 500, frappe.utils.today())

		# Archive the contract directly (bypass readiness for test speed)
		frappe.set_user("Administrator")
		frappe.db.set_value("Lease Contract", ctx["contract"], "is_archived", 1, update_modified=False)

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 0)
		self.assertEqual(current["receipts"], 0)

	def test_current_month_capped_at_today(self):
		"""A due dated tomorrow (in current month) must NOT be counted."""
		from rental.rental.api.dashboard import get_financial_trend
		today = frappe.utils.today()
		today_date = date.fromisoformat(today)
		tomorrow = today_date + timedelta(days=1)

		# Only test if tomorrow is still in the same calendar month
		if tomorrow.month != today_date.month:
			self.skipTest("Tomorrow crosses month boundary — cannot test current-month cutoff")

		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 1000, str(tomorrow))

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 0)  # tomorrow excluded

	def test_months_are_chronological(self):
		"""Months must be ordered oldest → newest."""
		from rental.rental.api.dashboard import get_financial_trend
		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		# Verify by (year, month) ascending
		keys = [(m["year"], m["month"]) for m in result["months"]]
		self.assertEqual(keys, sorted(keys))

	def test_account_isolation_no_cross_account_aggregation(self):
		"""Dues in account A must NOT appear in account B's trend."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx_a = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx_a["contract"], ctx_a["tenant"], 1000, frappe.utils.today())

		# Account B should see 0 for the current month
		frappe.set_user(self.owner_b)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 0)
		self.assertEqual(result["currency"], "ILS")

		# Account A should see 1000
		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 1000)
		self.assertEqual(result["currency"], "JOD")

	def test_regular_user_cannot_query_other_account(self):
		"""A regular user passing another account's name must get PermissionError."""
		from rental.rental.api.dashboard import get_financial_trend
		frappe.set_user(self.owner_a)
		with self.assertRaises(frappe.PermissionError):
			get_financial_trend(account=self.account_b)

	def test_system_manager_without_account_raises(self):
		"""System Manager must pass an explicit account."""
		from rental.rental.api.dashboard import get_financial_trend
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.ValidationError):
			get_financial_trend()

	def test_system_manager_with_explicit_account(self):
		"""System Manager can query a specific account's trend."""
		from rental.rental.api.dashboard import get_financial_trend
		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 2000, frappe.utils.today())

		frappe.set_user("Administrator")
		result = get_financial_trend(account=self.account_a)
		self.assertEqual(result["account"], self.account_a)
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 2000)

	def test_past_month_dues_appear_in_correct_month(self):
		"""A due dated 2 months ago must appear in that month, not the current one."""
		from rental.rental.api.dashboard import get_financial_trend
		today = date.fromisoformat(frappe.utils.today())
		# Go back 2 months
		pm = today.month - 2
		py = today.year
		while pm < 1:
			pm += 12
			py -= 1
		past_date = date(py, pm, 15)

		ctx = self._setup_contract(self.account_a)
		self._create_due(self.account_a, ctx["contract"], ctx["tenant"], 750, str(past_date))

		frappe.set_user(self.owner_a)
		result = get_financial_trend()
		# Find the month matching past_date
		target = [mo for mo in result["months"] if mo["year"] == py and mo["month"] == pm]
		self.assertTrue(target, "Past month should be in the 6-month window")
		self.assertEqual(target[0]["dues"], 750)
		# Current month should be 0
		current = self._current_month_row(result)
		self.assertEqual(current["dues"], 0)
