# Copyright (c) 2025, SVNIX Solutions and contributors
# For license information, please see license.txt

"""
Document event handlers for Tally integration.

Wired via hooks.py doc_events. Each function receives the Frappe document
as its first argument (and method name as second, which we ignore).

Supported flows (all ERP → Tally):
  Customer / Supplier  →  Tally Ledger  →  sync_ledger_to_tally
  Item (stock)         →  Tally Stock Item  →  sync_stock_item_to_tally
  Sales Invoice        →  Tally Voucher (Sales) → submitted → sync_voucher_to_tally
  Purchase Invoice     →  Tally Voucher (Purchase) → submitted → sync_voucher_to_tally
  Payment Entry        →  Tally Voucher (Receipt/Payment) → submitted → sync_voucher_to_tally
"""

import re
import frappe
from frappe import _


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _tally_enabled():
	"""Return True only if Tally Settings exists and is enabled."""
	try:
		if frappe.db.exists("Tally Settings", "Tally Settings"):
			return frappe.db.get_single_value("Tally Settings", "enabled")
	except Exception:
		pass
	return False


def _get_tally_settings():
	"""Return Tally Settings as a dict (never raises)."""
	try:
		return frappe.get_doc("Tally Settings", "Tally Settings").as_dict()
	except Exception:
		return {}


def _sales_ledger():
	return _get_tally_settings().get("sales_ledger") or "Sales"


def _purchase_ledger():
	return _get_tally_settings().get("purchase_ledger") or "Purchases"


def _default_uom():
	return _get_tally_settings().get("default_uom") or "Nos"


def _clean_account_name(account_head):
	"""Strip ERPNext company suffix (e.g. ' - SVNX') from account head for Tally."""
	if not account_head:
		return account_head
	return re.sub(r'\s*-\s*[A-Z0-9]+$', '', str(account_head)).strip()


def _get_primary_address(doctype, docname, doc=None):
	"""
	Return the address for a linked Customer/Supplier, as a dict:
	{"address": "<multi-line text>", "state": ..., "country": ..., "pincode": ..., "gstin": ...}

	Prefers the address explicitly set as primary on the Customer/Supplier form
	(customer_primary_address / supplier_primary_address) — this is the address
	shown on the form and what the user actually edits. Falls back to the
	Dynamic Link + is_primary_address flag only if that field is empty, since
	the flag alone can point at a stale/wrong address when multiple are linked.
	"""
	empty = {"address": "", "state": "", "country": "", "pincode": "", "gstin": ""}

	primary_address_name = None
	primary_field = "customer_primary_address" if doctype == "Customer" else "supplier_primary_address"
	if doc is not None:
		primary_address_name = doc.get(primary_field)
	else:
		primary_address_name = frappe.db.get_value(doctype, docname, primary_field)

	try:
		if primary_address_name:
			a = frappe.db.get_value(
				"Address", primary_address_name,
				["address_line1", "address_line2", "city", "state", "country", "pincode", "gstin"],
				as_dict=True,
			)
		else:
			addr_row = frappe.db.sql("""
				SELECT a.address_line1, a.address_line2, a.city, a.state, a.country, a.pincode, a.gstin
				FROM `tabAddress` a
				INNER JOIN `tabDynamic Link` dl ON dl.parent = a.name
				WHERE dl.link_doctype = %(dt)s
				  AND dl.link_name = %(dn)s
				  AND dl.parenttype = 'Address'
				  AND a.disabled = 0
				ORDER BY a.is_primary_address DESC
				LIMIT 1
			""", {"dt": doctype, "dn": docname}, as_dict=True)
			a = addr_row[0] if addr_row else None

		if a:
			return {
				"address": "\n".join(p for p in [a.address_line1, a.address_line2, a.city] if p),
				"state": a.state or "",
				"country": a.country or "",
				"pincode": a.pincode or "",
				"gstin": a.gstin or "",
			}
	except Exception:
		pass
	return empty


