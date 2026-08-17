"""
Tally Bulk Synchronisation

Orchestrates full synchronisation runs across all entity types (ledgers,
stock items, vouchers) between Tally Software and ERPNext.
"""

import frappe
from frappe import _


def sync_all_from_tally():
	"""
	Primary scheduled task: synchronise all data from Tally to ERPNext.

	Triggered by scheduler_events defined in hooks.py. Runs only when Tally
	Settings exists, the integration is enabled, and auto-sync is active.
	"""
	frappe.logger("tally_sync").info("Tally scheduled synchronisation task initiated.")

	if not frappe.db.exists("Tally Settings", "Tally Settings"):
		frappe.logger("tally_sync").warning(
			"Tally Settings document not found. Scheduled synchronisation skipped."
		)
		return

	settings = frappe.get_doc("Tally Settings", "Tally Settings")
	frappe.logger("tally_sync").info(
		f"Tally Settings loaded — enabled: {settings.enabled}, "
		f"auto_sync: {settings.get('auto_sync')}"
	)

	if not settings.enabled:
		frappe.logger("tally_sync").info(
			"Tally integration is disabled. Scheduled synchronisation skipped."
		)
		return

	if not settings.get("auto_sync"):
		frappe.logger("tally_sync").info(
			"Automatic synchronisation is disabled. Scheduled synchronisation skipped."
		)
		return

	from tally_link.tally.doctype_sync import (
		sync_ledgers_from_tally,
		sync_stock_items_from_tally,
		sync_vouchers_from_tally
	)

	company = settings.get("default_company")
	frappe.logger("tally_sync").info(
		f"Initiating synchronisation for company: {company or 'All Companies'}"
	)

	try:
		if settings.get("sync_ledgers", True):
			frappe.logger("tally_sync").info("Queuing ledger synchronisation job.")
			frappe.enqueue(
				sync_ledgers_from_tally,
				queue="long",
				timeout=600,
				company=company,
				job_name="tally_sync_ledgers"
			)

		if settings.get("sync_stock_items", True):
			frappe.logger("tally_sync").info("Queuing stock item synchronisation job.")
			frappe.enqueue(
				sync_stock_items_from_tally,
				queue="long",
				timeout=600,
				company=company,
				job_name="tally_sync_stock_items"
			)

		if settings.get("sync_vouchers", True):
			frappe.logger("tally_sync").info("Queuing voucher synchronisation job.")
			frappe.enqueue(
				sync_vouchers_from_tally,
				queue="long",
				timeout=600,
				job_name="tally_sync_vouchers"
			)

		frappe.logger("tally_sync").info("All synchronisation jobs have been queued successfully.")

	except Exception as e:
		frappe.logger("tally_sync").error(f"Scheduled Tally synchronisation failed: {str(e)}")
		frappe.log_error(
			message=str(e),
			title=_("Tally Scheduled Synchronisation Failed")
		)
