"""Backfill rental_account on existing User Unit Preference records.

After adding the ``rental_account`` field to the User Unit Preference DocType,
existing records have a NULL rental_account.  Since the current architecture is
1:1 (User ↔ Rental Account via ``owner_user``), we can safely derive the
account from the preference's ``user`` field.

This patch is idempotent — it only updates records where rental_account
is NULL.

Run:
    bench --site <site> execute rental.rental.patches.v1_backfill_user_unit_preference_account.execute
"""

import frappe


def execute():
	"""Set rental_account on all User Unit Preference records that lack it."""
	prefs = frappe.db.get_all(
		"User Unit Preference",
		filters={"rental_account": ["is", "not set"]},
		fields=["name", "user"],
	)

	if not prefs:
		print("User Unit Preference: no records need backfill.")
		return {"backfilled": 0}

	backfilled = 0
	skipped = 0

	for pref in prefs:
		# Derive rental_account from the user via owner_user (1:1 relationship)
		account = frappe.db.get_value(
			"Rental Account",
			{"owner_user": pref["user"]},
			"name",
		)
		if not account:
			print(f"  SKIP: User Unit Preference '{pref['name']}' — user '{pref['user']}' has no Rental Account")
			skipped += 1
			continue

		frappe.db.set_value(
			"User Unit Preference",
			pref["name"],
			"rental_account",
			account,
			update_modified=False,
		)
		backfilled += 1

	frappe.db.commit()
	print(f"User Unit Preference: backfilled {backfilled} record(s), skipped {skipped}.")
	return {"backfilled": backfilled, "skipped": skipped}
