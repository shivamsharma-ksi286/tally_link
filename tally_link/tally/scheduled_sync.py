"""
Scheduled Tasks for Tally Sync

This module contains background tasks that run on schedule to sync data
between Tally and ERPNext.
"""

import frappe
from frappe import _
from frappe.utils import now


def sync_all_from_tally():
	"""
	Main scheduled task to sync all data from Tally to ERPNext.
	Runs based on scheduler_events in hooks.py.

	Only runs if:
	- Tally Settings exists and is enabled
	- Auto sync is enabled in settings
	"""
	frappe.logger("tally_sync").info(f"[{now()}] Tally sync task triggered")

	# Check if Tally Settings exists and is enabled
	if not frappe.db.exists("Tally Settings", "Tally Settings"):
		frappe.logger("tally_sync").warning(f"[{now()}] Tally Settings DocType does not exist - skipping sync")
		return

	settings = frappe.get_doc("Tally Settings", "Tally Settings")
	frappe.logger("tally_sync").info(f"[{now()}] Tally Settings loaded - enabled: {settings.enabled}, auto_sync: {settings.get('auto_sync')}")

	if not settings.enabled:
		frappe.logger("tally_sync").info(f"[{now()}] Tally integration is disabled - skipping sync")
		return

	if not settings.get("auto_sync"):
		frappe.logger("tally_sync").info(f"[{now()}] Auto sync is disabled - skipping sync")
		return

	# Import sync functions
	from tally_link.tally.doctype_sync import (
		sync_ledgers_from_tally,
		sync_stock_items_from_tally,
		sync_vouchers_from_tally
	)

	company = settings.get("default_company")
	frappe.logger("tally_sync").info(f"[{now()}] Starting sync for company: {company or 'All Companies'}")

	try:
		# Sync master data
		if settings.get("sync_ledgers", True):
			frappe.logger("tally_sync").info(f"[{now()}] Enqueuing ledger sync...")
			frappe.enqueue(
				sync_ledgers_from_tally,
				queue="long",
				timeout=600,
				company=company,
				job_name="tally_sync_ledgers"
			)

		if settings.get("sync_stock_items", True):
			frappe.logger("tally_sync").info(f"[{now()}] Enqueuing stock items sync...")
			frappe.enqueue(
				sync_stock_items_from_tally,
				queue="long",
				timeout=600,
				company=company,
				job_name="tally_sync_stock_items"
			)

		# Sync transactions (vouchers)
		if settings.get("sync_vouchers", True):
			frappe.logger("tally_sync").info(f"[{now()}] Enqueuing vouchers sync...")
			frappe.enqueue(
				sync_vouchers_from_tally,
				queue="long",
				timeout=600,
				job_name="tally_sync_vouchers"
			)

		frappe.logger("tally_sync").info(f"[{now()}] All sync jobs enqueued successfully")

	except Exception as e:
		frappe.logger("tally_sync").error(f"[{now()}] Tally sync failed: {str(e)}")
		frappe.log_error(
			message=str(e),
			title=_("Tally Scheduled Sync Failed")
		)