def _create_tally_voucher(voucher_type, doc_name, posting_date, party_name,
						  ledger_entries, narration, linked_doctype, linked_docname):
	"""
	Insert + submit a Tally Voucher doc. Returns the doc or None on failure.
	Submission triggers TallyVoucher.on_submit → sync_voucher_to_tally.
	"""
	from tally_link.tally.doctype_sync import create_sync_log

	# Skip if already pushed
	if frappe.db.exists("Tally Voucher", {"reference_number": doc_name}):
		frappe.logger("tally_sync").info(f"Tally Voucher already exists for {doc_name}, skipping.")
		return None

	try:
		tv = frappe.get_doc({
			"doctype": "Tally Voucher",
			"voucher_type": voucher_type,
			"date": posting_date,
			"party_ledger_name": party_name,
			"narration": narration,
			"reference_number": doc_name,
			"reference_date": posting_date,
			"linked_doctype": linked_doctype,
			"linked_docname": linked_docname,
			"auto_sync": 1,
			"sync_direction": "ERP to Tally",
		})
		for entry in ledger_entries:
			tv.append("ledger_entries", entry)

		tv.insert(ignore_permissions=True)
		tv.submit()
		return tv
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_(f"Tally Voucher Creation Failed for {linked_doctype} {doc_name}")
		)
		create_sync_log(
			sync_type="Transaction",
			operation="Create",
			status="Failed",
			direction="ERP to Tally",
			entity_type="Voucher",
			entity_name=doc_name,
			reference_doctype=linked_doctype,
			reference_name=doc_name,
			error_message=str(e),
		)
		return None


def _party_ledger_fields(doc, party_type):
	"""Build the Tally Ledger field values for a Customer/Supplier, including address/GSTIN."""
	name_field = "customer_name" if party_type == "Customer" else "supplier_name"
	addr = _get_primary_address(party_type, doc.name, doc=doc)
	return {
		"mobile": doc.get("mobile_no") or "",
		"email": doc.get("email_id") or "",
		"gstin": doc.get("gstin") or addr["gstin"] or "",
		"pan": doc.get("pan") or "",
		"address": addr["address"],
		"state": addr["state"],
		"country": addr["country"],
		"pincode": addr["pincode"],
		"mailing_name": doc.get(name_field),
	}


def sync_party_fields_to_ledger(doctype, docname):
	"""
	Refresh a Customer/Supplier's linked Tally Ledger with current address/GSTIN/PAN/contact
	details. Creates the ledger if it doesn't exist yet. Returns the Tally Ledger docname,
	or None if Tally sync is disabled or creation failed.
	"""
	if not _tally_enabled():
		return None

	doc = frappe.get_doc(doctype, docname)
	name_field = "customer_name" if doctype == "Customer" else "supplier_name"
	ledger_name = doc.get(name_field)

	if not frappe.db.exists("Tally Ledger", ledger_name):
		frappe.flags.in_tally_synchronous_push = True
		try:
			if doctype == "Customer":
				customer_after_insert(doc)
			else:
				supplier_after_insert(doc)
		finally:
			frappe.flags.in_tally_synchronous_push = False
		return frappe.db.get_value("Tally Ledger", {"ledger_name": ledger_name}, "name")

	ledger = frappe.get_doc("Tally Ledger", ledger_name)
	fields = _party_ledger_fields(doc, doctype)
	changed = False
	for field, val in fields.items():
		if val and getattr(ledger, field) != val:
			setattr(ledger, field, val)
			changed = True

	if changed:
		ledger.save(ignore_permissions=True)

	return ledger.name


# ─────────────────────────────────────────────────────────────
# Customer  →  Tally Ledger
# ─────────────────────────────────────────────────────────────

