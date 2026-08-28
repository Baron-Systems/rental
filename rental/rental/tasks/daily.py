import frappe

from rental.rental.services.contract_validation import expire_contracts


def expire_contracts_task():
	"""Daily cron: expire past contracts.

	Source: ``src/services/contract-expiration-cron.ts`` → ``runExpirationJob``.
	Calls ``expireContracts()`` which:
	- Flips active contracts with end_date < today to expired.
	- Checks for started approved renewals and sets closedByRenewalAt.
	- Recalculates unit status.
	- Closes expired contracts whose renewal has started.

	The original wraps the call in try/catch, logging the start and result,
	and swallowing errors so the cron keeps running. The Frappe ``daily``
	scheduler handles deduplication (cronStarted guard) and midnight
	scheduling (msUntilNextMidnight), so those are not replicated here.
	"""
	logger = frappe.logger()
	try:
		logger.info("[ContractExpirationCron] Running daily contract expiration check...")
		count = expire_contracts()
		logger.info(f"[ContractExpirationCron] {count} contract(s) marked as expired.")
	except Exception as error:
		logger.error(f"[ContractExpirationCron] Error during expiration job: {error}")
