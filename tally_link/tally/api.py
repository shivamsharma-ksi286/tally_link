"""
Tally API Endpoints

This module provides whitelisted API endpoints for Tally integration operations
that can be called from the frontend or external systems.
"""

import frappe
from frappe import _
from tally_link.tally.client import TallyClient


def _extract_import_result(response):
	"""
	Extract the result fields from a parsed Tally Import Data response.
	Tally returns: {"RESPONSE": {"CREATED": "1", "LINEERROR": "...", "EXCEPTIONS": "1", ...}}
	"""
	if not isinstance(response, dict):
		return {}
	# Primary path: RESPONSE key at top level
	if "RESPONSE" in response:
		r = response["RESPONSE"]
		return r if isinstance(r, dict) else {}
	# Fallback: ENVELOPE > BODY > DATA > IMPORTRESULT (older Tally versions)
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


@frappe.whitelist()
def get_companies():
	"""
	Get list of all companies from Tally

	Returns:
		list: List of company dictionaries
	"""
	try:
		client = TallyClient()
		companies = client.get_companies()
		return {"success": True, "data": companies}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Get Companies"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_current_company():
	"""
	Get current company information from Tally

	Returns:
		dict: Company information
	"""
	try:
		client = TallyClient()
		company = client.get_current_company()
		return {"success": True, "data": company}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Get Current Company"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_ledgers(company=None):
	"""
	Get all ledgers from Tally

	Args:
		company: Company name (optional)

	Returns:
		dict: Response with ledgers list
	"""
	try:
		client = TallyClient()
		ledgers = client.get_ledgers(company=company)
		return {"success": True, "data": ledgers}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Get Ledgers"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def create_ledger(name, parent, address=None, mobile=None, email=None):
	"""
	Create a new ledger in Tally

	Args:
		name: Ledger name
		parent: Parent ledger group
		address: Address (optional)
		mobile: Mobile number (optional)
		email: Email (optional)

	Returns:
		dict: Response with creation status
	"""
	try:
		client = TallyClient()
		response = client.create_ledger(
			name=name,
			parent=parent,
			address=address,
			mobile=mobile,
			email=email
		)
		return {"success": True, "data": response}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Create Ledger"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_stock_items(company=None):
	"""
	Get all stock items from Tally

	Args:
		company: Company name (optional)

	Returns:
		dict: Response with stock items list
	"""
	try:
		client = TallyClient()
		items = client.get_stock_items(company=company)
		return {"success": True, "data": items}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Get Stock Items"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def create_stock_item(name, category, unit):
	"""
	Create a new stock item in Tally

	Args:
		name: Item name
		category: Item category
		unit: Unit of measurement

	Returns:
		dict: Response with creation status
	"""
	try:
		client = TallyClient()
		response = client.create_stock_item(name=name, category=category, unit=unit)
		return {"success": True, "data": response}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Create Stock Item"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_vouchers(voucher_type=None, from_date=None, to_date=None):
	"""
	Get vouchers from Tally

	Args:
		voucher_type: Type of voucher (Sales, Purchase, etc.)
		from_date: Start date (optional)
		to_date: End date (optional)

	Returns:
		dict: Response with vouchers list
	"""
	try:
		client = TallyClient()
		vouchers = client.get_vouchers(
			voucher_type=voucher_type,
			from_date=from_date,
			to_date=to_date
		)
		return {"success": True, "data": vouchers}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Get Vouchers"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def create_voucher(voucher_type, date, ledger_entries, narration=None):
	"""
	Create a voucher in Tally

	Args:
		voucher_type: Type of voucher (Sales, Purchase, Receipt, Payment, Journal)
		date: Voucher date
		ledger_entries: JSON string or list of ledger entry dictionaries
		narration: Voucher narration (optional)

	Returns:
		dict: Response with creation status
	"""
	try:
		import json

		# Parse ledger_entries if it's a JSON string
		if isinstance(ledger_entries, str):
			ledger_entries = json.loads(ledger_entries)

		client = TallyClient()
		response = client.create_voucher(
			voucher_type=voucher_type,
			date=date,
			ledger_entries=ledger_entries,
			narration=narration
		)
		return {"success": True, "data": response}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Create Voucher"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def get_groups(group_type="Ledger"):
	"""
	Get groups from Tally

	Args:
		group_type: Type of group (Ledger, Stock, etc.)

	Returns:
		dict: Response with groups list
	"""
	try:
		client = TallyClient()
		groups = client.get_groups(group_type=group_type)
		return {"success": True, "data": groups}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Get Groups"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_customers_from_tally():
	"""
	Sync customers from Tally to ERPNext

	Returns:
		dict: Response with sync status
	"""
	try:
		from tally_link.tally.master_sync import sync_customers
		result = sync_customers()
		return {"success": True, "data": result}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Sync Customers"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def sync_items_from_tally():
	"""
	Sync items from Tally to ERPNext

	Returns:
		dict: Response with sync status
	"""
	try:
		from tally_link.tally.master_sync import sync_items
		result = sync_items()
		return {"success": True, "data": result}
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Sync Items"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def push_sales_invoice_to_tally(sales_invoice_name):
	"""
	Push a Sales Invoice from ERPNext to Tally as a Sales Voucher (synchronous).
	"""
	try:
		import re

		si = frappe.get_doc("Sales Invoice", sales_invoice_name)

		if si.docstatus != 1:
			return {"success": False, "message": _("Only submitted Sales Invoices can be pushed to Tally.")}

		client = TallyClient()
		settings = TallyClient.get_tally_settings()
		company_name = settings.get("default_company") or ""

		# Verify Tally is reachable and a company is open
		tally_ready = client.verify_tally_ready()
		if not tally_ready.get("ok"):
			return {"success": False, "message": tally_ready["error"]}

		def clean(account_head):
			return re.sub(r'\s*-\s*[A-Z0-9]+$', '', str(account_head or '')).strip()

		# Build ledger entries
		# In Tally Sales voucher: customer=credit (is_debit=False), income/tax=debit (is_debit=True)
		income_by_account = {}
		for item in si.items or []:
			acct = clean(item.income_account) if item.income_account else "Sales"
			income_by_account[acct] = income_by_account.get(acct, 0) + float(item.amount or 0)
		if not income_by_account:
			income_by_account["Sales"] = float(si.total or 0)

		ledger_entries = [
			{"ledger_name": si.customer_name, "amount": float(si.grand_total or 0), "is_debit": False},
		]
		for acct, amt in income_by_account.items():
			ledger_entries.append({"ledger_name": acct, "amount": amt, "is_debit": True})
		for tax in si.taxes or []:
			if tax.tax_amount:
				ledger_entries.append({"ledger_name": clean(tax.account_head), "amount": float(tax.tax_amount), "is_debit": True})

		# Format date as YYYYMMDD
		d = si.posting_date
		tally_date = d.strftime("%Y%m%d") if hasattr(d, 'strftime') else str(d).replace('-', '')

		# Push all referenced ledgers to Tally first (ignore failures — ledger may already exist)
		from tally_link.tally.doctype_sync import sync_ledger_to_tally
		all_ledger_names = {entry["ledger_name"] for entry in ledger_entries}
		for ledger_name in all_ledger_names:
			tally_ledger_name = frappe.db.get_value("Tally Ledger", {"ledger_name": ledger_name}, "name")
			if not tally_ledger_name and ledger_name == si.customer_name:
				from tally_link.tally.events import customer_after_insert
				customer_doc = frappe.get_doc("Customer", si.customer) if si.customer else None
				if customer_doc:
					frappe.flags.in_tally_synchronous_push = True
					try:
						customer_after_insert(customer_doc)
					finally:
						frappe.flags.in_tally_synchronous_push = False
					frappe.db.commit()
					tally_ledger_name = frappe.db.get_value("Tally Ledger", {"ledger_name": ledger_name}, "name")
			if tally_ledger_name:
				sync_ledger_to_tally(tally_ledger_name, operation="create")

		response = client.create_voucher(
			voucher_type="Sales",
			date=tally_date,
			ledger_entries=ledger_entries,
			narration=f"Sales Invoice {si.name} - {si.customer_name}",
			company_name=company_name,
			party_ledger=si.customer_name,
		)

		# Check Tally's response
		import_result = _extract_import_result(response)
		line_error = import_result.get("LINEERROR")
		created = str(import_result.get("CREATED", "0")).strip()
		tally_accepted = (not line_error) and (created != "0")

		if tally_accepted:
			frappe.db.commit()
			return {"success": True, "message": _("Sales Invoice pushed to Tally successfully."), "data": {"tally_response": response}}
		else:
			raw_error = line_error or "Tally rejected the voucher (CREATED=0)"
			if "date is missing" in raw_error.lower() or "date missing" in raw_error.lower():
				error_msg = (
					f"Tally rejected the voucher for date {tally_date}. "
					f"Possible causes: (1) Tally date lock is set — go to Tally > F11 > Security and remove the entry restriction date; "
					f"(2) No company open in Tally — open '{company_name}' at Gateway of Tally; "
					f"(3) Date is outside the active financial year in Tally."
				)
			else:
				error_msg = raw_error
			frappe.log_error(message=error_msg, title=_("Tally Push Failed - Sales Invoice"))
			return {"success": False, "message": error_msg}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Push Sales Invoice"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def push_purchase_invoice_to_tally(purchase_invoice_name):
	"""Push a Purchase Invoice from ERPNext to Tally as a Purchase Voucher."""
	try:
		import re

		pi = frappe.get_doc("Purchase Invoice", purchase_invoice_name)

		if pi.docstatus != 1:
			return {"success": False, "message": _("Only submitted Purchase Invoices can be pushed to Tally.")}

		client = TallyClient()
		settings = TallyClient.get_tally_settings()
		company_name = settings.get("default_company") or ""

		tally_ready = client.verify_tally_ready()
		if not tally_ready.get("ok"):
			return {"success": False, "message": tally_ready["error"]}

		def clean(account_head):
			return re.sub(r'\s*-\s*[A-Z0-9]+$', '', str(account_head or '')).strip()

		# In Tally Purchase voucher: supplier=credit (is_debit=False), expense/tax=debit (is_debit=True)
		expense_by_account = {}
		for item in pi.items or []:
			acct = clean(item.expense_account) if item.expense_account else "Purchase"
			expense_by_account[acct] = expense_by_account.get(acct, 0) + float(item.amount or 0)
		if not expense_by_account:
			expense_by_account["Purchase"] = float(pi.total or 0)

		ledger_entries = [
			{"ledger_name": pi.supplier_name, "amount": float(pi.grand_total or 0), "is_debit": False},
		]
		for acct, amt in expense_by_account.items():
			ledger_entries.append({"ledger_name": acct, "amount": amt, "is_debit": True})
		for tax in pi.taxes or []:
			if tax.tax_amount:
				ledger_entries.append({"ledger_name": clean(tax.account_head), "amount": float(tax.tax_amount), "is_debit": True})

		d = pi.posting_date
		tally_date = d.strftime("%Y%m%d") if hasattr(d, 'strftime') else str(d).replace('-', '')

		from tally_link.tally.doctype_sync import sync_ledger_to_tally
		all_ledger_names = {entry["ledger_name"] for entry in ledger_entries}
		for ledger_name in all_ledger_names:
			tally_ledger_name = frappe.db.get_value("Tally Ledger", {"ledger_name": ledger_name}, "name")
			if tally_ledger_name:
				sync_ledger_to_tally(tally_ledger_name, operation="create")

		response = client.create_voucher(
			voucher_type="Purchase",
			date=tally_date,
			ledger_entries=ledger_entries,
			narration=f"Purchase Invoice {pi.name} - {pi.supplier_name}",
			company_name=company_name,
			party_ledger=pi.supplier_name,
		)

		import_result = _extract_import_result(response)
		line_error = import_result.get("LINEERROR")
		created = str(import_result.get("CREATED", "0")).strip()
		tally_accepted = (not line_error) and (created != "0")

		if tally_accepted:
			frappe.db.commit()
			return {"success": True, "message": _("Purchase Invoice pushed to Tally successfully.")}
		else:
			raw_error = line_error or "Tally rejected the voucher (CREATED=0)"
			if "date is missing" in raw_error.lower() or "out of range" in raw_error.lower():
				error_msg = (
					f"Tally rejected the voucher for date {tally_date}. "
					f"Check: (1) Financial year covers this date in Tally; "
					f"(2) No date lock under F11 > Security; "
					f"(3) Company '{company_name}' is open in Tally."
				)
			else:
				error_msg = raw_error
			frappe.log_error(message=error_msg, title=_("Tally Push Failed - Purchase Invoice"))
			return {"success": False, "message": error_msg}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Push Purchase Invoice"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def push_customer_to_tally(customer_name):
	"""Push a Customer from ERPNext to Tally as a ledger (synchronous), including current address/GSTIN/PAN."""
	try:
		client = TallyClient()
		tally_ready = client.verify_tally_ready()
		if not tally_ready.get("ok"):
			return {"success": False, "message": tally_ready["error"]}

		from tally_link.tally.events import sync_party_fields_to_ledger
		tally_ledger_name = sync_party_fields_to_ledger("Customer", customer_name)
		frappe.db.commit()

		if not tally_ledger_name:
			return {"success": False, "message": _("Failed to create Tally Ledger for this Customer. Check that Tally Sync is enabled in Tally Settings.")}

		from tally_link.tally.doctype_sync import sync_ledger_to_tally
		result = sync_ledger_to_tally(tally_ledger_name, operation="update")

		if result.get("success"):
			response = {"success": True, "message": _("Customer pushed to Tally successfully.")}
			if result.get("warning"):
				response["warning"] = result["warning"]
			return response
		else:
			return {"success": False, "message": result.get("error") or _("Tally rejected the ledger.")}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Push Customer"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def push_supplier_to_tally(supplier_name):
	"""Push a Supplier from ERPNext to Tally as a ledger (synchronous), including current address/GSTIN/PAN."""
	try:
		client = TallyClient()
		tally_ready = client.verify_tally_ready()
		if not tally_ready.get("ok"):
			return {"success": False, "message": tally_ready["error"]}

		from tally_link.tally.events import sync_party_fields_to_ledger
		tally_ledger_name = sync_party_fields_to_ledger("Supplier", supplier_name)
		frappe.db.commit()

		if not tally_ledger_name:
			return {"success": False, "message": _("Failed to create Tally Ledger for this Supplier. Check that Tally Sync is enabled in Tally Settings.")}

		from tally_link.tally.doctype_sync import sync_ledger_to_tally
		result = sync_ledger_to_tally(tally_ledger_name, operation="update")

		if result.get("success"):
			response = {"success": True, "message": _("Supplier pushed to Tally successfully.")}
			if result.get("warning"):
				response["warning"] = result["warning"]
			return response
		else:
			return {"success": False, "message": result.get("error") or _("Tally rejected the ledger.")}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Push Supplier"))
		return {"success": False, "message": str(e)}