def customer_after_insert(doc, method=None):
	"""Create a Tally Ledger for a new Customer and queue sync to Tally."""
	if not _tally_enabled():
		return

	if frappe.db.exists("Tally Ledger", doc.customer_name):
		return

	try:
		addr = _get_primary_address("Customer", doc.name, doc=doc)
		tally_ledger = frappe.get_doc({
			"doctype": "Tally Ledger",
			"ledger_name": doc.customer_name,
			"parent_group": "Sundry Debtors",
			"mailing_name": doc.customer_name,
			"address": addr["address"],
			"state": addr["state"],
			"country": addr["country"],
			"pincode": addr["pincode"],
			"mobile": doc.get("mobile_no") or "",
			"email": doc.get("email_id") or "",
			"gstin": doc.get("gstin") or addr["gstin"] or "",
			"pan": doc.get("pan") or "",
			"linked_doctype": "Customer",
			"linked_docname": doc.name,
			"auto_sync": 1,
			"sync_direction": "ERP to Tally",
			"sync_status": "Pending",
		})
		tally_ledger.insert(ignore_permissions=True)
		# TallyLedger.after_insert auto-enqueues sync_ledger_to_tally
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_("Tally Ledger Creation Failed for Customer {0}").format(doc.name)
		)


def customer_on_update(doc, method=None):
	"""Propagate Customer name/contact changes to its Tally Ledger."""
	if not _tally_enabled():
		return

	if not frappe.db.exists("Tally Ledger", doc.customer_name):
		customer_after_insert(doc, method)
		return

	try:
		ledger = frappe.get_doc("Tally Ledger", doc.customer_name)
		changed = False

		for erp_field, ledger_field in [("mobile_no", "mobile"), ("email_id", "email"), ("gstin", "gstin"), ("pan", "pan")]:
			val = doc.get(erp_field)
			if val and getattr(ledger, ledger_field) != val:
				setattr(ledger, ledger_field, val)
				changed = True

		addr = _get_primary_address("Customer", doc.name, doc=doc)
		for ledger_field in ("address", "state", "country", "pincode"):
			val = addr[ledger_field]
			if val and getattr(ledger, ledger_field) != val:
				setattr(ledger, ledger_field, val)
				changed = True

		if changed:
			ledger.save(ignore_permissions=True)
			frappe.enqueue(
				"tally_link.tally.doctype_sync.sync_ledger_to_tally",
				queue="short", timeout=300, enqueue_after_commit=True,
				ledger_name=ledger.name, operation="update",
			)
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_("Tally Ledger Update Failed for Customer {0}").format(doc.name)
		)


# ─────────────────────────────────────────────────────────────
# Supplier  →  Tally Ledger
# ─────────────────────────────────────────────────────────────

def supplier_after_insert(doc, method=None):
	"""Create a Tally Ledger for a new Supplier and queue sync to Tally."""
	if not _tally_enabled():
		return

	if frappe.db.exists("Tally Ledger", doc.supplier_name):
		return

	try:
		addr = _get_primary_address("Supplier", doc.name, doc=doc)
		tally_ledger = frappe.get_doc({
			"doctype": "Tally Ledger",
			"ledger_name": doc.supplier_name,
			"parent_group": "Sundry Creditors",
			"mailing_name": doc.supplier_name,
			"address": addr["address"],
			"state": addr["state"],
			"country": addr["country"],
			"pincode": addr["pincode"],
			"mobile": doc.get("mobile_no") or "",
			"email": doc.get("email_id") or "",
			"gstin": doc.get("gstin") or addr["gstin"] or "",
			"pan": doc.get("pan") or "",
			"linked_doctype": "Supplier",
			"linked_docname": doc.name,
			"auto_sync": 1,
			"sync_direction": "ERP to Tally",
			"sync_status": "Pending",
		})
		tally_ledger.insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_("Tally Ledger Creation Failed for Supplier {0}").format(doc.name)
		)


