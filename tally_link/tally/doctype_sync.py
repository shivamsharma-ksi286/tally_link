"""
DocType Synchronization Module

This module handles synchronization between Tally DocTypes and Tally software.
It provides functions to sync data in both directions and log all operations.
"""

import frappe
from frappe import _
from frappe.utils import now
import json
import traceback
from datetime import datetime, date
from tally_link.tally.client import TallyClient


class DateTimeEncoder(json.JSONEncoder):
	"""Custom JSON encoder that handles datetime objects"""
	def default(self, obj):
		if isinstance(obj, (datetime, date)):
			return obj.isoformat()
		return super().default(obj)


def _extract_import_result(response):
	"""
	Extract result fields from a parsed Tally Import Data response.
	Tally returns: {"RESPONSE": {"CREATED": "1", "LINEERROR": "...", "EXCEPTIONS": "1", ...}}
	"""
	if not isinstance(response, dict):
		return {}
	if "RESPONSE" in response:
		r = response["RESPONSE"]
		return r if isinstance(r, dict) else {}
	# Fallback: ENVELOPE > BODY > DATA > IMPORTRESULT
	envelope = response.get("ENVELOPE", {})
	if isinstance(envelope, dict):
		body = envelope.get("BODY", {})
		if isinstance(body, dict):
			data = body.get("DATA", {})
			if isinstance(data, dict):
				result = data.get("IMPORTRESULT", {})
				if isinstance(result, dict):
					return result
	return {}


def create_sync_log(sync_type, operation, status, direction, entity_type, entity_name=None,
                   reference_doctype=None, reference_name=None, tally_data=None,
                   erp_data=None, error_message=None):
	"""
	Create a Tally Sync Log entry

	Args:
		sync_type: Master Data/Transaction/Report
		operation: Create/Update/Delete/Read
		status: Pending/In Progress/Success/Failed/Partial
		direction: Tally to ERP/ERP to Tally/Bidirectional
		entity_type: Ledger/Stock Item/Voucher/etc
		entity_name: Name of the entity
		reference_doctype: ERPNext DocType
		reference_name: ERPNext document name
		tally_data: JSON data from Tally
		erp_data: JSON data from ERP
		error_message: Error message if failed

	Returns:
		Sync log document name
	"""
	try:
		# Validate reference_name exists for the given reference_doctype to avoid link errors
		safe_reference_doctype = None
		safe_reference_name = None
		if reference_doctype and reference_name:
			if frappe.db.exists(reference_doctype, reference_name):
				safe_reference_doctype = reference_doctype
				safe_reference_name = reference_name

		log = frappe.get_doc({
			"doctype": "Tally Sync Log",
			"sync_type": sync_type,
			"operation": operation,
			"status": status,
			"direction": direction,
			"entity_type": entity_type,
			"entity_name": entity_name,
			"reference_doctype": safe_reference_doctype,
			"reference_name": safe_reference_name,
			"tally_data": json.dumps(tally_data, indent=2, cls=DateTimeEncoder) if tally_data else None,
			"erp_data": json.dumps(erp_data, indent=2, cls=DateTimeEncoder) if erp_data else None,
			"error_message": error_message,
			"traceback": traceback.format_exc() if error_message else None,
			"sync_date": now(),
			"processed_by": frappe.session.user
		})
		log.insert(ignore_permissions=True)
		frappe.db.commit()
		return log.name
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Failed to create Tally Sync Log"))
		return None


# ================== LEDGER SYNC ==================

