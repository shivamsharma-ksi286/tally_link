"""
Tally Master Data Synchronisation

Provides helper functions for synchronising master data (customers, suppliers,
stock items) and transactions between Tally Software and ERPNext.
"""

from datetime import datetime

import frappe
from frappe import _
from tally_link.tally.client import TallyClient


def sync_customers():
	"""
	Synchronise customers from Tally to ERPNext.

	Fetches ledgers under the "Sundry Debtors" group from Tally and creates
	or updates the corresponding Customer records in ERPNext.

	Returns:
		dict: Synchronisation result counts — created, updated, skipped, total.
	"""
	client = TallyClient()
	ledgers = client.get_ledgers()

	records_created = 0
	records_updated = 0
	records_skipped = 0

	customer_ledgers = [
		ledger for ledger in ledgers
		if ledger.get("parent") == "Sundry Debtors"
	]

	for ledger in customer_ledgers:
		try:
			customer_name = ledger.get("name")
			if not customer_name:
				records_skipped += 1
				continue

			if frappe.db.exists("Customer", {"customer_name": customer_name}):
				customer = frappe.get_doc("Customer", {"customer_name": customer_name})
				customer.tally_ledger_name = customer_name
				if ledger.get("mobile"):
					customer.mobile_no = ledger.get("mobile")
				if ledger.get("email"):
					customer.email_id = ledger.get("email")
				customer.save(ignore_permissions=True)
				records_updated += 1
			else:
				customer = frappe.get_doc({
					"doctype": "Customer",
					"customer_name": customer_name,
					"customer_type": "Company",
					"customer_group": "Commercial",
					"territory": "All Territories",
					"tally_ledger_name": customer_name,
					"mobile_no": ledger.get("mobile"),
					"email_id": ledger.get("email")
				})
				customer.insert(ignore_permissions=True)
				records_created += 1

			frappe.db.commit()

		except Exception as e:
			frappe.log_error(
				message=f"An error occurred while synchronising customer '{ledger.get('name')}': {str(e)}",
				title=_("Tally Customer Synchronisation Error")
			)
			records_skipped += 1
			continue

	return {
		"created": records_created,
		"updated": records_updated,
		"skipped": records_skipped,
		"total": len(customer_ledgers)
	}


def sync_items():
	"""
	Synchronise stock items from Tally to ERPNext.

	Fetches all stock items from Tally and creates or updates the corresponding
	Item records in ERPNext.

	Returns:
		dict: Synchronisation result counts — created, updated, skipped, total.
	"""
	client = TallyClient()
	stock_items = client.get_stock_items()

	records_created = 0
	records_updated = 0
	records_skipped = 0

	for tally_item in stock_items:
		try:
			item_name = tally_item.get("name")
			if not item_name:
				records_skipped += 1
				continue

			if frappe.db.exists("Item", {"item_name": item_name}):
				item = frappe.get_doc("Item", {"item_name": item_name})
				item.tally_item_name = item_name
				if tally_item.get("base_units"):
					item.stock_uom = tally_item.get("base_units")
				item.save(ignore_permissions=True)
				records_updated += 1
			else:
				item = frappe.get_doc({
					"doctype": "Item",
					"item_code": item_name,
					"item_name": item_name,
					"item_group": tally_item.get("parent", "Products"),
					"stock_uom": tally_item.get("base_units", "Nos"),
					"tally_item_name": item_name,
					"is_stock_item": 1
				})
				item.insert(ignore_permissions=True)
				records_created += 1

			frappe.db.commit()

		except Exception as e:
			frappe.log_error(
				message=f"An error occurred while synchronising stock item '{tally_item.get('name')}': {str(e)}",
				title=_("Tally Stock Item Synchronisation Error")
			)
			records_skipped += 1
			continue

	return {
		"created": records_created,
		"updated": records_updated,
		"skipped": records_skipped,
		"total": len(stock_items)
	}


def push_sales_invoice(sales_invoice_name):
	"""
	Push a Sales Invoice from ERPNext to Tally as a voucher.

	Converts the invoice into a Journal voucher with debit entries for the customer
	and credit entries for sales and tax ledgers, then submits it to Tally.

	Args:
		sales_invoice_name (str): Name of the Sales Invoice document.

	Returns:
		dict: Push result containing the invoice name and Tally response.
	"""
	client = TallyClient()
	si = frappe.get_doc("Sales Invoice", sales_invoice_name)

	ledger_entries = [
		{"ledger_name": si.customer_name, "amount": si.grand_total, "is_debit": True},
		{"ledger_name": "Sales", "amount": si.total, "is_debit": False},
	]
	for tax in si.taxes:
		ledger_entries.append({
			"ledger_name": tax.account_head,
			"amount": tax.tax_amount,
			"is_debit": False
		})

	posting_date_str = si.posting_date
	if isinstance(posting_date_str, str):
		tally_date = datetime.strptime(posting_date_str, "%Y-%m-%d").strftime("%Y%m%d")
	else:
		tally_date = posting_date_str.strftime("%Y%m%d")

	response = client.create_voucher(
		voucher_type="Journal",
		date=tally_date,
		ledger_entries=ledger_entries,
		narration=f"Sales Invoice {si.name} — {si.customer_name}"
	)

	si.db_set("tally_voucher_number", response.get("voucher_number"), update_modified=False)
	frappe.db.commit()

	return {
		"sales_invoice": si.name,
		"tally_response": response
	}


def validate_tally_connection():
	"""
	Verify that the Tally server is reachable.

	Returns:
		tuple: (is_connected (bool), message (str))
	"""
	try:
		client = TallyClient()
		if client.test_connection():
			return True, _("Connection to Tally server established successfully.")
		else:
			return False, _("Unable to connect to the Tally server.")
	except Exception as e:
		return False, str(e)