def supplier_on_update(doc, method=None):
	"""Propagate Supplier contact changes to its Tally Ledger."""
	if not _tally_enabled():
		return

	if not frappe.db.exists("Tally Ledger", doc.supplier_name):
		supplier_after_insert(doc, method)
		return

	try:
		ledger = frappe.get_doc("Tally Ledger", doc.supplier_name)
		changed = False

		for erp_field, ledger_field in [("mobile_no", "mobile"), ("email_id", "email"), ("gstin", "gstin"), ("pan", "pan")]:
			val = doc.get(erp_field)
			if val and getattr(ledger, ledger_field) != val:
				setattr(ledger, ledger_field, val)
				changed = True

		addr = _get_primary_address("Supplier", doc.name, doc=doc)
		for ledger_field in ("address", "state", "country", "pincode"):
			val = addr[ledger_field]
			if val and getattr(ledger, ledger_field) != val:
				setattr(ledger, ledger_field, val)
				changed = True

		if changed:
			ledger.save(ignore_permissions=True)
			frappe.enqueue(
				"tally_link.tally.doctype_sync.sync_ledger_to_tally",
				queue="short", timeout=300, enqueue_after_commit=True,
				ledger_name=ledger.name, operation="update",
			)
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_("Tally Ledger Update Failed for Supplier {0}").format(doc.name)
		)


# ─────────────────────────────────────────────────────────────
# Item  →  Tally Stock Item
# ─────────────────────────────────────────────────────────────

def item_after_insert(doc, method=None):
	"""Create a Tally Stock Item for a new stock Item."""
	if not _tally_enabled():
		return

	if not doc.is_stock_item:
		return

	if frappe.db.exists("Tally Stock Item", doc.item_name):
		return

	try:
		tally_item = frappe.get_doc({
			"doctype": "Tally Stock Item",
			"item_name": doc.item_name,
			"parent_group": doc.item_group or "Primary",
			"category": doc.item_group or "Primary",
			"base_units": doc.stock_uom or _default_uom(),
			"hsn_code": doc.get("gst_hsn_code") or "",
			"linked_doctype": "Item",
			"linked_docname": doc.name,
			"auto_sync": 1,
			"sync_direction": "ERP to Tally",
			"sync_status": "Pending",
		})
		tally_item.insert(ignore_permissions=True)
		# TallyStockItem.after_insert auto-enqueues sync_stock_item_to_tally
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_("Tally Stock Item Creation Failed for Item {0}").format(doc.name)
		)


def item_on_update(doc, method=None):
	"""Propagate Item name/group changes to its Tally Stock Item."""
	if not _tally_enabled():
		return

	if not doc.is_stock_item:
		return

	if not frappe.db.exists("Tally Stock Item", doc.item_name):
		item_after_insert(doc, method)
		return

	try:
		tally_item = frappe.get_doc("Tally Stock Item", doc.item_name)
		changed = False

		if doc.get("gst_hsn_code") and tally_item.hsn_code != doc.gst_hsn_code:
			tally_item.hsn_code = doc.gst_hsn_code
			changed = True
		if doc.item_group and tally_item.category != doc.item_group:
			tally_item.category = doc.item_group
			changed = True

		if changed:
			tally_item.save(ignore_permissions=True)
			frappe.enqueue(
				"tally_link.tally.doctype_sync.sync_stock_item_to_tally",
				queue="short", timeout=300, enqueue_after_commit=True,
				item_name=tally_item.name, operation="update",
			)
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_("Tally Stock Item Update Failed for Item {0}").format(doc.name)
		)


# ─────────────────────────────────────────────────────────────
# Sales Invoice  →  Tally Voucher (Sales)
# ─────────────────────────────────────────────────────────────

def sales_invoice_on_submit(doc, method=None):
	"""On Sales Invoice submission, ensure customer ledger exists then push voucher."""
	if not _tally_enabled():
		return

	# Ensure Tally Ledger exists for the customer
	if not frappe.db.exists("Tally Ledger", doc.customer_name):
		customer_doc = frappe.get_doc("Customer", doc.customer) if doc.customer else None
		if customer_doc:
			customer_after_insert(customer_doc)

	frappe.enqueue(
		"tally_link.tally.events._push_sales_invoice",
		queue="short", timeout=300, enqueue_after_commit=True,
		sales_invoice_name=doc.name,
	)