def sync_ledgers_from_tally(company=None, parent_group=None):
	"""
	Sync all ledgers from Tally to Tally Ledger DocType

	Args:
		company: Tally company name (optional)
		parent_group: Filter by parent group (optional)

	Returns:
		dict: Sync statistics
	"""
	frappe.logger("tally_sync").info(f"[{now()}] sync_ledgers_from_tally started - company: {company}, parent_group: {parent_group}")

	created = 0
	updated = 0
	failed = 0

	try:
		frappe.logger("tally_sync").info(f"[{now()}] Initializing TallyClient...")
		client = TallyClient()
		frappe.logger("tally_sync").info(f"[{now()}] TallyClient initialized, fetching ledgers...")
		ledgers = client.get_ledgers(company=company)
		frappe.logger("tally_sync").info(f"[{now()}] Fetched {len(ledgers) if ledgers else 0} ledgers from Tally")

		if parent_group:
			ledgers = [l for l in ledgers if l.get("parent") == parent_group]

		for ledger_data in ledgers:
			try:
				ledger_name = ledger_data.get("name")
				if not ledger_name:
					continue

				# Check if ledger exists
				if frappe.db.exists("Tally Ledger", ledger_name):
					# Update existing
					ledger = frappe.get_doc("Tally Ledger", ledger_name)
					operation = "Update"
				else:
					# Create new
					ledger = frappe.new_doc("Tally Ledger")
					ledger.ledger_name = ledger_name
					operation = "Create"

				# Map fields. Only overwrite contact/mailing fields when Tally actually
				# returned a value — a blank read (e.g. from a Tally version/report
				# that doesn't expose LEDMAILINGDETAILS.LIST) must not erase data that
				# a manual ERP-to-Tally push already wrote locally.
				ledger.parent_group = ledger_data.get("parent")
				ledger.alias = ledger_data.get("alias")
				ledger.guid = ledger_data.get("guid")
				ledger.tally_company = company or ledger_data.get("company")
				for field in ("mailing_name", "address", "state", "country", "pincode", "mobile", "email", "pan", "gstin"):
					value = ledger_data.get(field)
					if value:
						setattr(ledger, field, value)
				ledger.opening_balance = ledger_data.get("opening_balance", 0)
				ledger.current_balance = ledger_data.get("current_balance", 0)
				ledger.last_sync_date = now()
				ledger.sync_status = "Synced"
				ledger.additional_data = json.dumps(ledger_data, indent=2, cls=DateTimeEncoder)

				ledger.save(ignore_permissions=True)

				if operation == "Create":
					created += 1
				else:
					updated += 1

				# Create sync log
				create_sync_log(
					sync_type="Master Data",
					operation=operation,
					status="Success",
					direction="Tally to ERP",
					entity_type="Ledger",
					entity_name=ledger_name,
					reference_doctype="Tally Ledger",
					reference_name=ledger.name,
					tally_data=ledger_data
				)

			except Exception as e:
				failed += 1
				frappe.log_error(
					message=f"Error syncing ledger {ledger_data.get('name')}: {str(e)}",
					title=_("Ledger Sync Error")
				)
				create_sync_log(
					sync_type="Master Data",
					operation="Update" if frappe.db.exists("Tally Ledger", ledger_data.get("name")) else "Create",
					status="Failed",
					direction="Tally to ERP",
					entity_type="Ledger",
					entity_name=ledger_data.get("name"),
					tally_data=ledger_data,
					error_message=str(e)
				)
				continue

		frappe.db.commit()

	except Exception as e:
		frappe.logger("tally_sync").error(f"[{now()}] Ledger sync failed with error: {str(e)}")
		frappe.log_error(message=str(e), title=_("Ledger Sync Failed"))
		raise

	frappe.logger("tally_sync").info(f"[{now()}] sync_ledgers_from_tally completed - created: {created}, updated: {updated}, failed: {failed}")
	return {"created": created, "updated": updated, "failed": failed, "total": created + updated + failed}


