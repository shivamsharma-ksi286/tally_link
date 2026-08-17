"""
Tally Client Wrapper for Frappe/ERPNext Integration

This module provides a Frappe-friendly wrapper around the TallyClient,
handling connection management, error handling, and data transformation.
"""

import frappe
from frappe import _
from tally_link.tally.xml_client import TallyXmlClient as BaseTallyClient


class TallyClient:
	"""
	Wrapper class for TallyClient that integrates with Frappe's settings and error handling.
	"""

	def __init__(self, host=None, port=None, timeout=30):
		"""
		Initialize Tally Client with settings from Frappe

		Args:
			host: Tally server host (defaults to settings or localhost)
			port: Tally server port (defaults to settings or 9000)
			timeout: Request timeout in seconds (defaults to 30)
		"""
		# Get settings from Tally Settings doctype if not provided
		if not host or not port:
			settings = self.get_tally_settings()
			host = host or settings.get("host", "localhost")
			port = port or settings.get("port", 9000)

		# Format host as URL if not already
		if not host.startswith("http"):
			tally_url = f"http://{host}"
		else:
			tally_url = host

		try:
			self.client = BaseTallyClient(tally_url=tally_url, tally_port=int(port), timeout=timeout)
		except Exception as e:
			frappe.throw(_("Failed to initialize Tally Client: {0}").format(str(e)))

	@staticmethod
	def get_tally_settings():
		"""
		Get Tally integration settings from Frappe

		Returns:
			dict: Tally settings
		"""
		try:
			if frappe.db.exists("Tally Settings", "Tally Settings"):
				settings = frappe.get_doc("Tally Settings", "Tally Settings")
				# default_company is a child table (Tally Comapny rows); use the first entry
				default_company = ""
				if settings.default_company:
					default_company = settings.default_company[0].tally_company or ""
				return {
					"host": settings.host or "localhost",
					"port": settings.port or 9000,
					"enabled": settings.enabled,
					"default_company": default_company,
				}
		except Exception:
			pass

		return {"host": "localhost", "port": 9000, "enabled": False, "default_company": ""}

	def get_last_xml_request(self):
		"""Proxy to get the last XML request sent to Tally"""
		return self.client.get_last_xml_request()

	@staticmethod
	def _convert_tally_date(date_str):
		"""
		Convert Tally date format (YYYYMMDD) to Frappe format (YYYY-MM-DD)

		Args:
			date_str: Date string in YYYYMMDD format

		Returns:
			str: Date in YYYY-MM-DD format or None
		"""
		if not date_str or len(date_str) != 8:
			return None
		try:
			return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
		except Exception:
			return None

	@staticmethod
	def _extract_value(value, default=""):
		"""
		Extract scalar value from potentially nested dictionary structure.

		When XML elements have both text content and child elements/attributes,
		the parser returns a dict with '_text' key. This helper extracts the
		actual text value.

		Args:
			value: Value to extract (can be str, int, float, dict, or None)
			default: Default value if extraction fails

		Returns:
			Scalar value (str, int, float) or default
		"""
		if value is None:
			return default

		# If it's already a scalar value, return as-is
		if isinstance(value, (str, int, float, bool)):
			return value

		# If it's a dict, try to extract _text key
		if isinstance(value, dict):
			# Try _text key first (text content with child elements)
			if '_text' in value:
				return value['_text']
			# If no _text, might be empty element
			return default

		# For any other type, convert to string or return default
		try:
			return str(value)
		except Exception:
			return default

	@staticmethod
	def _extract_numeric_value(value, default=0):
		"""
		Extract numeric value from Tally formatted strings.

		Tally returns values like "234567 Nos", "9.48/Nos", "-2,111,103.00"
		This function extracts the numeric part.

		Args:
			value: Value to extract (can be str, int, float, dict, or None)
			default: Default value if extraction fails (default: 0)

		Returns:
			float: Numeric value or default
		"""
		if value is None:
			return default

		# If already numeric, return as-is
		if isinstance(value, (int, float)):
			return float(value)

		# If it's a dict, try to extract _text key first
		if isinstance(value, dict):
			value = value.get('_text', value)

		# Convert to string for parsing
		if not isinstance(value, str):
			try:
				return float(value)
			except (ValueError, TypeError):
				return default

		# Remove commas and extract numeric part
		# Handle formats like: "234567 Nos", "9.48/Nos", "-2,111,103.00", "123.45"
		import re
		# Remove commas
		value = value.replace(',', '')
		# Extract first number (including negative sign and decimal)
		match = re.search(r'-?\d+\.?\d*', value)
		if match:
			try:
				return float(match.group())
			except ValueError:
				return default

		return default

	def test_connection(self):
		"""
		Test connection to Tally server

		Returns:
			bool: True if connection successful, False otherwise
		"""
		try:
			return self.client.test_connection()
		except Exception as e:
			frappe.log_error(
				message=str(e), title=_("Tally Connection Error")
			)
			return False

	def verify_tally_ready(self, company_name=None):
		"""
		Verify Tally is reachable and responding.

		Uses a Collection query (ledger list) which always returns data when Tally is running,
		regardless of whether a specific company is active or has any transactions.

		Returns:
			dict: {"ok": True} or {"ok": False, "error": "<human-readable reason>"}
		"""
		try:
			settings = self.get_tally_settings()
			co = company_name or settings.get("default_company") or ""
			# Collection query — returns ledger names; works even if company has no transactions
			xml = (
				"<ENVELOPE>"
				"<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>"
				"<BODY><EXPORTDATA><REQUESTDESC>"
				"<STATICVARIABLES>"
				f"<SVCURRENTCOMPANY>{co}</SVCURRENTCOMPANY>"
				"</STATICVARIABLES>"
				"<REQUESTDATA><TALLYMESSAGE>"
				"<COLLECTION ISMODIFY=\"No\" ISFIXED=\"No\" ISOPTION=\"No\" ISINTERNAL=\"No\">"
				"<TYPE>Ledger</TYPE><FETCH>NAME</FETCH>"
				"</COLLECTION>"
				"</TALLYMESSAGE></REQUESTDATA>"
				"</REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>"
			)
			resp = self.client._send_request(xml)
			if not resp:
				return {"ok": False, "error": "No response from Tally server. Check that Tally is running and the ngrok tunnel is active."}
			resp_lower = resp.lower()
			# ngrok / HTTP error pages
			if "404 not found" in resp_lower or "503 service" in resp_lower or (
				"ngrok" in resp_lower and "<envelope>" not in resp_lower
			):
				return {"ok": False, "error": "Cannot reach Tally server. Verify the ngrok tunnel is running and Tally is open."}
			# Any XML from Tally = Tally is up and responding
			if "<envelope>" in resp_lower or "<envelope/" in resp_lower or "<response>" in resp_lower:
				return {"ok": True}
			# Non-XML response (HTML error page, etc.)
			return {"ok": False, "error": f"Tally returned an unexpected response. Raw: {resp[:200]}"}
		except Exception as e:
			return {"ok": False, "error": f"Tally connection error: {str(e)}"}

	def get_current_company(self):
		"""
		Get current company information from Tally

		Returns:
			dict: Company information
		"""
		try:
			xml_response = self.client.get_current_company()
			return self.client.parse_xml_response(xml_response)
		except Exception as e:
			frappe.throw(_("Failed to get company info: {0}").format(str(e)))

	def get_companies(self):
		"""
		Get list of all companies in Tally

		Returns:
			list: List of company dictionaries
		"""
		try:
			xml_response = self.client.get_companies_list()
			parsed = self.client.parse_xml_response(xml_response)
			# Extract companies from parsed response
			companies = parsed.get("ENVELOPE", {}).get("BODY", {}).get("DATA", {}).get("COLLECTION", {}).get("COMPANY", [])
			if isinstance(companies, dict):
				companies = [companies]
			return companies
		except Exception as e:
			frappe.throw(_("Failed to get companies: {0}").format(str(e)))

	def get_ledgers(self, company=None):
		"""
		Get all ledgers from Tally

		Args:
			company: Company name (optional)

		Returns:
			list: List of ledger dictionaries
		"""
		try:
			xml_response = self.client.get_ledgers_list(company_name=company)
			parsed = self.client.parse_xml_response(xml_response)

			# Check if parsed response is valid
			if not isinstance(parsed, dict):
				frappe.throw(_("Invalid response from Tally: {0}").format(str(parsed)))

			# Extract ledgers from parsed response - structure may vary
			# Try different possible paths in the XML structure
			ledgers = []

			envelope = parsed.get("ENVELOPE", parsed)
			body = envelope.get("BODY", envelope)
			data = body.get("DATA", body)
			collection = data.get("COLLECTION", data)

			# Ledgers might be under LEDGER key
			ledger_data = collection.get("LEDGER", [])
			if isinstance(ledger_data, dict):
				ledger_data = [ledger_data]

			for ledger in ledger_data:
				# Address/state/country/mailing name/pincode live under
				# LEDMAILINGDETAILS.LIST in current TallyPrime versions — the legacy
				# flat tags (ADDRESS/STATENAME/COUNTRYOFRESIDENCE/MAILINGNAME) are
				# no longer populated by Tally at all. Fall back to them only if
				# mailing details aren't present (older Tally versions).
				mailing_details = ledger.get("LEDMAILINGDETAILS.LIST") or {}
				if isinstance(mailing_details, list):
					mailing_details = mailing_details[0] if mailing_details else {}

				address_value = self._extract_value(mailing_details.get("ADDRESS.LIST", ""))
				if not address_value:
					address_list = mailing_details.get("ADDRESS.LIST")
					if isinstance(address_list, dict):
						addr_lines = address_list.get("ADDRESS", "")
						if isinstance(addr_lines, list):
							address_value = "\n".join(self._extract_value(a) for a in addr_lines if a)
						else:
							address_value = self._extract_value(addr_lines)
				if not address_value:
					address_value = self._extract_value(ledger.get("ADDRESS", ""))

				state_value = self._extract_value(mailing_details.get("STATE", "")) or self._extract_value(ledger.get("STATENAME", ""))
				country_value = self._extract_value(mailing_details.get("COUNTRY", "")) or self._extract_value(ledger.get("COUNTRYOFRESIDENCE", ""))
				pincode_value = self._extract_value(mailing_details.get("PINCODE", ""))
				mailing_name_value = self._extract_value(mailing_details.get("MAILINGNAME", "")) or self._extract_value(ledger.get("MAILINGNAME", ""))

				ledgers.append({
					"name": self._extract_value(ledger.get("NAME", ledger.get("@NAME", ""))),
					"parent": self._extract_value(ledger.get("PARENT", "")),
					"guid": self._extract_value(ledger.get("GUID", "")),
					"opening_balance": self._extract_numeric_value(ledger.get("OPENINGBALANCE", 0)),
					"closing_balance": self._extract_numeric_value(ledger.get("CLOSINGBALANCE", 0)),
					"address": address_value,
					"state": state_value,
					"country": country_value,
					"pincode": pincode_value,
					"mailing_name": mailing_name_value,
					"mobile": self._extract_value(ledger.get("LEDGERPHONE", ledger.get("MOBILE", ""))),
					"email": self._extract_value(ledger.get("EMAIL", "")),
					"gstin": self._extract_value(ledger.get("PARTYGSTIN", ledger.get("GSTIN", ""))),
					"pan": self._extract_value(ledger.get("INCOMETAXNUMBER", ledger.get("PAN", ""))),
				})

			return ledgers
		except Exception as e:
			frappe.throw(_("Failed to get ledgers: {0}").format(str(e)))

	def create_ledger(self, name, parent, address=None, country=None, state=None, pincode=None,
					  mobile=None, gstin=None, pan=None, email=None, mailing_name=None,
					  company_name=None, action="Create", **kwargs):
		"""
		Create or update a ledger in Tally

		Args:
			name: Ledger name
			parent: Parent ledger group
			address: Address (optional) — multi-line supported
			country: Country of residence (optional)
			state: State name (optional)
			pincode: Postal/PIN code (optional) — required for Tally to persist
				address/state/country/mailing name at all (see xml_client.create_ledger)
			mobile: Mobile number (optional)
			gstin: GSTIN (optional)
			pan: PAN / Income Tax number (optional)
			email: Email address (optional)
			mailing_name: Mailing name (optional)
			company_name: Tally company name (optional)
			action: "Create" or "Alter" — use "Alter" if the ledger already exists in Tally
			**kwargs: Additional ledger properties

		Returns:
			dict: Response from Tally
		"""
		try:
			xml_response = self.client.create_ledger(
				name=name,
				parent=parent,
				address=address,
				country=country,
				state=state,
				pincode=pincode,
				mobile=mobile,
				gstin=gstin,
				pan=pan,
				email=email,
				mailing_name=mailing_name,
				company_name=company_name,
				action=action,
			)
			return self.client.parse_xml_response(xml_response)
		except Exception as e:
			frappe.throw(_("Failed to create ledger: {0}").format(str(e)))

	def get_stock_items(self, company=None):
		"""
		Get all stock items from Tally

		Args:
			company: Company name (optional)

		Returns:
			list: List of stock item dictionaries
		"""
		try:
			xml_response = self.client.get_stock_items_list()
			parsed = self.client.parse_xml_response(xml_response)

			# Check if parsed response is valid
			if not isinstance(parsed, dict):
				frappe.log_error(
					message=f"Invalid response from Tally: {parsed}",
					title=_("Failed to get stock items")
				)
				return []

			# Extract stock items from parsed response
			stock_items = []
			envelope = parsed.get("ENVELOPE", parsed)
			body = envelope.get("BODY", envelope)
			data = body.get("DATA", body)
			collection = data.get("COLLECTION", data)

			# Stock items might be under STOCKITEM key
			item_data = collection.get("STOCKITEM", [])
			if isinstance(item_data, dict):
				item_data = [item_data]

			for item in item_data:
				stock_items.append({
					"name": self._extract_value(item.get("NAME", item.get("@NAME", ""))),
					"alias": self._extract_value(item.get("ALIAS", "")),
					"guid": self._extract_value(item.get("GUID", "")),
					"master_id": self._extract_value(item.get("MASTERID", "")),
					"parent": self._extract_value(item.get("PARENT", "")),
					"base_units": self._extract_value(item.get("BASEUNITS", "")),
					"opening_balance": self._extract_numeric_value(item.get("OPENINGBALANCE", 0)),
					"opening_rate": self._extract_numeric_value(item.get("OPENINGRATE", 0)),
					"opening_value": self._extract_numeric_value(item.get("OPENINGVALUE", 0)),
					"current_balance": self._extract_numeric_value(item.get("CLOSINGBALANCE", 0)),
					"current_rate": self._extract_numeric_value(item.get("CLOSINGRATE", 0)),
					"current_value": self._extract_numeric_value(item.get("CLOSINGVALUE", 0)),
					"hsn_code": self._extract_value(item.get("HSNCODE", "")),
					"gst_applicable": self._extract_value(item.get("GSTAPPLICABLE", "No")),
					"gst_rate": self._extract_value(item.get("TAXCLASSIFICATIONNAME", "")),
				})

			return stock_items
		except Exception as e:
			frappe.log_error(message=str(e), title=_("Failed to get stock items"))
			return []

	def create_stock_item(self, name, category, unit, **kwargs):
		"""
		Create a new stock item in Tally

		Args:
			name: Item name
			category: Item category (not used, kept for compatibility)
			unit: Unit of measurement
			**kwargs: Additional item properties (opening_balance, hsn_code, gst_rate)

		Returns:
			dict: Response from Tally
		"""
		try:
			opening_balance = kwargs.get('opening_balance', 0)
			hsn_code = kwargs.get('hsn_code')
			gst_rate = kwargs.get('gst_rate')

			xml_response = self.client.create_stock_item(
				name=name,
				base_unit=unit,
				opening_balance=opening_balance,
				hsn_code=hsn_code,
				gst_rate=gst_rate
			)
			return self.client.parse_xml_response(xml_response)
		except Exception as e:
			frappe.throw(_("Failed to create stock item: {0}").format(str(e)))

	def get_vouchers(self, voucher_type=None, from_date=None, to_date=None, company_name=None):
		"""
		Get vouchers from Tally

		Args:
			voucher_type: Type of voucher (Sales, Purchase, etc.)
			from_date: Start date (format: YYYYMMDD) - optional, fetches all if not provided
			to_date: End date (format: YYYYMMDD) - optional, fetches all if not provided
			company_name: Company name (optional)

		Returns:
			list: List of voucher dictionaries
		"""
		try:
			if not company_name:
				settings = self.get_tally_settings()
				company_name = settings.get("default_company", "")

			# Use the new get_vouchers_list function (no date filter if not provided)
			xml_response = self.client.get_vouchers_list(
				company_name=company_name,
				from_date=from_date,
				to_date=to_date
			)

			parsed = self.client.parse_xml_response(xml_response)
			vouchers = self._extract_vouchers(parsed)

			# Filter by voucher_type if specified
			if voucher_type and vouchers:
				vouchers = [v for v in vouchers if v.get('voucher_type') == voucher_type]

			return vouchers
		except Exception as e:
			frappe.log_error(message=str(e), title=_("Failed to get vouchers"))
			return []

	def _extract_vouchers(self, parsed_response):
		"""Extract vouchers from parsed XML response with all details"""
		vouchers = []
		envelope = parsed_response.get("ENVELOPE", parsed_response)
		body = envelope.get("BODY", envelope)
		data = body.get("DATA", body)
		collection = data.get("COLLECTION", data)

		# Try different possible paths for voucher data
		voucher_data = collection.get("VOUCHER", data.get("VOUCHER", data.get("TALLYMESSAGE", {}).get("VOUCHER", [])))
		if isinstance(voucher_data, dict):
			voucher_data = [voucher_data]

		for voucher in voucher_data:
			# Extract ledger entries
			ledger_entries = []
			all_ledger_entries = voucher.get("ALLLEDGERENTRIES.LIST", voucher.get("ALLLEDGERENTRIES", {}).get("LIST", []))
			if isinstance(all_ledger_entries, dict):
				all_ledger_entries = [all_ledger_entries]

			for entry in all_ledger_entries:
				ledger_name = self._extract_value(entry.get("LEDGERNAME", ""))
				amount = self._extract_numeric_value(entry.get("AMOUNT", 0))
				is_debit = amount >= 0
				is_credit = amount < 0

				ledger_entries.append({
					"ledger_name": ledger_name,
					"amount": abs(amount),
					"is_debit": is_debit,
					"is_credit": is_credit
				})

			vouchers.append({
				"guid": self._extract_value(voucher.get("GUID", "")),
				"master_id": self._extract_value(voucher.get("MASTERID", "")),
				"voucher_type": self._extract_value(voucher.get("VOUCHERTYPENAME", "")),
				"voucher_number": self._extract_value(voucher.get("VOUCHERNUMBER", "")),
				"date": self._convert_tally_date(self._extract_value(voucher.get("DATE", ""))),
				"party_ledger": self._extract_value(voucher.get("PARTYLEDGERNAME", "")),
				"narration": self._extract_value(voucher.get("NARRATION", "")),
				"reference_number": self._extract_value(voucher.get("REFERENCE", "")),
				"reference_date": self._convert_tally_date(self._extract_value(voucher.get("REFERENCEDATE", ""))),
				"is_cancelled": 1 if self._extract_value(voucher.get("ISCANCELLED", "No")) == "Yes" else 0,
				"ledger_entries": ledger_entries,
			})

		return vouchers

	def create_voucher(self, voucher_type, date, ledger_entries, narration=None, **kwargs):
		"""
		Create a voucher in Tally

		Args:
			voucher_type: Type of voucher (Sales, Purchase, Receipt, Payment, Journal)
			date: Voucher date (format: YYYYMMDD)
			ledger_entries: List of ledger entry dictionaries with keys:
							- ledger_name (str)
							- is_debit (bool)
							- amount (float)
			narration: Voucher narration (optional)
			**kwargs: Additional voucher properties (company_name, voucher_number)

		Returns:
			dict: Response from Tally
		"""
		try:
			company_name = kwargs.get('company_name') or ""
			if not company_name:
				settings = self.get_tally_settings()
				company_name = settings.get("default_company") or ""

			voucher_number = kwargs.get('voucher_number')
			party_ledger = kwargs.get('party_ledger')
			inventory_entries = kwargs.get('inventory_entries') or []
			vtype = voucher_type.lower()

			if vtype == 'sales':
				xml_response = self.client.create_sales_voucher(
					company_name=company_name,
					ledger_entries=ledger_entries,
					inventory_entries=inventory_entries,
					date=date,
					voucher_number=voucher_number,
					narration=narration or "",
					party_ledger=party_ledger,
				)
			elif vtype == 'purchase':
				xml_response = self.client.create_purchase_voucher(
					company_name=company_name,
					ledger_entries=ledger_entries,
					inventory_entries=inventory_entries,
					date=date,
					voucher_number=voucher_number,
					narration=narration or "",
					party_ledger=party_ledger,
				)
			elif vtype == 'receipt':
				party = party_ledger or next(
					(e['ledger_name'] for e in ledger_entries if not e.get('is_debit')), None
				)
				amount = next((e['amount'] for e in ledger_entries if not e.get('is_debit')), 0)
				xml_response = self.client.create_receipt_voucher(
					party_ledger_name=party,
					amount=amount,
					date=date,
					narration=narration or "",
					voucher_number=voucher_number,
					company_name=company_name,
					ledger_entries=ledger_entries,
				)
			else:
				# Journal, Payment, Contra, Debit Note, Credit Note
				xml_response = self.client.create_journal_voucher(
					company_name=company_name,
					entries=ledger_entries,
					date=date,
					voucher_number=voucher_number,
					narration=narration or "",
				)

			return self.client.parse_xml_response(xml_response)
		except Exception as e:
			frappe.throw(_("Failed to create voucher: {0}").format(str(e)))

	def get_groups(self, group_type="Ledger", company_name=None):
		"""
		Get groups from Tally

		Args:
			group_type: Type of group (Ledger, Stock, etc.) - currently only Ledger is supported
			company_name: Company name (optional)

		Returns:
			list: List of group dictionaries
		"""
		try:
			xml_response = self.client.get_groups_list(company_name=company_name)
			parsed = self.client.parse_xml_response(xml_response)

			# Check if parsed response is valid
			if not isinstance(parsed, dict):
				frappe.log_error(
					message=f"Invalid response from Tally: {parsed}",
					title=_("Failed to get groups")
				)
				return []

			# Extract groups from parsed response
			groups = []
			envelope = parsed.get("ENVELOPE", parsed)
			body = envelope.get("BODY", envelope)
			data = body.get("DATA", body)
			collection = data.get("COLLECTION", data)

			# Groups might be under GROUP key
			group_data = collection.get("GROUP", [])
			if isinstance(group_data, dict):
				group_data = [group_data]

			for group in group_data:
				groups.append({
					"name": self._extract_value(group.get("NAME", group.get("@NAME", ""))),
					"parent": self._extract_value(group.get("PARENT", "")),
					"master_id": self._extract_value(group.get("MASTERID", "")),
				})

			return groups
		except Exception as e:
			frappe.log_error(message=str(e), title=_("Failed to get groups"))
			return []


@frappe.whitelist()
def test_tally_connection(host=None, port=None):
	"""
	Test connection to Tally server (whitelisted for API access)

	Args:
		host: Tally server host
		port: Tally server port

	Returns:
		dict: Connection status
	"""
	try:
		client = TallyClient(host=host, port=port)
		if client.test_connection():
			return {
				"success": True,
				"message": _("Successfully connected to Tally server")
			}
		else:
			return {
				"success": False,
				"message": _("Failed to connect to Tally server")
			}
	except Exception as e:
		return {
			"success": False,
			"message": str(e)
		}