@frappe.whitelist()
def _push_sales_invoice(sales_invoice_name):
	"""Background job / manual trigger: create + submit a Tally Voucher for a Sales Invoice."""
	si = frappe.get_doc("Sales Invoice", sales_invoice_name)

	posting_date = si.posting_date

	# Build per-item income entries from invoice items (income_account per line)
	# Group by income account so we collapse multiple lines with the same account
	income_by_account = {}
	for item in si.items or []:
		acct = _clean_account_name(item.income_account) if item.income_account else _sales_ledger()
		income_by_account[acct] = income_by_account.get(acct, 0) + float(item.amount or 0)

	# If no per-item income accounts found, fall back to configured sales ledger
	if not income_by_account:
		income_by_account[_sales_ledger()] = float(si.total or 0)

	ledger_entries = [
		{"ledger_name": si.customer_name, "amount": float(si.grand_total or 0), "is_debit": 1},
	]
	for acct, amt in income_by_account.items():
		ledger_entries.append({"ledger_name": acct, "amount": amt, "is_debit": 0})

	for tax in si.taxes or []:
		if tax.tax_amount:
			ledger_entries.append({
				"ledger_name": _clean_account_name(tax.account_head),
				"amount": float(tax.tax_amount),
				"is_debit": 0,
			})

	frappe.logger("tally_sync").info(
		f"[SI Push] {sales_invoice_name}: date={posting_date}, entries={ledger_entries}"
	)

	tv = _create_tally_voucher(
		voucher_type="Sales",
		doc_name=sales_invoice_name,
		posting_date=posting_date,
		party_name=si.customer_name,
		ledger_entries=ledger_entries,
		narration=f"Sales Invoice {si.name} - {si.customer_name}",
		linked_doctype="Sales Invoice",
		linked_docname=si.name,
	)
	if tv:
		si.db_set("tally_voucher_number", tv.name, update_modified=False)
		frappe.db.commit()


def sales_invoice_on_cancel(doc, method=None):
	"""Cancel the corresponding Tally Voucher when a Sales Invoice is cancelled."""
	if not _tally_enabled():
		return

	frappe.enqueue(
		"tally_link.tally.events._cancel_voucher_for_doc",
		queue="short", timeout=300, enqueue_after_commit=True,
		linked_doctype="Sales Invoice",
		linked_docname=doc.name,
	)


# ─────────────────────────────────────────────────────────────
# Purchase Invoice  →  Tally Voucher (Purchase)
# ─────────────────────────────────────────────────────────────

def purchase_invoice_on_submit(doc, method=None):
	"""On Purchase Invoice submission, ensure supplier ledger exists then push voucher."""
	if not _tally_enabled():
		return

	if not frappe.db.exists("Tally Ledger", doc.supplier_name):
		supplier_doc = frappe.get_doc("Supplier", doc.supplier) if doc.supplier else None
		if supplier_doc:
			supplier_after_insert(supplier_doc)

	frappe.enqueue(
		"tally_link.tally.events._push_purchase_invoice",
		queue="short", timeout=300, enqueue_after_commit=True,
		purchase_invoice_name=doc.name,
	)


@frappe.whitelist()
def _push_purchase_invoice(purchase_invoice_name):
	"""Background job / manual trigger: create + submit a Tally Voucher for a Purchase Invoice."""
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice_name)

	# Build per-item expense entries from invoice items
	expense_by_account = {}
	for item in pi.items or []:
		acct = _clean_account_name(item.expense_account) if item.expense_account else _purchase_ledger()
		expense_by_account[acct] = expense_by_account.get(acct, 0) + float(item.amount or 0)

	if not expense_by_account:
		expense_by_account[_purchase_ledger()] = float(pi.total or 0)

	ledger_entries = []
	for acct, amt in expense_by_account.items():
		ledger_entries.append({"ledger_name": acct, "amount": amt, "is_debit": 1})

	for tax in pi.taxes or []:
		if tax.tax_amount:
			ledger_entries.append({
				"ledger_name": _clean_account_name(tax.account_head),
				"amount": float(tax.tax_amount),
				"is_debit": 1,
			})
	ledger_entries.append(
		{"ledger_name": pi.supplier_name, "amount": float(pi.grand_total or 0), "is_debit": 0}
	)

	frappe.logger("tally_sync").info(
		f"[PI Push] {purchase_invoice_name}: date={pi.posting_date}, entries={ledger_entries}"
	)

	tv = _create_tally_voucher(
		voucher_type="Purchase",
		doc_name=purchase_invoice_name,
		posting_date=pi.posting_date,
		party_name=pi.supplier_name,
		ledger_entries=ledger_entries,
		narration=f"Purchase Invoice {pi.name} - {pi.supplier_name}",
		linked_doctype="Purchase Invoice",
		linked_docname=pi.name,
	)
	if tv:
		pi.db_set("tally_voucher_number", tv.name, update_modified=False)
		frappe.db.commit()