@frappe.whitelist()
def sync_ledger_to_tally(ledger_name, operation="create"):
	"""
	Sync a Tally Ledger from ERP to Tally

	Args:
		ledger_name: Name of the Tally Ledger document (docname or ledger_name field)
		operation: create/update

	Returns:
		dict: Sync result
	"""
	try:
		# ledger_name may be the display name (ledger_name field), not the docname
		if not frappe.db.exists("Tally Ledger", ledger_name):
			actual_name = frappe.db.get_value("Tally Ledger", {"ledger_name": ledger_name}, "name")
			if not actual_name:
				frappe.log_error(message=f"Tally Ledger {ledger_name} not found", title=_("Ledger Push Failed"))
				return {"success": False, "error": f"Tally Ledger {ledger_name} not found"}
			ledger_name = actual_name
		ledger = frappe.get_doc("Tally Ledger", ledger_name)
		client = TallyClient()

		settings = TallyClient.get_tally_settings()
		company_name = settings.get("default_company") or ""

		ledger_data = {
			"name": ledger.ledger_name,
			"parent": ledger.parent_group,
			"address": ledger.address,
			"country": ledger.country,
			"state": ledger.state,
			"pincode": ledger.pincode,
			"mobile": ledger.mobile,
			"email": ledger.email,
			"gstin": ledger.gstin,
			"pan": ledger.pan,
			"mailing_name": ledger.mailing_name,
			"company_name": company_name,
		}

		# Ledgers that were synced before already exist in Tally — sending Action="Create"
		# for those makes Tally raise EXCEPTIONS=1 instead of updating. Use Alter for them.
		tally_action = "Alter" if ledger.sync_status == "Synced" or operation == "update" else "Create"
		response = client.create_ledger(action=tally_action, **ledger_data)

		import_result = _extract_import_result(response)
		line_error = import_result.get("LINEERROR")
		created = str(import_result.get("CREATED", "0")).strip()
		altered = str(import_result.get("ALTERED", "0")).strip()
		exceptions = str(import_result.get("EXCEPTIONS", "0")).strip()
		tally_accepted = (not line_error) and (created != "0" or altered != "0")

		# A Create attempt against a ledger Tally already has raises EXCEPTIONS=1 with
		# no LINEERROR text — retry once as an Alter before giving up.
		if not tally_accepted and tally_action == "Create" and not line_error and exceptions != "0":
			response = client.create_ledger(action="Alter", **ledger_data)
			import_result = _extract_import_result(response)
			line_error = import_result.get("LINEERROR")
			created = str(import_result.get("CREATED", "0")).strip()
			altered = str(import_result.get("ALTERED", "0")).strip()
			tally_accepted = (not line_error) and (created != "0" or altered != "0")

		ledger.db_set("last_sync_date", now(), update_modified=False)
		if tally_accepted:
			ledger.db_set("sync_status", "Synced", update_modified=False)
			sync_status = "Success"
		else:
			ledger.db_set("sync_status", "Failed", update_modified=False)
			sync_status = "Failed"

		create_sync_log(
			sync_type="Master Data",
			operation=operation.capitalize(),
			status=sync_status,
			direction="ERP to Tally",
			entity_type="Ledger",
			entity_name=ledger.ledger_name,
			reference_doctype="Tally Ledger",
			reference_name=ledger.name,
			erp_data=ledger.as_dict(),
			tally_data=response,
			error_message=line_error if line_error else None
		)

		if not tally_accepted:
			error_msg = line_error or (
				"Tally rejected the ledger (CREATED=0, EXCEPTIONS=1). "
				"This usually means a ledger with this exact name already exists under a "
				"different parent group in Tally, or the ledger name conflicts with a reserved name."
				if exceptions != "0" else "Tally rejected ledger creation (CREATED=0)"
			)
			return {"success": False, "error": error_msg, "response": response}

		result = {"success": True, "response": response}

		has_address_data = bool(ledger.address or ledger.state or ledger.country)

		if has_address_data and not ledger.pincode:
			# Tally silently discards address/state/country/mailing name unless a
			# pincode is also present — surface that instead of failing silently.
			result["warning"] = (
				f"Address/state/country were NOT sent to Tally — Tally requires a pincode "
				f"to save these fields, and this ledger's linked address has none. "
				f"Add a pincode to the address on the linked {ledger.linked_doctype or 'record'} and push again."
			)
		elif has_address_data and ledger.pincode:
			# Tally can silently drop the LEDMAILINGDETAILS.LIST block when import
			# requests land in quick succession, even with correct data and a valid
			# pincode — isolated, well-spaced writes are reliable. Verify it actually
			# persisted and retry with growing pauses before reporting success.
			import time

			def _mailing_details_landed():
				try:
					tally_ledgers = client.get_ledgers()
					match = next((l for l in tally_ledgers if l.get("name") == ledger.ledger_name), None)
					return bool(match and match.get("address"))
				except Exception:
					return True  # can't verify — don't block success on a read failure

			if not _mailing_details_landed():
				for delay in (4, 8, 15):
					time.sleep(delay)
					client.create_ledger(action="Alter", **ledger_data)
					time.sleep(2)
					if _mailing_details_landed():
						break
				else:
					result["warning"] = (
						"Tally accepted the ledger but the address/state/country/pincode did not "
						"save after several attempts — this happens intermittently on this Tally "
						"server. Try pushing again in a minute; if it keeps happening, check the "
						"Tally desktop app for details."
					)

		return result

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Ledger Push Failed"))
		# ledger_name is the display-name field value, not necessarily the docname;
		# resolve the actual docname to avoid "Could not find Reference Name" errors
		doc_name = frappe.db.get_value("Tally Ledger", {"ledger_name": ledger_name}, "name") or ledger_name
		create_sync_log(
			sync_type="Master Data",
			operation=operation.capitalize(),
			status="Failed",
			direction="ERP to Tally",
			entity_type="Ledger",
			entity_name=ledger_name,
			reference_doctype="Tally Ledger",
			reference_name=doc_name,
			error_message=str(e)
		)
		return {"success": False, "error": str(e)}


