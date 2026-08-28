import frappe

from rental.rental.services.contract_validation import expire_contracts


def expire_contracts_task():
	"""Daily cron: expire past contracts.

	Source: ``src/services/contract-expiration-cron.ts``.
	Calls ``expireContracts()`` which:
	- Flips active contracts with end_date < today to expired.
	- Checks for started approved renewals and sets closedByRenewalAt.
	- Recalculates unit status.
	- Closes expired contracts whose renewal has started.
	"""
	count = expire_contracts()
	frappe.logger().info(f"Contract expiration cron: expired {count} contract(s)")
	return count