def purchase_invoice_on_cancel(doc, method=None):
	"""Cancel the Tally Voucher when a Purchase Invoice is cancelled."""
	if not _tally_enabled():
		return

	frappe.enqueue(
		"tally_link.tally.events._cancel_voucher_for_doc",
		queue="short", timeout=300, enqueue_after_commit=True,
		linked_doctype="Purchase Invoice",
		linked_docname=doc.name,
	)


# ─────────────────────────────────────────────────────────────
# Payment Entry  →  Tally Voucher (Receipt / Payment)
# ─────────────────────────────────────────────────────────────

def payment_entry_on_submit(doc, method=None):
	"""On Payment Entry submission, push as Receipt or Payment voucher to Tally."""
	if not _tally_enabled():
		return

	frappe.enqueue(
		"tally_link.tally.events._push_payment_entry",
		queue="short", timeout=300, enqueue_after_commit=True,
		payment_entry_name=doc.name,
	)


@frappe.whitelist()
def _push_payment_entry(payment_entry_name):
	"""Background job / manual trigger: create + submit a Tally Voucher for a Payment Entry."""
	pe = frappe.get_doc("Payment Entry", payment_entry_name)

	# Receipt = money received from customer; Payment = money paid to supplier
	voucher_type = "Receipt" if pe.payment_type == "Receive" else "Payment"
	party_ledger = pe.party_name or "Cash"
	amount = float(pe.paid_amount or 0)

	if pe.payment_type == "Receive":
		# Debit bank/cash account, Credit party (customer)
		bank_account = _clean_account_name(pe.paid_to) if pe.paid_to else "Cash"
		ledger_entries = [
			{"ledger_name": bank_account, "amount": amount, "is_debit": 1},
			{"ledger_name": party_ledger, "amount": amount, "is_debit": 0},
		]
	else:
		# Debit party (supplier), Credit bank/cash account
		bank_account = _clean_account_name(pe.paid_from) if pe.paid_from else "Cash"
		ledger_entries = [
			{"ledger_name": party_ledger, "amount": amount, "is_debit": 1},
			{"ledger_name": bank_account, "amount": amount, "is_debit": 0},
		]

	narration = pe.remarks or f"{voucher_type} - {party_ledger}"
	frappe.logger("tally_sync").info(
		f"[PE Push] {payment_entry_name}: type={voucher_type}, entries={ledger_entries}"
	)

	tv = _create_tally_voucher(
		voucher_type=voucher_type,
		doc_name=payment_entry_name,
		posting_date=pe.posting_date,
		party_name=party_ledger,
		ledger_entries=ledger_entries,
		narration=narration,
		linked_doctype="Payment Entry",
		linked_docname=pe.name,
	)
	if tv:
		pe.db_set("tally_voucher_number", tv.name, update_modified=False)
		frappe.db.commit()


def payment_entry_on_cancel(doc, method=None):
	"""Cancel the Tally Voucher when a Payment Entry is cancelled."""
	if not _tally_enabled():
		return

	frappe.enqueue(
		"tally_link.tally.events._cancel_voucher_for_doc",
		queue="short", timeout=300, enqueue_after_commit=True,
		linked_doctype="Payment Entry",
		linked_docname=doc.name,
	)


# ─────────────────────────────────────────────────────────────
# Reverse Sync: Tally Ledger → Customer (Tally-to-ERP)
# ─────────────────────────────────────────────────────────────