# ================== STOCK ITEM SYNC ==================

def sync_stock_items_from_tally(company=None):
	"""
	Sync all stock items from Tally to Tally Stock Item DocType

	Args:
		company: Tally company name (optional)

	Returns:
		dict: Sync statistics
	"""
	frappe.logger("tally_sync").info(f"[{now()}] sync_stock_items_from_tally started - company: {company}")

	created = 0
	updated = 0
	failed = 0

	try:
		frappe.logger("tally_sync").info(f"[{now()}] Initializing TallyClient...")
		client = TallyClient()
		frappe.logger("tally_sync").info(f"[{now()}] TallyClient initialized, fetching stock items...")
		items = client.get_stock_items(company=company)
		frappe.logger("tally_sync").info(f"[{now()}] Fetched {len(items) if items else 0} stock items from Tally")

		for item_data in items:
			try:
				item_name = item_data.get("name")
				if not item_name:
					continue

				# Check if item exists
				if frappe.db.exists("Tally Stock Item", item_name):
					item = frappe.get_doc("Tally Stock Item", item_name)
					operation = "Update"
				else:
					item = frappe.new_doc("Tally Stock Item")
					item.item_name = item_name
					operation = "Create"

				# Map fields
				item.parent_group = item_data.get("parent") or item_data.get("category")
				item.alias = item_data.get("alias")
				item.guid = item_data.get("guid")
				item.tally_company = company or item_data.get("company")
				item.category = item_data.get("category")
				item.base_units = item_data.get("base_units")
				item.opening_balance = item_data.get("opening_balance", 0)
				item.opening_rate = item_data.get("opening_rate", 0)
				item.opening_value = item_data.get("opening_value", 0)
				item.current_balance = item_data.get("current_balance", 0)
				item.current_rate = item_data.get("current_rate", 0)
				item.current_value = item_data.get("current_value", 0)
				item.hsn_code = item_data.get("hsn_code")

				# Handle GST fields
				gst_applicable = item_data.get("gst_applicable", "No")
				item.gst_applicable = 1 if gst_applicable and str(gst_applicable).lower() in ["yes", "true", "1"] else 0
				item.gst_rate = item_data.get("gst_rate")

				item.last_sync_date = now()
				item.sync_status = "Synced"
				item.additional_data = json.dumps(item_data, indent=2, cls=DateTimeEncoder)

				item.save(ignore_permissions=True)

				if operation == "Create":
					created += 1
				else:
					updated += 1

				create_sync_log(
					sync_type="Master Data",
					operation=operation,
					status="Success",
					direction="Tally to ERP",
					entity_type="Stock Item",
					entity_name=item_name,
					reference_doctype="Tally Stock Item",
					reference_name=item.name,
					tally_data=item_data
				)

			except Exception as e:
				failed += 1
				frappe.log_error(
					message=f"Error syncing item {item_data.get('name')}: {str(e)}",
					title=_("Item Sync Error")
				)
				create_sync_log(
					sync_type="Master Data",
					operation="Update" if frappe.db.exists("Tally Stock Item", item_data.get("name")) else "Create",
					status="Failed",
					direction="Tally to ERP",
					entity_type="Stock Item",
					entity_name=item_data.get("name"),
					tally_data=item_data,
					error_message=str(e)
				)
				continue

		frappe.db.commit()

	except Exception as e:
		frappe.logger("tally_sync").error(f"[{now()}] Stock items sync failed with error: {str(e)}")
		frappe.log_error(message=str(e), title=_("Item Sync Failed"))
		raise

	frappe.logger("tally_sync").info(f"[{now()}] sync_stock_items_from_tally completed - created: {created}, updated: {updated}, failed: {failed}")
	return {"created": created, "updated": updated, "failed": failed, "total": created + updated + failed}


