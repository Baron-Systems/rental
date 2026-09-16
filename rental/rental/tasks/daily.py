import frappe

from rental.rental.services.contract_validation import (
	activate_started_contracts,
	expire_contracts,
)


def expire_contracts_task():
	"""Daily cron: sync contract lifecycle (expire + activate).

	Source: ``src/services/contract-expiration-cron.ts`` → ``runExpirationJob``.
	Calls ``expireContracts()`` which:
	- Flips active contracts with end_date < today to expired.
	- Checks for started approved renewals and sets closedByRenewalAt.
	- Recalculates unit status.
	- Closes expired contracts whose renewal has started.

	Then calls ``activate_started_contracts()`` which handles the
	reserved → rented transition when an upcoming active contract's
	start_date has arrived — the only time-driven transition not covered
	by expireContracts(). derive_unit_status remains the single source
	of truth; activate_started_contracts only re-derives status for units
	currently marked 'reserved' and writes only when the result differs.

	The original wraps the call in try/catch, logging the start and result,
	and swallowing errors so the cron keeps running. The Frappe ``daily``
	scheduler handles deduplication (cronStarted guard) and midnight
	scheduling (msUntilNextMidnight), so those are not replicated here.
	"""
	logger = frappe.logger()
	try:
		logger.info("[ContractLifecycleCron] Running daily contract lifecycle sync...")
		expired_count = expire_contracts()
		activated_count = activate_started_contracts()
		logger.info(
			f"[ContractLifecycleCron] expired={expired_count}, activated={activated_count}"
		)
	except Exception as error:
		logger.error(f"[ContractLifecycleCron] Error during lifecycle job: {error}")