def tally_ledger_after_insert(doc, method=None):
	"""
	When a Tally Ledger is synced FROM Tally (sync_direction = Tally to ERP),
	auto-create or link a Customer/Supplier in ERPNext.
	"""
	if doc.sync_direction not in ("Tally to ERP", "Bidirectional"):
		return
	if doc.linked_doctype and doc.linked_docname:
		return  # already linked

	if doc.parent_group == "Sundry Debtors":
		_upsert_customer_from_ledger(doc)
	elif doc.parent_group == "Sundry Creditors":
		_upsert_supplier_from_ledger(doc)


def _upsert_customer_from_ledger(ledger):
	try:
		existing = frappe.db.get_value("Customer", {"customer_name": ledger.ledger_name}, "name")
		if existing:
			customer = frappe.get_doc("Customer", existing)
		else:
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": ledger.ledger_name,
				"customer_type": "Company",
				"customer_group": "Commercial",
				"territory": "All Territories",
			})

		if ledger.mobile:
			customer.mobile_no = ledger.mobile
		if ledger.email:
			customer.email_id = ledger.email
		if ledger.gstin:
			customer.tax_id = ledger.gstin
		if ledger.pan:
			customer.pan = ledger.pan

		if customer.is_new():
			customer.insert(ignore_permissions=True)
		else:
			customer.save(ignore_permissions=True)

		ledger.db_set("linked_doctype", "Customer", update_modified=False)
		ledger.db_set("linked_docname", customer.name, update_modified=False)
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Customer Sync from Tally Failed for {0}").format(ledger.name))


def _upsert_supplier_from_ledger(ledger):
	try:
		existing = frappe.db.get_value("Supplier", {"supplier_name": ledger.ledger_name}, "name")
		if existing:
			supplier = frappe.get_doc("Supplier", existing)
		else:
			supplier = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": ledger.ledger_name,
				"supplier_type": "Company",
				"supplier_group": "All Supplier Groups",
			})

		if ledger.mobile:
			supplier.mobile_no = ledger.mobile
		if ledger.email:
			supplier.email_id = ledger.email
		if ledger.gstin:
			supplier.tax_id = ledger.gstin
		if ledger.pan:
			supplier.pan = ledger.pan

		if supplier.is_new():
			supplier.insert(ignore_permissions=True)
		else:
			supplier.save(ignore_permissions=True)

		ledger.db_set("linked_doctype", "Supplier", update_modified=False)
		ledger.db_set("linked_docname", supplier.name, update_modified=False)
	except Exception as e:
		frappe.log_error(message=str(e), title=_("Supplier Sync from Tally Failed for {0}").format(ledger.name))


# ─────────────────────────────────────────────────────────────
# Shared: cancel a Tally Voucher linked to an ERP doc
# ─────────────────────────────────────────────────────────────

@frappe.whitelist()
def _cancel_voucher_for_doc(linked_doctype, linked_docname):
	"""
	Background job: find the Tally Voucher linked to an ERP document
	and cancel it both in Tally and locally.
	"""
	from tally_link.tally.doctype_sync import cancel_voucher_in_tally

	voucher_name = frappe.db.get_value(
		"Tally Voucher",
		{"reference_number": linked_docname},
		"name"
	)
	if not voucher_name:
		frappe.logger("tally_sync").warning(
			f"No Tally Voucher found for {linked_doctype} {linked_docname} — skipping cancel"
		)
		return

	try:
		cancel_voucher_in_tally(voucher_name)
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title=_(f"Tally Cancel Failed for {linked_doctype} {linked_docname}")
		)


# ─────────────────────────────────────────────────────────────
# Tally Stock Item  →  ERPNext Item (reverse sync on save)
# ─────────────────────────────────────────────────────────────

def tally_stock_item_on_update(doc, method=None):
	"""When a Tally Stock Item is saved (any direction), ensure an ERPNext Item exists."""
	from tally_link.tally.doctype_sync import _upsert_erpnext_item
	if doc.linked_doctype and doc.linked_docname:
		return  # already linked, nothing to do
	try:
		_upsert_erpnext_item(doc)
	except Exception as e:
		frappe.log_error(message=str(e), title=_("ERPNext Item Sync Failed for {0}").format(doc.name))