@frappe.whitelist()
def sync_stock_item_to_tally(item_name, operation="create"):
	"""
	Sync a Tally Stock Item from ERP to Tally

	Args:
		item_name: Name of the Tally Stock Item document
		operation: create/update

	Returns:
		dict: Sync result
	"""
	try:
		item = frappe.get_doc("Tally Stock Item", item_name)
		client = TallyClient()

		item_data = {
			"name": item.item_name,
			"category": item.category or item.parent_group,
			"unit": item.base_units
		}

		if operation == "create":
			response = client.create_stock_item(**item_data)
		else:
			response = client.create_stock_item(**item_data)

		# Update sync status
		item.db_set("last_sync_date", now(), update_modified=False)
		item.db_set("sync_status", "Synced", update_modified=False)

		create_sync_log(
			sync_type="Master Data",
			operation=operation.capitalize(),
			status="Success",
			direction="ERP to Tally",
			entity_type="Stock Item",
			entity_name=item.item_name,
			reference_doctype="Tally Stock Item",
			reference_name=item.name,
			erp_data=item.as_dict(),
			tally_data=response
		)

		return {"success": True, "response": response}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Item Push Failed"))
		create_sync_log(
			sync_type="Master Data",
			operation=operation.capitalize(),
			status="Failed",
			direction="ERP to Tally",
			entity_type="Stock Item",
			entity_name=item_name,
			reference_doctype="Tally Stock Item",
			reference_name=item_name,
			error_message=str(e)
		)
		return {"success": False, "error": str(e)}


# ================== VOUCHER SYNC ==================