@frappe.whitelist()
def push_payment_entry_to_tally(payment_entry_name):
	"""Push a Payment Entry from ERPNext to Tally as a Receipt or Payment Voucher."""
	try:
		import re

		pe = frappe.get_doc("Payment Entry", payment_entry_name)

		if pe.docstatus != 1:
			return {"success": False, "message": _("Only submitted Payment Entries can be pushed to Tally.")}

		client = TallyClient()
		settings = TallyClient.get_tally_settings()
		company_name = settings.get("default_company") or ""

		tally_ready = client.verify_tally_ready()
		if not tally_ready.get("ok"):
			return {"success": False, "message": tally_ready["error"]}

		def clean(account_head):
			return re.sub(r'\s*-\s*[A-Z0-9]+$', '', str(account_head or '')).strip()

		voucher_type = "Receipt" if pe.payment_type == "Receive" else "Payment"
		amount = float(pe.paid_amount or 0)
		party_ledger = pe.party_name or ""

		if pe.payment_type == "Receive":
			# Debit bank/cash, credit customer
			bank_account = clean(pe.paid_to) if pe.paid_to else "Cash"
			ledger_entries = [
				{"ledger_name": bank_account, "amount": amount, "is_debit": True},
				{"ledger_name": party_ledger, "amount": amount, "is_debit": False},
			]
		else:
			# Debit supplier, credit bank/cash
			bank_account = clean(pe.paid_from) if pe.paid_from else "Cash"
			ledger_entries = [
				{"ledger_name": party_ledger, "amount": amount, "is_debit": True},
				{"ledger_name": bank_account, "amount": amount, "is_debit": False},
			]

		d = pe.posting_date
		tally_date = d.strftime("%Y%m%d") if hasattr(d, 'strftime') else str(d).replace('-', '')

		from tally_link.tally.doctype_sync import sync_ledger_to_tally
		for entry in ledger_entries:
			tally_ledger_name = frappe.db.get_value("Tally Ledger", {"ledger_name": entry["ledger_name"]}, "name")
			if tally_ledger_name:
				sync_ledger_to_tally(tally_ledger_name, operation="create")

		response = client.create_voucher(
			voucher_type=voucher_type,
			date=tally_date,
			ledger_entries=ledger_entries,
			narration=pe.remarks or f"{voucher_type} - {party_ledger}",
			company_name=company_name,
			party_ledger=party_ledger,
		)

		import_result = _extract_import_result(response)
		line_error = import_result.get("LINEERROR")
		created = str(import_result.get("CREATED", "0")).strip()
		tally_accepted = (not line_error) and (created != "0")

		if tally_accepted:
			frappe.db.commit()
			return {"success": True, "message": _(f"{voucher_type} pushed to Tally successfully.")}
		else:
			raw_error = line_error or "Tally rejected the voucher (CREATED=0)"
			if "date is missing" in raw_error.lower() or "out of range" in raw_error.lower():
				error_msg = (
					f"Tally rejected the voucher for date {tally_date}. "
					f"Check: (1) Financial year covers this date in Tally; "
					f"(2) No date lock under F11 > Security; "
					f"(3) Company '{company_name}' is open in Tally."
				)
			else:
				error_msg = raw_error
			frappe.log_error(message=error_msg, title=_("Tally Push Failed - Payment Entry"))
			return {"success": False, "message": error_msg}

	except Exception as e:
		frappe.log_error(message=str(e), title=_("Tally API Error - Push Payment Entry"))
		return {"success": False, "message": str(e)}