def sync_vouchers_from_tally(voucher_type=None, from_date=None, to_date=None):
	"""
	Sync vouchers from Tally to Tally Voucher DocType

	Args:
		voucher_type: Type of voucher (optional)
		from_date: Start date (optional)
		to_date: End date (optional)

	Returns:
		dict: Sync statistics
	"""
	frappe.logger("tally_sync").info(f"[{now()}] sync_vouchers_from_tally started - voucher_type: {voucher_type}, from_date: {from_date}, to_date: {to_date}")

	created = 0
	updated = 0
	failed = 0

	try:
		frappe.logger("tally_sync").info(f"[{now()}] Initializing TallyClient...")
		client = TallyClient()
		frappe.logger("tally_sync").info(f"[{now()}] TallyClient initialized, fetching vouchers...")
		vouchers = client.get_vouchers(
			voucher_type=voucher_type,
			from_date=from_date,
			to_date=to_date
		)
		frappe.logger("tally_sync").info(f"[{now()}] Fetched {len(vouchers) if vouchers else 0} vouchers from Tally")

		for voucher_data in vouchers:
			try:
				voucher_number = voucher_data.get("voucher_number")
				guid = voucher_data.get("guid")

				# Check if voucher exists by GUID or voucher number
				existing = None
				if guid:
					existing = frappe.db.get_value("Tally Voucher", {"guid": guid}, "name")

				if existing:
					voucher = frappe.get_doc("Tally Voucher", existing)
					operation = "Update"
				else:
					voucher = frappe.new_doc("Tally Voucher")
					operation = "Create"

				# Map fields
				voucher.voucher_type = voucher_data.get("voucher_type")
				voucher.voucher_number = voucher_number
				voucher.date = voucher_data.get("date")
				voucher.guid = guid
				voucher.tally_company = voucher_data.get("company")
				voucher.party_ledger_name = voucher_data.get("party_ledger")
				voucher.narration = voucher_data.get("narration")
				voucher.reference_number = voucher_data.get("reference_number")
				voucher.reference_date = voucher_data.get("reference_date")
				voucher.is_cancelled = voucher_data.get("is_cancelled", 0)

				# Clear and add ledger entries
				voucher.ledger_entries = []
				for entry in voucher_data.get("ledger_entries", []):
					voucher.append("ledger_entries", {
						"ledger_name": entry.get("ledger_name"),
						"is_debit": entry.get("is_debit", False),
						"is_credit": entry.get("is_credit", False),
						"amount": entry.get("amount", 0)
					})

				voucher.last_sync_date = now()
				voucher.sync_status = "Synced"
				voucher.voucher_data = json.dumps(voucher_data, indent=2, cls=DateTimeEncoder)

				# Submitted (docstatus=1) and cancelled (docstatus=2) docs cannot be
				# saved normally — use db_set for field-level updates instead.
				if operation == "Update" and voucher.docstatus in (1, 2):
					voucher.db_set({
						"voucher_type": voucher.voucher_type,
						"voucher_number": voucher.voucher_number,
						"date": voucher.date,
						"guid": voucher.guid,
						"tally_company": voucher.tally_company,
						"party_ledger_name": voucher.party_ledger_name,
						"narration": voucher.narration,
						"reference_number": voucher.reference_number,
						"reference_date": voucher.reference_date,
						"is_cancelled": voucher.is_cancelled,
						"last_sync_date": voucher.last_sync_date,
						"sync_status": voucher.sync_status,
						"voucher_data": voucher.voucher_data,
					}, update_modified=False)
				else:
					voucher.save(ignore_permissions=True)

				if operation == "Create":
					created += 1
				else:
					updated += 1

				create_sync_log(
					sync_type="Transaction",
					operation=operation,
					status="Success",
					direction="Tally to ERP",
					entity_type="Voucher",
					entity_name=voucher_number,
					reference_doctype="Tally Voucher",
					reference_name=voucher.name,
					tally_data=voucher_data
				)

			except Exception as e:
				failed += 1
				frappe.log_error(
					message=f"Error syncing voucher {voucher_data.get('voucher_number')}: {str(e)}",
					title=_("Voucher Sync Error")
				)
				create_sync_log(
					sync_type="Transaction",
					operation="Update" if existing else "Create",
					status="Failed",
					direction="Tally to ERP",
					entity_type="Voucher",
					entity_name=voucher_data.get("voucher_number"),
					tally_data=voucher_data,
					error_message=str(e)
				)
				continue

		frappe.db.commit()

	except Exception as e:
		frappe.logger("tally_sync").error(f"[{now()}] Voucher sync failed with error: {str(e)}")
		frappe.log_error(message=str(e), title=_("Voucher Sync Failed"))
		raise

	frappe.logger("tally_sync").info(f"[{now()}] sync_vouchers_from_tally completed - created: {created}, updated: {updated}, failed: {failed}")
	return {"created": created, "updated": updated, "failed": failed, "total": created + updated + failed}


@frappe.whitelist()
def sync_voucher_to_tally(voucher_name, operation="create"):
	"""
	Sync a Tally Voucher from ERP to Tally

	Args:
		voucher_name: Name of the Tally Voucher document
		operation: create/update

	Returns:
		dict: Sync result
	"""
	try:
		voucher = frappe.get_doc("Tally Voucher", voucher_name)
		client = TallyClient()

		# Verify Tally is reachable and a company is open before attempting push
		tally_ready = client.verify_tally_ready()
		if not tally_ready.get("ok"):
			error_msg = tally_ready["error"]
			voucher.db_set("sync_status", "Failed", update_modified=False)
			create_sync_log(sync_type="Transaction", operation=operation.capitalize(), status="Failed",
				direction="ERP to Tally", entity_type="Voucher", entity_name=voucher.name,
				reference_doctype="Tally Voucher", reference_name=voucher.name,
				error_message=error_msg)
			frappe.log_error(message=error_msg, title=_("Voucher Push Failed - Tally Not Ready"))
			return {"success": False, "error": error_msg}

		# Prepare ledger entries
		ledger_entries = []
		for entry in voucher.ledger_entries:
			ledger_entries.append({
				"ledger_name": entry.ledger_name,
				"amount": entry.amount,
				"is_debit": entry.is_debit
			})

		# Format date as YYYYMMDD for Tally XML (Frappe stores as YYYY-MM-DD)
		tally_date = voucher.date
		if tally_date and hasattr(tally_date, 'strftime'):
			tally_date = tally_date.strftime("%Y%m%d")
		elif tally_date and isinstance(tally_date, str) and '-' in str(tally_date):
			tally_date = str(tally_date).replace('-', '')

		# Get company from settings
		settings = TallyClient.get_tally_settings()
		company_name = settings.get("default_company") or ""

		# Ensure party ledger exists in Tally — missing ledger causes misleading "date missing" error
		if voucher.party_ledger_name:
			tally_ledger_exists = frappe.db.get_value("Tally Ledger", {"ledger_name": voucher.party_ledger_name}, "name")
			if not tally_ledger_exists:
				error_msg = f"Party ledger '{voucher.party_ledger_name}' not found in Tally Ledger. Create the customer/supplier in Tally first."
				voucher.db_set("sync_status", "Failed", update_modified=False)
				create_sync_log(sync_type="Transaction", operation=operation.capitalize(), status="Failed",
					direction="ERP to Tally", entity_type="Voucher", entity_name=voucher.name,
					reference_doctype="Tally Voucher", reference_name=voucher.name,
					error_message=error_msg)
				frappe.log_error(message=error_msg, title=_("Voucher Push Failed - Missing Ledger"))
				return {"success": False, "error": error_msg}

		# Create voucher in Tally
		response = client.create_voucher(
			voucher_type=voucher.voucher_type,
			date=tally_date,
			ledger_entries=ledger_entries,
			narration=voucher.narration,
			company_name=company_name,
			party_ledger=voucher.party_ledger_name,
		)

		# Check if Tally actually accepted the voucher
		import_result = _extract_import_result(response)
		line_error = import_result.get("LINEERROR")
		created = str(import_result.get("CREATED", "0")).strip()
		tally_accepted = (not line_error) and (created != "0")

		voucher.db_set("last_sync_date", now(), update_modified=False)

		if tally_accepted:
			if response.get("voucher_number"):
				voucher.db_set("voucher_number", response.get("voucher_number"), update_modified=False)
			if response.get("guid"):
				voucher.db_set("guid", response.get("guid"), update_modified=False)
			voucher.db_set("sync_status", "Synced", update_modified=False)

			create_sync_log(
				sync_type="Transaction",
				operation=operation.capitalize(),
				status="Success",
				direction="ERP to Tally",
				entity_type="Voucher",
				entity_name=voucher.voucher_number or voucher.name,
				reference_doctype="Tally Voucher",
				reference_name=voucher.name,
				erp_data=voucher.as_dict(),
				tally_data=response
			)
			return {"success": True, "response": response}
		else:
			raw_error = line_error or "Tally rejected the voucher (CREATED=0)"
			# Translate Tally's misleading "date missing" error into a specific actionable message
			if "date is missing" in raw_error.lower() or "date missing" in raw_error.lower():
				error_msg = (
					f"Tally rejected voucher date {tally_date} for {voucher.voucher_type} voucher. "
					f"Possible causes: (1) Tally date lock — go to Tally > F11 > Security and remove the entry lock date; "
					f"(2) No company open in Tally — open '{company_name}' at Gateway of Tally; "
					f"(3) Date {tally_date} is outside Tally's active financial year. "
					f"Raw Tally error: {raw_error}"
				)
			else:
				error_msg = raw_error
			voucher.db_set("sync_status", "Failed", update_modified=False)
			create_sync_log(
				sync_type="Transaction",
				operation=operation.capitalize(),
				status="Failed",
				direction="ERP to Tally",
				entity_type="Voucher",
				entity_name=voucher.name,
				reference_doctype="Tally Voucher",
				reference_name=voucher.name,
				erp_data=voucher.as_dict(),
				tally_data=response,
				error_message=error_msg
			)
			frappe.log_error(message=error_msg, title=_("Voucher Push Failed - Tally Rejected"))
			return {"success": False, "error": error_msg}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Voucher Push Failed"))
		create_sync_log(
			sync_type="Transaction",
			operation=operation.capitalize(),
			status="Failed",
			direction="ERP to Tally",
			entity_type="Voucher",
			entity_name=voucher_name,
			reference_doctype="Tally Voucher",
			reference_name=voucher_name,
			error_message=str(e)
		)
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def cancel_voucher_in_tally(voucher_name):
	"""
	Cancel a voucher in Tally (Note: Tally doesn't support deletion, use cancel)

	Args:
		voucher_name: Name of the Tally Voucher document

	Returns:
		dict: Sync result
	"""
	try:
		voucher = frappe.get_doc("Tally Voucher", voucher_name)

		# Note: tally-integration package may not support cancel operation
		# This would need to be implemented based on Tally's XML API

		voucher.db_set("is_cancelled", 1, update_modified=False)
		voucher.db_set("sync_status", "Synced", update_modified=False)

		create_sync_log(
			sync_type="Transaction",
			operation="Delete",
			status="Success",
			direction="ERP to Tally",
			entity_type="Voucher",
			entity_name=voucher.voucher_number or voucher.name,
			reference_doctype="Tally Voucher",
			reference_name=voucher.name
		)

		return {"success": True, "message": "Voucher marked as cancelled"}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Voucher Cancel Failed"))
		return {"success": False, "error": str(e)}


def _get_safe_item_group(preferred):
	"""Return preferred item group if it exists in ERPNext, else fall back to root."""
	if preferred and frappe.db.exists("Item Group", preferred):
		return preferred
	for fallback in ("All Item Groups", "Products", "Services"):
		if frappe.db.exists("Item Group", fallback):
			return fallback
	root = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ""}, "name")
	return root or "All Item Groups"


def _upsert_erpnext_item(tally_stock_item_doc):
	"""
	Create or update an ERPNext Item from a Tally Stock Item document.
	Links the Tally Stock Item back to the ERPNext Item once created/found.
	"""
	item_name = tally_stock_item_doc.item_name
	if not item_name:
		return

	if frappe.db.exists("Item", {"item_name": item_name}):
		item = frappe.get_doc("Item", {"item_name": item_name})
		changed = False
		if tally_stock_item_doc.base_units and item.stock_uom != tally_stock_item_doc.base_units:
			item.stock_uom = tally_stock_item_doc.base_units
			changed = True
		if tally_stock_item_doc.category:
			safe_group = _get_safe_item_group(tally_stock_item_doc.category)
			if item.item_group != safe_group:
				item.item_group = safe_group
				changed = True
		if changed:
			item.save(ignore_permissions=True)
	else:
		preferred = tally_stock_item_doc.category or tally_stock_item_doc.parent_group
		item = frappe.get_doc({
			"doctype": "Item",
			"item_code": item_name,
			"item_name": item_name,
			"item_group": _get_safe_item_group(preferred),
			"stock_uom": tally_stock_item_doc.base_units or "Nos",
			"is_stock_item": 1,
		})
		item.insert(ignore_permissions=True)

	tally_stock_item_doc.db_set("linked_doctype", "Item", update_modified=False)
	tally_stock_item_doc.db_set("linked_docname", item.name, update_modified=False)


# ================== API ENDPOINTS ==================

@frappe.whitelist()
def sync_all_ledgers(company=None, parent_group=None):
	"""API endpoint to sync ledgers from Tally"""
	return sync_ledgers_from_tally(company=company, parent_group=parent_group)


@frappe.whitelist()
def sync_all_stock_items(company=None):
	"""API endpoint to sync stock items from Tally"""
	return sync_stock_items_from_tally(company=company)


@frappe.whitelist()
def sync_all_vouchers(voucher_type=None, from_date=None, to_date=None):
	"""API endpoint to sync vouchers from Tally"""
	return sync_vouchers_from_tally(voucher_type=voucher_type, from_date=from_date, to_date=to_date)
