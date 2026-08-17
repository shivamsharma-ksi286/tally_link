import requests
import frappe
from lxml import etree as ET


class TallyXmlClient:
    def __init__(self, tally_url="http://localhost", tally_port=9000, timeout=30):
        """
        Initialise the Tally XML client with server connection parameters.

        Args:
            tally_url (str): Tally server base URL. Default: http://localhost
            tally_port (int): Tally server port number. Default: 9000
            timeout (int): Request timeout in seconds. Default: 30
        """
        self.tally_url = tally_url
        self.tally_port = tally_port
        self.timeout = timeout
        self.endpoint = f"{tally_url}:{tally_port}"
        self.last_xml_request = None

    def _send_request(self, xml_request):
        """
        Transmit an XML request to the Tally server and return the response.

        Args:
            xml_request (str): Well-formed XML request string.

        Returns:
            str: XML response text from Tally server.
        """
        try:
            self.last_xml_request = xml_request

            frappe.logger("tally").info(f"Tally request dispatched to {self.endpoint}.")
            frappe.logger("tally").info(f"Request payload:\n{xml_request}")

            response = requests.post(self.endpoint, data=xml_request, timeout=self.timeout)

            if response.status_code == 200:
                return response.text
            else:
                error_message = f"HTTP error {response.status_code} received from Tally server."
                frappe.logger("tally").error(error_message)
                frappe.logger("tally").error(f"Response body:\n{response.text}")
                return error_message
        except Exception as exc:
            error_message = f"Request failed: {str(exc)}"
            frappe.logger("tally").error(f"Tally request exception: {error_message}")
            frappe.logger("tally").error(f"Failed request payload:\n{xml_request}")
            return error_message

    def test_connection(self):
        """
        Verify connectivity to the Tally server.

        Returns:
            bool: True if the server is reachable, False otherwise.
        """
        try:
            response = requests.post(self.endpoint, data="")
            return response.status_code == 200
        except Exception:
            return False

    def get_current_company(self):
        """
        Retrieve the currently active company name from Tally.

        Returns:
            str: XML response containing the current company name.
        """
        xml_request = """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>CompanyInfo</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES />
            <TDL>
                <TDLMESSAGE>
                    <OBJECT NAME="CurrentCompany">
                        <LOCALFORMULA>CurrentCompany:##SVCURRENTCOMPANY</LOCALFORMULA>
                    </OBJECT>
                    <COLLECTION NAME="CompanyInfo">
                        <OBJECTS>CurrentCompany</OBJECTS>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    # -------------------- Collections --------------------

    def get_sales_report(self):
        """
        Fetch all Sales Vouchers for the current period.

        Returns:
            str: XML response containing sales vouchers.
        """
        xml_request = """<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>Sales Vouchers</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>

</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_companies_list(self, include_simple_companies=False):
        """
        Retrieve the list of companies available in Tally.

        Args:
            include_simple_companies (bool): Include simple companies in the result. Default: False

        Returns:
            str: XML response containing the company list.
        """
        simple_companies_value = "No" if not include_simple_companies else "Yes"

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>List of Companies</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
            <SVIsSimpleCompany>{simple_companies_value}</SVIsSimpleCompany>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="Yes" ISOPTION="No" ISINTERNAL="No" NAME="List of Companies">
                        <TYPE>Company</TYPE>
                        <NATIVEMETHOD>Name</NATIVEMETHOD>
                    </COLLECTION>
                    <ExportHeader>EmpId:5989</ExportHeader>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_ledgers_list(self, company_name=None):
        """
        Retrieve the list of ledgers from Tally.

        Args:
            company_name (str): Company name to scope the request. Default: None

        Returns:
            str: XML response containing the ledger list.
        """
        company_element = f"<SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>" if company_name else ""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>Ledgers</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                {company_element}
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No" ISOPTION="No" ISINTERNAL="No" NAME="Ledgers">
                        <TYPE>Ledger</TYPE>
                        <NATIVEMETHOD>Address</NATIVEMETHOD>
                        <NATIVEMETHOD>Masterid</NATIVEMETHOD>
                        <NATIVEMETHOD>*</NATIVEMETHOD>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_stock_items_list(self):
        """
        Retrieve the list of stock items from Tally with detailed information.

        Returns:
            str: XML response containing stock items including balance, rate, and value.
        """
        xml_request = """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>Custom List of StockItems</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="Yes" ISOPTION="No" ISINTERNAL="No" NAME="Custom List of StockItems">
                        <TYPE>StockItem</TYPE>
                        <FETCH>NAME</FETCH>
                        <FETCH>PARENT</FETCH>
                        <FETCH>ALIAS</FETCH>
                        <FETCH>GUID</FETCH>
                        <FETCH>MASTERID</FETCH>
                        <FETCH>BASEUNITS</FETCH>
                        <FETCH>OPENINGBALANCE</FETCH>
                        <FETCH>OPENINGRATE</FETCH>
                        <FETCH>OPENINGVALUE</FETCH>
                        <FETCH>CLOSINGBALANCE</FETCH>
                        <FETCH>CLOSINGRATE</FETCH>
                        <FETCH>CLOSINGVALUE</FETCH>
                        <FETCH>HSNCODE</FETCH>
                        <FETCH>GSTAPPLICABLE</FETCH>
                        <FETCH>TAXCLASSIFICATIONNAME</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_vouchers_by_type(self, company_name, from_date, to_date, voucher_type="Attendance"):
        """
        Retrieve vouchers of a specified type within a date range.

        Args:
            company_name (str): Company name.
            from_date (str): Start date (format: DD-MMM-YYYY or YYYYMMDD).
            to_date (str): End date (format: DD-MMM-YYYY or YYYYMMDD).
            voucher_type (str): Voucher type name. Default: Attendance

        Returns:
            str: XML response containing matching vouchers.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>Custom Voucher Collection</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$SysName:XML</SVEXPORTFORMAT>
                <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                <SVFROMDATE TYPE="Date">{from_date}</SVFROMDATE>
                <SVTODATE TYPE="Date">{to_date}</SVTODATE>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="Yes" ISOPTION="No" ISINTERNAL="No" NAME="Custom Voucher Collection">
                        <TYPE>Voucher</TYPE>
                        <FILTERS>VoucherTypeFilter, DateFilter</FILTERS>
                        <FETCH>GUID</FETCH>
                        <FETCH>MASTERID</FETCH>
                        <FETCH>VOUCHERTYPENAME</FETCH>
                        <FETCH>VOUCHERNUMBER</FETCH>
                        <FETCH>DATE</FETCH>
                        <FETCH>PARTYLEDGERNAME</FETCH>
                        <FETCH>NARRATION</FETCH>
                        <FETCH>REFERENCE</FETCH>
                        <FETCH>REFERENCEDATE</FETCH>
                        <FETCH>ISCANCELLED</FETCH>
                        <FETCH>ALLLEDGERENTRIES.LIST</FETCH>
                    </COLLECTION>
                    <SYSTEM TYPE="Formulae" NAME="VoucherTypeFilter">$VoucherTypeName = "{voucher_type}"</SYSTEM>
                    <SYSTEM TYPE="Formulae" NAME="DateFilter">$Date &gt;= @@SVFROMDATE AND $Date &lt;= @@SVTODATE</SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_vouchers_list(self, company_name=None, from_date=None, to_date=None):
        """
        Retrieve a list of vouchers from Tally with optional filters.

        Args:
            company_name (str): Company name. Default: None
            from_date (str): Start date in YYYYMMDD format. Default: None
            to_date (str): End date in YYYYMMDD format. Default: None

        Returns:
            str: XML response containing the voucher list.
        """
        static_vars = "<STATICVARIABLES>\n"
        if company_name:
            static_vars += f"                <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>\n"
        if from_date:
            static_vars += f"                <SVFROMDATE TYPE=\"Date\">{from_date}</SVFROMDATE>\n"
        if to_date:
            static_vars += f"                <SVTODATE TYPE=\"Date\">{to_date}</SVTODATE>\n"
        static_vars += "            </STATICVARIABLES>"

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>List of Vouchers</ID>
    </HEADER>
    <BODY>
        <DESC>
            {static_vars}
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="Yes" ISOPTION="No" ISINTERNAL="No" NAME="List of Vouchers">
                        <TYPE>Voucher</TYPE>
                        <FETCH>GUID</FETCH>
                        <FETCH>MASTERID</FETCH>
                        <FETCH>VOUCHERTYPENAME</FETCH>
                        <FETCH>VOUCHERNUMBER</FETCH>
                        <FETCH>DATE</FETCH>
                        <FETCH>PARTYLEDGERNAME</FETCH>
                        <FETCH>NARRATION</FETCH>
                        <FETCH>REFERENCE</FETCH>
                        <FETCH>REFERENCEDATE</FETCH>
                        <FETCH>ISCANCELLED</FETCH>
                        <FETCH>ALLLEDGERENTRIES.LIST</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_groups_list(self, company_name=None):
        """
        Retrieve the list of account groups from Tally.

        Args:
            company_name (str): Company name. Default: None

        Returns:
            str: XML response containing the groups list.
        """
        company_element = f"<SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>" if company_name else ""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>List of Groups</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                {company_element}
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION NAME="List of Groups" ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No" ISOPTION="No" ISINTERNAL="No">
                        <TYPE>Group</TYPE>
                        <FETCH>Name, Parent, MasterID</FETCH>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    # -------------------- Reports --------------------

    def get_payslip(self, from_date, to_date, employee_name):
        """
        Retrieve an employee payslip as PDF content.

        Args:
            from_date (str): Start date (format: YYYYMMDD).
            to_date (str): End date (format: YYYYMMDD).
            employee_name (str): Employee name.

        Returns:
            bytes: PDF content of the payslip, or an error string on failure.
        """
        xml_request = f"""<ENVELOPE>
<HEADER>
<TALLYREQUEST>Export Data</TALLYREQUEST>
</HEADER>
<BODY>
<EXPORTDATA>
<REQUESTDESC>
<REPORTNAME>SelectiveEmployeePaySlip</REPORTNAME>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:pdf</SVEXPORTFORMAT>
<SVFROMDATE>{from_date}</SVFROMDATE>
<SVTODATE>{to_date}</SVTODATE>
<CostCentreName>{employee_name}</CostCentreName>
</STATICVARIABLES>
</REQUESTDESC>
</EXPORTDATA>
</BODY>
</ENVELOPE>"""
        try:
            response = requests.post(self.endpoint, data=xml_request)
            if response.status_code == 200:
                return response.content
            else:
                frappe.logger("tally").error(
                    f"Payslip retrieval failed: HTTP {response.status_code} — {response.text[:200]}"
                )
                return f"HTTP error {response.status_code}"
        except Exception as exc:
            frappe.logger("tally").exception("An error occurred during payslip retrieval.")
            return f"Request failed: {str(exc)}"

    def get_sales_report_voucher_register(self, from_date, to_date, company_name, voucher_type="Sales"):
        """
        Retrieve sales data using the Voucher Register report.

        Args:
            from_date (str): Start date (format: YYYYMMDD).
            to_date (str): End date (format: YYYYMMDD).
            company_name (str): Company name.
            voucher_type (str): Voucher type. Default: Sales

        Returns:
            str: XML response containing the sales report.
        """
        xml_request = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>EXPORT</TALLYREQUEST>
    <TYPE>DATA</TYPE>
    <ID>Voucher Register</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:xml</SVEXPORTFORMAT>
        <SVFROMDATE TYPE="DATE">{from_date}</SVFROMDATE>
        <SVTODATE TYPE="DATE">{to_date}</SVTODATE>
        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        <VOUCHERTYPENAME TYPE="STRING">{voucher_type}</VOUCHERTYPENAME>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_bill_receivables(self, from_date, to_date, company_name):
        """
        Retrieve the bills receivable report.

        Args:
            from_date (str): Start date (format: DD-MMM-YYYY).
            to_date (str): End date (format: DD-MMM-YYYY).
            company_name (str): Company name.

        Returns:
            str: XML response containing bill receivables.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <STATICVARIABLES>
                    <SVViewName>Accounting Voucher View</SVViewName>
                    <SVFROMDATE>{from_date}</SVFROMDATE>
                    <SVTODATE>{to_date}</SVTODATE>
                    <SVEXPORTFORMAT>$$SysName:xml</SVEXPORTFORMAT>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
                <REPORTNAME>Bills Receivable</REPORTNAME>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_ledger_vouchers(self, from_date, to_date, ledger_name="Sales"):
        """
        Retrieve vouchers associated with a specific ledger.

        Args:
            from_date (str): Start date.
            to_date (str): End date.
            ledger_name (str): Ledger name. Default: Sales

        Returns:
            str: XML response containing ledger vouchers.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>Vouchers</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVViewName>Accounting Voucher View</SVViewName>
                <SVFROMDATE>{from_date}</SVFROMDATE>
                <SVTODATE TYPE="Date">{to_date}</SVTODATE>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No" ISOPTION="No" ISINTERNAL="No" NAME="Vouchers">
                        <TYPE> Vouchers</TYPE>
                        <Childof>{ledger_name}</Childof>
                        <NATIVEMETHOD>*</NATIVEMETHOD>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_group_vouchers(self, from_date, to_date, group_name="Sales Accounts"):
        """
        Retrieve vouchers associated with a specific account group.

        Args:
            from_date (str): Start date.
            to_date (str): End date.
            group_name (str): Account group name. Default: Sales Accounts

        Returns:
            str: XML response containing group vouchers.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>Vouchers</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVViewName>Accounting Voucher View</SVViewName>
                <SVFROMDATE>{from_date}</SVFROMDATE>
                <SVTODATE TYPE="Date">{to_date}</SVTODATE>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No" ISOPTION="No" ISINTERNAL="No" NAME="Vouchers">
                        <TYPE> Vouchers : Group</TYPE>
                        <Childof>{group_name}</Childof>
                        <NATIVEMETHOD>*</NATIVEMETHOD>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_stock_vouchers_summary(self, stock_item_name, explode_vnum=True, explode_flag=False):
        """
        Retrieve a stock vouchers summary for a given item.

        Args:
            stock_item_name (str): Stock item name.
            explode_vnum (bool): Include voucher numbers. Default: True
            explode_flag (bool): Include detailed format. Default: False

        Returns:
            str: XML response containing the stock vouchers summary.
        """
        explode_vnum_value = "Yes" if explode_vnum else "No"
        explode_flag_value = "Yes" if explode_flag else "No"

        xml_request = f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>Export</TALLYREQUEST>
<TYPE>Data</TYPE>
<ID>Stock Vouchers</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
<ExplodeVNum>{explode_vnum_value}</ExplodeVNum>
<EXPLODEFLAG>{explode_flag_value}</EXPLODEFLAG>
<StockItemName>{stock_item_name}</StockItemName>
</STATICVARIABLES>
</DESC>
</BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_stock_ageing(self, stock_group_name, from_date, to_date):
        """
        Retrieve the stock ageing report for a given group.

        Args:
            stock_group_name (str): Stock group name.
            from_date (str): Start date (format: DD-MMM-YYYY).
            to_date (str): End date (format: DD-MMM-YYYY).

        Returns:
            str: XML response containing the stock ageing report.
        """
        xml_request = f"""<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>Export</TALLYREQUEST>
<TYPE>Data</TYPE>
<ID>StockAgeing</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
<StockGroupName>{stock_group_name}</StockGroupName>
<StockAgeFrom>{from_date}</StockAgeFrom> <StockAgeTo>{to_date}</StockAgeTo>
</STATICVARIABLES>
</DESC>
</BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_list_of_accounts(self, from_date="", to_date=""):
        """
        Retrieve the full list of accounts from Tally.

        Args:
            from_date (str): Start date (format: YYMMDD). Default: ""
            to_date (str): End date (format: YYMMDD). Default: ""

        Returns:
            str: XML response containing the accounts list.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVFROMDATE>{from_date}</SVFROMDATE>
                    <SVTODATE>{to_date}</SVTODATE>
                    <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    # -------------------- Objects --------------------

    def get_ledger_by_name(self, ledger_name, from_date=None, to_date=None):
        """
        Retrieve a specific ledger by its name.

        Args:
            ledger_name (str): Ledger name.
            from_date (str): Start date (format: YYYYMMDD). Default: None
            to_date (str): End date (format: YYYYMMDD). Default: None

        Returns:
            str: XML response containing ledger details.
        """
        date_variables = ""
        if from_date and to_date:
            date_variables = f"""<SVFROMDATE TYPE="Date">{from_date}</SVFROMDATE>
                <SVTODATE TYPE="Date">{to_date}</SVTODATE>"""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>Ledgers</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                {date_variables}
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No" ISOPTION="No" ISINTERNAL="No" NAME="Ledgers">
                        <TYPE>Ledger</TYPE>
                        <NATIVEMETHOD>Address</NATIVEMETHOD>
                        <NATIVEMETHOD>*</NATIVEMETHOD>
                        <FILTERS>LedgerNameFilter</FILTERS>
                    </COLLECTION>
                    <SYSTEM TYPE="Formulae" NAME="LedgerNameFilter">$Name="{ledger_name}"</SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_voucher_by_master_id(self, master_id, company_name=None):
        """
        Retrieve a voucher using its Tally master ID.

        Args:
            master_id (str): Master ID of the voucher.
            company_name (str): Company name. Default: None

        Returns:
            str: XML response containing voucher details.
        """
        company_element = f"<SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>" if company_name else ""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>EXPORT</TALLYREQUEST>
        <TYPE>Object</TYPE>
        <SUBTYPE>VOUCHER</SUBTYPE>
        <ID TYPE="Name">ID:'{master_id}'</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
            {company_element}
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVViewName>Accounting Voucher View</SVViewName>
            </STATICVARIABLES>
            <FETCHLIST>
                <FETCH>*</FETCH>
            </FETCHLIST>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_voucher_by_number_and_date(self, voucher_date, voucher_number, company_name=None):
        """
        Retrieve a voucher using its number and date.

        Args:
            voucher_date (str): Voucher date (format: DD-MMM-YYYY).
            voucher_number (str): Voucher number.
            company_name (str): Company name. Default: None

        Returns:
            str: XML response containing voucher details.
        """
        company_element = f"<SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>" if company_name else ""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>EXPORT</TALLYREQUEST>
        <TYPE>Object</TYPE>
        <SUBTYPE>VOUCHER</SUBTYPE>
        <ID TYPE="Name">Date:'{voucher_date}':VoucherNumber:'{voucher_number}'</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
            {company_element}
                <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                <SVViewName>Accounting Voucher View</SVViewName>
            </STATICVARIABLES>
            <FETCHLIST>
                <FETCH>*</FETCH>
            </FETCHLIST>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_stock_item_by_master_id(self, master_id):
        """
        Retrieve a stock item using its Tally master ID.

        Args:
            master_id (str): Master ID of the stock item.

        Returns:
            str: XML response containing stock item details.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>MasterCollection</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES>
            </STATICVARIABLES>
            <TDL>
                <TDLMESSAGE>
                    <COLLECTION ISMODIFY="No" ISFIXED="No" ISINITIALIZE="No" ISOPTION="No" ISINTERNAL="No" NAME="MasterCollection">
                        <TYPE>masters</TYPE>
                        <NATIVEMETHOD>*</NATIVEMETHOD>
                        <FILTERS>MasterIdFilter</FILTERS>
                    </COLLECTION>
                    <SYSTEM TYPE="Formulae" NAME="MasterIdFilter">$Masterid={master_id}</SYSTEM>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def get_license_info(self):
        """
        Retrieve Tally licence information.

        Returns:
            str: XML response containing licence details.
        """
        xml_request = """<ENVELOPE>
    <HEADER>
        <VERSION>1</VERSION>
        <TALLYREQUEST>Export</TALLYREQUEST>
        <TYPE>Collection</TYPE>
        <ID>LicenseInfo</ID>
    </HEADER>
    <BODY>
        <DESC>
            <STATICVARIABLES />
            <TDL>
                <TDLMESSAGE>
                    <OBJECT NAME="LicenseInfo">
                        <LOCALFORMULA>IsEducationalMode:  $$LicenseInfo:IsEducationalMode</LOCALFORMULA>
                        <LOCALFORMULA>IsSilver: $$LicenseInfo:IsSilver</LOCALFORMULA>
                        <LOCALFORMULA>IsGold: $$LicenseInfo:IsGold</LOCALFORMULA>
                        <LOCALFORMULA>PlanName: If $$LicenseInfo:IsEducationalMode Then "Educational Version" ELSE  If $$LicenseInfo:IsSilver Then "Silver" ELSE  If $$LicenseInfo:IsGold Then "Gold" else ""</LOCALFORMULA>
                        <LOCALFORMULA>SerialNumber: $$LicenseInfo:SerialNumber</LOCALFORMULA>
                        <LOCALFORMULA>AccountId:$$LicenseInfo:AccountID</LOCALFORMULA>
                        <LOCALFORMULA>IsIndian: $$LicenseInfo:IsIndian</LOCALFORMULA>
                        <LOCALFORMULA>RemoteSerialNumber: $$LicenseInfo:RemoteSerialNumber</LOCALFORMULA>
                        <LOCALFORMULA>IsRemoteAccessMode: $$LicenseInfo:IsRemoteAccessMode</LOCALFORMULA>
                        <LOCALFORMULA>IsLicClientMode: $$LicenseInfo:IsLicClientMode</LOCALFORMULA>
                        <LOCALFORMULA>AdminMailId:$$LicenseInfo:AdminEmailID</LOCALFORMULA>
                        <LOCALFORMULA>IsAdmin:$$LicenseInfo:IsAdmin</LOCALFORMULA>
                        <LOCALFORMULA>ApplicationPath:$$SysInfo:ApplicationPath</LOCALFORMULA>
                        <LOCALFORMULA>DataPath:##SVCurrentPath</LOCALFORMULA>
                        <LOCALFORMULA>UserLevel:$$cmpusername</LOCALFORMULA>
                    </OBJECT>
                    <COLLECTION NAME="LicenseInfo">
                        <OBJECTS>LicenseInfo</OBJECTS>
                    </COLLECTION>
                </TDLMESSAGE>
            </TDL>
        </DESC>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def create_ledger(self, name, parent=None, address=None, country=None, state=None, pincode=None,
                      mobile=None, gstin=None, pan=None, email=None, mailing_name=None,
                      company_name=None, action="Create", **kwargs):
        """
        Create or update a ledger entry in Tally.

        Args:
            name (str): Ledger name.
            parent (str): Parent group name. Default: None
            address (str): Party address — may be multi-line (\\n separated). Default: None
            country (str): Country of residence. Default: None
            state (str): State name. Default: None
            pincode (str): Postal/PIN code. Required for Tally to persist address/state/
                country/mailing name at all — if omitted, Tally silently accepts the
                request (EXCEPTIONS=0) but discards the entire mailing-details block.
                Default: None
            mobile (str): Mobile number. Default: None
            gstin (str): GST Identification Number. Default: None
            pan (str): Income Tax / PAN number. Default: None
            email (str): Email address. Default: None
            mailing_name (str): Mailing name (defaults to ledger name in Tally if omitted). Default: None
            company_name (str): Tally company name. Default: None
            action (str): "Create" or "Alter". Use "Alter" when the ledger already
                exists in Tally — Tally raises an exception (EXCEPTIONS=1) if
                "Create" is sent for a name that already exists. Default: "Create"

        Returns:
            str: XML response confirming ledger creation/update.
        """
        import datetime

        def esc(value):
            return (
                str(value)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        parent_element = f"<PARENT>{esc(parent)}</PARENT>" if parent else ""
        mobile_element = f"<LEDGERPHONE>{esc(mobile)}</LEDGERPHONE>" if mobile else ""
        email_element = f"<EMAIL>{esc(email)}</EMAIL>" if email else ""
        gstin_element = f"<PARTYGSTIN>{esc(gstin)}</PARTYGSTIN>" if gstin else ""
        pan_element = f"<INCOMETAXNUMBER>{esc(pan)}</INCOMETAXNUMBER>" if pan else ""
        company_element = f"<SVCURRENTCOMPANY>{esc(company_name)}</SVCURRENTCOMPANY>" if company_name else ""
        ledger_action = "Alter" if str(action).lower() == "alter" else "Create"

        # Address, state, country, mailing name and pincode are NOT stored by Tally
        # from the legacy flat tags (ADDRESS/STATENAME/COUNTRYOFRESIDENCE/MAILINGNAME) —
        # TallyPrime silently accepts and discards them. They must go inside
        # LEDMAILINGDETAILS.LIST, which requires both an APPLICABLEFROM date and a
        # PINCODE to actually persist — omitting PINCODE drops the whole block silently.
        mailing_details_element = ""
        if address or state or country or mailing_name:
            address_list_element = ""
            if address:
                address_lines = [line.strip() for line in str(address).splitlines() if line.strip()]
                if address_lines:
                    address_rows = "".join(f"<ADDRESS>{esc(line)}</ADDRESS>" for line in address_lines)
                    address_list_element = f'<ADDRESS.LIST TYPE="String">{address_rows}</ADDRESS.LIST>'

            applicable_from = datetime.date.today().strftime("%Y%m%d")
            mailing_name_inner = f"<MAILINGNAME>{esc(mailing_name)}</MAILINGNAME>" if mailing_name else ""
            state_inner = f"<STATE>{esc(state)}</STATE>" if state else ""
            country_inner = f"<COUNTRY>{esc(country)}</COUNTRY>" if country else ""
            pincode_inner = f"<PINCODE>{esc(pincode)}</PINCODE>" if pincode else ""

            mailing_details_element = f"""<LEDMAILINGDETAILS.LIST>
                                <APPLICABLEFROM>{applicable_from}</APPLICABLEFROM>
                                {mailing_name_inner}
                                {address_list_element}
                                {state_inner}
                                {country_inner}
                                {pincode_inner}
                            </LEDMAILINGDETAILS.LIST>"""

        xml_request = f"""<ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Import Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>All Masters</REPORTNAME>
                    <STATICVARIABLES>
                        {company_element}
                    </STATICVARIABLES>
                </REQUESTDESC>
                <REQUESTDATA>
                    <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <LEDGER Action="{ledger_action}">
                            <NAME>{esc(name)}</NAME>
                            {parent_element}
                            {mailing_details_element}
                            {mobile_element}
                            {email_element}
                            {gstin_element}
                            {pan_element}
                        </LEDGER>
                    </TALLYMESSAGE>
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>"""
        return self._send_request(xml_request)

    def create_receipt_voucher(self, party_ledger_name, amount, date=None, narration="",
                               voucher_number=None, company_name="", ledger_entries=None):
        """
        Create a receipt voucher in Tally.

        Args:
            party_ledger_name (str): Party ledger name (customer who paid).
            amount (float): Amount received.
            date (str): Voucher date in YYYYMMDD format. Default: today
            narration (str): Voucher narration. Default: ""
            voucher_number (str): Voucher number. Default: None (auto-generated)
            company_name (str): Tally company name.
            ledger_entries (list): Full ledger entries if available (overrides party+amount).

        Returns:
            str: XML response confirming voucher creation.
        """
        from datetime import datetime
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        elif hasattr(date, 'strftime'):
            date = date.strftime("%Y%m%d")
        elif isinstance(date, str) and '-' in date:
            date = date.replace('-', '')

        company_name = company_name or ""
        voucher_number_element = f"<VOUCHERNUMBER>{voucher_number}</VOUCHERNUMBER>" if voucher_number else ""

        # Build ledger entry XML from full entries if provided, else use party+amount
        if ledger_entries:
            entry_elements = []
            for entry in ledger_entries:
                is_deemed_positive = "Yes" if entry.get('is_debit') else "No"
                entry_amount = float(entry.get('amount', 0))
                signed_amount = -entry_amount if entry.get('is_debit') else entry_amount
                entry_elements.append(f"""<ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{entry.get('ledger_name', '')}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{is_deemed_positive}</ISDEEMEDPOSITIVE>
                <AMOUNT>{signed_amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")
            ledger_entries_xml = "\n".join(entry_elements)
        else:
            ledger_entries_xml = f"""<ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{party_ledger_name}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <AMOUNT>-{amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>Cash</LEDGERNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <AMOUNT>{amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>"""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Receipt" ACTION="Create">
                        <DATE>{date}</DATE>
                        <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
                        {voucher_number_element}
                        <PARTYLEDGERNAME>{party_ledger_name}</PARTYLEDGERNAME>
                        <NARRATION>{narration}</NARRATION>
                        {ledger_entries_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def create_stock_item(self, name, base_unit, opening_balance=0, hsn_code=None, gst_rate=None):
        """
        Create a new stock item in Tally.

        Args:
            name (str): Stock item name.
            base_unit (str): Base unit of measurement (e.g. Nos, Kg).
            opening_balance (float): Opening balance quantity. Default: 0
            hsn_code (str): HSN code. Default: None
            gst_rate (float): GST rate percentage. Default: None

        Returns:
            str: XML response confirming item creation.
        """
        gst_details = ""
        if hsn_code and gst_rate:
            half_rate = gst_rate / 2
            gst_details = f"""
            <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>
            <GSTDETAILS.LIST>
                <APPLICABLEFROM>20200401</APPLICABLEFROM>
                <CALCULATIONTYPE>On Value</CALCULATIONTYPE>
                <HSNCODE>{hsn_code}</HSNCODE>
                <TAXABILITY>Taxable</TAXABILITY>
                <STATEWISEDETAILS.LIST>
                    <STATENAME>&#4; Any</STATENAME>
                    <RATEDETAILS.LIST>
                        <GSTRATEDUTYHEAD>Central Tax</GSTRATEDUTYHEAD>
                        <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                        <GSTRATE> {half_rate}</GSTRATE>
                    </RATEDETAILS.LIST>
                    <RATEDETAILS.LIST>
                        <GSTRATEDUTYHEAD>State Tax</GSTRATEDUTYHEAD>
                        <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                        <GSTRATE> {half_rate}</GSTRATE>
                    </RATEDETAILS.LIST>
                    <RATEDETAILS.LIST>
                        <GSTRATEDUTYHEAD>Integrated Tax</GSTRATEDUTYHEAD>
                        <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                        <GSTRATE> {gst_rate}</GSTRATE>
                    </RATEDETAILS.LIST>
                    <RATEDETAILS.LIST>
                        <GSTRATEDUTYHEAD>Cess</GSTRATEDUTYHEAD>
                        <GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>
                    </RATEDETAILS.LIST>
                </STATEWISEDETAILS.LIST>
            </GSTDETAILS.LIST>"""

        xml_request = f"""<ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Import Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>All Masters</REPORTNAME>
                </REQUESTDESC>
                <REQUESTDATA>
                    <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <STOCKITEM Action="Create">
                            <NAME>{name}</NAME>
                            <BASEUNITS>{base_unit}</BASEUNITS>
                            <OPENINGBALANCE>{opening_balance}</OPENINGBALANCE>
                            {gst_details}
                        </STOCKITEM>
                    </TALLYMESSAGE>
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>"""
        return self._send_request(xml_request)

    def create_unit(self, name, is_simple_unit=True):
        """
        Create a new unit of measurement in Tally.

        Args:
            name (str): Unit name (e.g. Nos, Kg).
            is_simple_unit (bool): Whether this is a simple unit. Default: True

        Returns:
            str: XML response confirming unit creation.
        """
        is_simple = "true" if is_simple_unit else "false"

        xml_request = f"""<ENVELOPE>
        <HEADER>
            <TALLYREQUEST>Import Data</TALLYREQUEST>
        </HEADER>
        <BODY>
            <IMPORTDATA>
                <REQUESTDESC>
                    <REPORTNAME>All Masters</REPORTNAME>
                </REQUESTDESC>
                <REQUESTDATA>
                    <TALLYMESSAGE xmlns:UDF="TallyUDF">
                        <UNIT Action="Create">
                            <ISSIMPLEUNIT>{is_simple}</ISSIMPLEUNIT>
                            <NAME>{name}</NAME>
                        </UNIT>
                    </TALLYMESSAGE>
                </REQUESTDATA>
            </IMPORTDATA>
        </BODY>
    </ENVELOPE>"""
        return self._send_request(xml_request)

    def parse_xml_response(self, xml_response):
        """
        Parse an XML response received from Tally into a Python dictionary.

        Args:
            xml_response (str): XML response string from Tally.

        Returns:
            dict: Parsed response as a nested dictionary, or an error string on failure.
        """
        try:
            frappe.logger("tally").info("Parsing Tally XML response.")
            frappe.logger("tally").debug(f"XML content to parse:\n{xml_response}")

            if isinstance(xml_response, str) and xml_response.startswith("Error:"):
                frappe.logger("tally").error(f"XML response contains an error: {xml_response}")
                return xml_response

            parser = ET.XMLParser(recover=True)
            root = ET.fromstring(xml_response.encode('utf-8'), parser=parser)
            if root is None:
                frappe.logger("tally").error(f"[parse_response] lxml returned None root. Raw response: {repr(xml_response[:500])}")
                return {"error": f"Tally returned unparseable response: {xml_response[:200]}"}
            frappe.logger("tally").debug("XML parsed successfully using lxml recovering parser.")

            def xml_to_dict(element):
                """Recursively convert an XML element to a dictionary."""
                result = {}

                if element.attrib:
                    for key, value in element.attrib.items():
                        result[f"@{key}"] = value

                children = list(element)
                if children:
                    child_dict = {}
                    for child in children:
                        child_data = xml_to_dict(child)
                        if child.tag in child_dict:
                            if not isinstance(child_dict[child.tag], list):
                                child_dict[child.tag] = [child_dict[child.tag]]
                            child_dict[child.tag].append(child_data)
                        else:
                            child_dict[child.tag] = child_data
                    result.update(child_dict)

                if element.text and element.text.strip():
                    if result:
                        result['_text'] = element.text.strip()
                    else:
                        return element.text.strip()

                return result if result else None

            parsed = {root.tag: xml_to_dict(root)}
            frappe.logger("tally").info(f"XML response parsed successfully. Root tag: {root.tag}")
            return parsed

        except ET.ParseError as parse_error:
            error_message = f"XML parse error: {str(parse_error)}"
            frappe.logger("tally").error(error_message)
            frappe.logger("tally").error(f"Unparseable XML content:\n{xml_response}")
            return error_message
        except Exception as exc:
            error_message = f"Unexpected parse exception: {str(exc)}"
            frappe.logger("tally").error(error_message)
            frappe.logger("tally").error(f"Unparseable XML content:\n{xml_response}")
            return {"error": error_message}

    # -------------------- Company Management --------------------

    def create_company(self, company_name, mailing_name=None, address_list=None, state=None,
                       pincode=None, country=None, email=None, financial_year_from="20250401",
                       books_from="20250401", base_currency_symbol="₹",
                       base_currency_formal_name="Indian Rupees", enable_bill_wise=True,
                       enable_cost_centers=False, enable_inventory=True):
        """
        Create a new company in Tally.

        Args:
            company_name (str): Company name.
            mailing_name (str): Mailing name. Default: same as company_name
            address_list (list): List of address lines. Default: None
            state (str): State name. Default: None
            pincode (str): Postal code. Default: None
            country (str): Country name. Default: None
            email (str): Email address. Default: None
            financial_year_from (str): Financial year start date (YYYYMMDD). Default: 20250401
            books_from (str): Books beginning date (YYYYMMDD). Default: 20250401
            base_currency_symbol (str): Currency symbol. Default: ₹
            base_currency_formal_name (str): Currency formal name. Default: Indian Rupees
            enable_bill_wise (bool): Enable bill-wise details. Default: True
            enable_cost_centers (bool): Enable cost centres. Default: False
            enable_inventory (bool): Enable inventory. Default: True

        Returns:
            str: XML response confirming company creation.
        """
        if not mailing_name:
            mailing_name = company_name

        address_element = ""
        if address_list and isinstance(address_list, list):
            address_lines = "".join(f"<ADDRESS>{addr}</ADDRESS>\n" for addr in address_list)
            address_element = f"""<ADDRESS.LIST TYPE="String">
                {address_lines}
            </ADDRESS.LIST>"""

        state_element = f"<STATENAME>{state}</STATENAME>" if state else ""
        pincode_element = f"<PINCODE>{pincode}</PINCODE>" if pincode else ""
        country_element = f"<COUNTRYNAME>{country}</COUNTRYNAME>" if country else ""
        email_element = f"<EMAIL>{email}</EMAIL>" if email else ""

        bill_wise_value = "Yes" if enable_bill_wise else "No"
        cost_centers_value = "Yes" if enable_cost_centers else "No"
        inventory_value = "Yes" if enable_inventory else "No"

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                 <STATICVARIABLES>
                 </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <COMPANY Action="Create">
                        <NAME>{company_name}</NAME>
                        <MAILINGNAME>{mailing_name}</MAILINGNAME>
                        {address_element}
                        {state_element}
                        {pincode_element}
                        {country_element}
                        {email_element}
                        <STARTINGFROM>{financial_year_from}</STARTINGFROM>
                        <BOOKSFROM>{books_from}</BOOKSFROM>
                        <BASECURRENCYSYMBOL>{base_currency_symbol}</BASECURRENCYSYMBOL>
                        <FORMALNAME>{base_currency_formal_name}</FORMALNAME>
                        <ISBILLWISEON>{bill_wise_value}</ISBILLWISEON>
                        <ISCOSTCENTRESON>{cost_centers_value}</ISCOSTCENTRESON>
                        <ISINVENTORYON>{inventory_value}</ISINVENTORYON>
                    </COMPANY>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def configure_company(self, company_name, enable_inventory=None, enable_bill_wise=None,
                          enable_cost_centers=None, enable_interest_calc=None):
        """
        Update company feature settings (F11) in Tally.

        Args:
            company_name (str): Company name.
            enable_inventory (bool): Enable inventory. Default: None (no change)
            enable_bill_wise (bool): Enable bill-wise details. Default: None (no change)
            enable_cost_centers (bool): Enable cost centres. Default: None (no change)
            enable_interest_calc (bool): Enable interest calculation. Default: None (no change)

        Returns:
            str: XML response confirming the update.
        """
        feature_elements = []

        if enable_inventory is not None:
            feature_elements.append(f"<ISINVENTORYENABLED>{'Yes' if enable_inventory else 'No'}</ISINVENTORYENABLED>")
        if enable_bill_wise is not None:
            feature_elements.append(f"<ISBILLWISEON>{'Yes' if enable_bill_wise else 'No'}</ISBILLWISEON>")
        if enable_cost_centers is not None:
            feature_elements.append(f"<ISCOSTCENTRESON>{'Yes' if enable_cost_centers else 'No'}</ISCOSTCENTRESON>")
        if enable_interest_calc is not None:
            feature_elements.append(f"<ISINTERESTON>{'Yes' if enable_interest_calc else 'No'}</ISINTERESTON>")

        if not feature_elements:
            return "No configuration parameters were specified."

        features_xml = "\n".join(feature_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <COMPANY NAME="{company_name}" ACTION="Alter">
                        {features_xml}
                    </COMPANY>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def enable_gst(self, company_name, state_name, gst_registration_type="Regular",
                   gstin=None, applicable_from="20250401"):
        """
        Enable GST for a company in Tally.

        Args:
            company_name (str): Company name.
            state_name (str): State name.
            gst_registration_type (str): GST registration type. Default: Regular
            gstin (str): GST Identification Number. Default: None
            applicable_from (str): GST applicable date (YYYYMMDD). Default: 20250401

        Returns:
            str: XML response confirming the update.
        """
        if gst_registration_type == "Regular" and not gstin:
            return "GSTIN is required for Regular GST registration type."

        gstin_element = f"<GSTIN>{gstin}</GSTIN>" if gstin else ""

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <COMPANY NAME="{company_name}" ACTION="Alter">
                        <ISGSTENABLED>Yes</ISGSTENABLED>
                        <STATENAME>{state_name}</STATENAME>
                        <GSTREGISTRATIONTYPE>{gst_registration_type}</GSTREGISTRATIONTYPE>
                        {gstin_element}
                        <APPLICABLEFROMGST>{applicable_from}</APPLICABLEFROMGST>
                        <SETALTERGSTDETAILS>Yes</SETALTERGSTDETAILS>
                        <HASSLABRATE>No</HASSLABRATE>
                        <HASLUTBOND>No</HASLUTBOND>
                    </COMPANY>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    # -------------------- Entity Management --------------------

    def delete_ledger(self, company_name, ledger_name):
        """
        Delete a ledger from Tally.

        Args:
            company_name (str): Company name.
            ledger_name (str): Ledger name to delete.

        Returns:
            str: XML response confirming deletion.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <LEDGER NAME="{ledger_name}" ACTION="Delete">
                    </LEDGER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def delete_stock_item(self, company_name, stock_item_name):
        """
        Delete a stock item from Tally.

        Args:
            company_name (str): Company name.
            stock_item_name (str): Stock item name to delete.

        Returns:
            str: XML response confirming deletion.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <STOCKITEM NAME="{stock_item_name}" ACTION="Delete">
                    </STOCKITEM>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def update_unit(self, company_name, unit_name, decimal_places=None, gst_uqc_code=None):
        """
        Update a unit of measurement in Tally.

        Args:
            company_name (str): Company name.
            unit_name (str): Unit name to update.
            decimal_places (int): Number of decimal places. Default: None (no change)
            gst_uqc_code (str): GST UQC code. Default: None (no change)

        Returns:
            str: XML response confirming the update.
        """
        update_elements = []

        if decimal_places is not None:
            update_elements.append(f"<DECIMALPLACES>{decimal_places}</DECIMALPLACES>")
        if gst_uqc_code is not None:
            update_elements.append(f"<ISGSTREPUOM>{gst_uqc_code}</ISGSTREPUOM>")

        if not update_elements:
            return "No update parameters were specified."

        elements_xml = "\n".join(update_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <UNIT NAME="{unit_name}" ACTION="Alter">
                        {elements_xml}
                    </UNIT>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def delete_unit(self, company_name, unit_name):
        """
        Delete a unit of measurement from Tally.

        Args:
            company_name (str): Company name.
            unit_name (str): Unit name to delete.

        Returns:
            str: XML response confirming deletion.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <UNIT NAME="{unit_name}" ACTION="Delete">
                    </UNIT>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    # -------------------- Voucher Management --------------------

    def create_journal_voucher(self, company_name, entries, date=None, voucher_number=None,
                               narration=""):
        """
        Create a journal voucher in Tally.

        Args:
            company_name (str): Company name.
            entries (list): List of dicts with keys: ledger_name (str), is_debit (bool), amount (float).
            date (str): Voucher date in YYYYMMDD format. Default: today
            voucher_number (str): Voucher number. Default: None (auto-generated)
            narration (str): Voucher narration. Default: ""

        Returns:
            str: XML response confirming voucher creation.
        """
        company_name = company_name or ""
        from datetime import datetime
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        elif hasattr(date, 'strftime'):
            date = date.strftime("%Y%m%d")
        elif isinstance(date, str) and '-' in date:
            date = date.replace('-', '')

        voucher_number_element = f"<VOUCHERNUMBER>{voucher_number}</VOUCHERNUMBER>" if voucher_number else ""

        ledger_entry_elements = []
        for entry in entries:
            is_deemed_positive = "Yes" if entry.get('is_debit', True) else "No"
            entry_amount = float(entry.get('amount', 0))
            signed_amount = -entry_amount if entry.get('is_debit', True) else entry_amount

            ledger_entry_elements.append(f"""<ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{entry.get('ledger_name', '')}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{is_deemed_positive}</ISDEEMEDPOSITIVE>
                <AMOUNT>{signed_amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")

        ledger_entries_xml = "\n".join(ledger_entry_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Journal" ACTION="Create">
                        <DATE>{date}</DATE>
                        <VOUCHERTYPENAME>Journal</VOUCHERTYPENAME>
                        {voucher_number_element}
                        <NARRATION>{narration}</NARRATION>
                        <PERSISTEDVIEW>Accounting Voucher View</PERSISTEDVIEW>
                        {ledger_entries_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def create_sales_voucher(self, company_name, ledger_entries, inventory_entries=None,
                             date=None, voucher_number=None, narration="", party_ledger=None):
        """
        Create a Sales voucher in Tally (appears in Sales Register).

        Args:
            company_name (str): Tally company name.
            ledger_entries (list): Dicts with ledger_name, amount, is_debit.
            inventory_entries (list): Dicts with item_name, qty, rate, amount, uom, godown.
            date (str): YYYYMMDD. Default: today.
            voucher_number (str): Voucher number. Default: auto-generated.
            narration (str): Narration. Default: "".
            party_ledger (str): Customer ledger name. Default: first debit entry.

        Returns:
            str: XML response.
        """
        company_name = company_name or ""
        from datetime import datetime, date as date_type
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        elif hasattr(date, 'strftime'):
            date = date.strftime("%Y%m%d")
        elif isinstance(date, str) and '-' in date:
            date = date.replace('-', '')

        voucher_number_element = f"<VOUCHERNUMBER>{voucher_number}</VOUCHERNUMBER>" if voucher_number else ""

        if not party_ledger:
            party_ledger = next(
                (e['ledger_name'] for e in ledger_entries if e.get('is_debit')), ""
            )

        ledger_entry_elements = []
        for entry in ledger_entries:
            is_deemed_positive = "Yes" if entry.get('is_debit') else "No"
            entry_amount = float(entry.get('amount', 0))
            signed_amount = -entry_amount if entry.get('is_debit') else entry_amount
            ledger_entry_elements.append(f"""<ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{entry.get('ledger_name', '')}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{is_deemed_positive}</ISDEEMEDPOSITIVE>
                <AMOUNT>{signed_amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")

        inventory_xml = ""
        if inventory_entries:
            inv_elements = []
            for item in inventory_entries:
                qty = float(item.get('qty', 1))
                rate = float(item.get('rate', 0))
                amount = float(item.get('amount', qty * rate))
                uom = item.get('uom') or item.get('stock_uom') or 'Nos'
                godown = item.get('godown') or 'Main Location'
                inv_elements.append(f"""<ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{item.get('item_name', '')}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
                <RATE>{rate}/Nos</RATE>
                <AMOUNT>{amount}</AMOUNT>
                <ACTUALQTY>{qty} {uom}</ACTUALQTY>
                <BILLEDQTY>{qty} {uom}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{godown}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <AMOUNT>{amount}</AMOUNT>
                    <ACTUALQTY>{qty} {uom}</ACTUALQTY>
                    <BILLEDQTY>{qty} {uom}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
            </ALLINVENTORYENTRIES.LIST>""")
            inventory_xml = "\n".join(inv_elements)

        ledger_entries_xml = "\n".join(ledger_entry_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Sales" ACTION="Create">
                        <DATE>{date}</DATE>
                        <EFFECTIVEDATE>{date}</EFFECTIVEDATE>
                        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
                        {voucher_number_element}
                        <PARTYLEDGERNAME>{party_ledger}</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <NARRATION>{narration}</NARRATION>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        {inventory_xml}
                        {ledger_entries_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def create_purchase_voucher(self, company_name, ledger_entries, inventory_entries=None,
                                date=None, voucher_number=None, narration="", party_ledger=None):
        """
        Create a Purchase voucher in Tally (appears in Purchase Register).

        Args:
            company_name (str): Tally company name.
            ledger_entries (list): Dicts with ledger_name, amount, is_debit.
            inventory_entries (list): Dicts with item_name, qty, rate, amount, uom, godown.
            date (str): YYYYMMDD. Default: today.
            voucher_number (str): Voucher number. Default: auto-generated.
            narration (str): Narration. Default: "".
            party_ledger (str): Supplier ledger name. Default: first credit entry.

        Returns:
            str: XML response.
        """
        company_name = company_name or ""
        from datetime import datetime
        if not date:
            date = datetime.now().strftime("%Y%m%d")
        elif hasattr(date, 'strftime'):
            date = date.strftime("%Y%m%d")
        elif isinstance(date, str) and '-' in date:
            date = date.replace('-', '')

        voucher_number_element = f"<VOUCHERNUMBER>{voucher_number}</VOUCHERNUMBER>" if voucher_number else ""

        if not party_ledger:
            party_ledger = next(
                (e['ledger_name'] for e in ledger_entries if not e.get('is_debit')), ""
            )

        ledger_entry_elements = []
        for entry in ledger_entries:
            is_deemed_positive = "Yes" if entry.get('is_debit') else "No"
            entry_amount = float(entry.get('amount', 0))
            signed_amount = -entry_amount if entry.get('is_debit') else entry_amount
            ledger_entry_elements.append(f"""<ALLLEDGERENTRIES.LIST>
                <LEDGERNAME>{entry.get('ledger_name', '')}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>{is_deemed_positive}</ISDEEMEDPOSITIVE>
                <AMOUNT>{signed_amount}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>""")

        inventory_xml = ""
        if inventory_entries:
            inv_elements = []
            for item in inventory_entries:
                qty = float(item.get('qty', 1))
                rate = float(item.get('rate', 0))
                amount = float(item.get('amount', qty * rate))
                uom = item.get('uom') or item.get('stock_uom') or 'Nos'
                godown = item.get('godown') or 'Main Location'
                inv_elements.append(f"""<ALLINVENTORYENTRIES.LIST>
                <STOCKITEMNAME>{item.get('item_name', '')}</STOCKITEMNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <RATE>{rate}/Nos</RATE>
                <AMOUNT>-{amount}</AMOUNT>
                <ACTUALQTY>{qty} {uom}</ACTUALQTY>
                <BILLEDQTY>{qty} {uom}</BILLEDQTY>
                <BATCHALLOCATIONS.LIST>
                    <GODOWNNAME>{godown}</GODOWNNAME>
                    <BATCHNAME>Primary Batch</BATCHNAME>
                    <AMOUNT>-{amount}</AMOUNT>
                    <ACTUALQTY>{qty} {uom}</ACTUALQTY>
                    <BILLEDQTY>{qty} {uom}</BILLEDQTY>
                </BATCHALLOCATIONS.LIST>
            </ALLINVENTORYENTRIES.LIST>""")
            inventory_xml = "\n".join(inv_elements)

        ledger_entries_xml = "\n".join(ledger_entry_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER VCHTYPE="Purchase" ACTION="Create">
                        <DATE>{date}</DATE>
                        <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
                        {voucher_number_element}
                        <PARTYLEDGERNAME>{party_ledger}</PARTYLEDGERNAME>
                        <ISINVOICE>Yes</ISINVOICE>
                        <NARRATION>{narration}</NARRATION>
                        <PERSISTEDVIEW>Invoice Voucher View</PERSISTEDVIEW>
                        {inventory_xml}
                        {ledger_entries_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def update_voucher(self, company_name, master_id, narration=None, voucher_type=None):
        """
        Update an existing voucher in Tally using its master ID.

        Args:
            company_name (str): Company name.
            master_id (str): Voucher master ID.
            narration (str): New narration. Default: None (no change)
            voucher_type (str): Voucher type name. Default: None (no change)

        Returns:
            str: XML response confirming the update.
        """
        update_elements = []

        if narration is not None:
            update_elements.append(f"<NARRATION>{narration}</NARRATION>")
        if voucher_type is not None:
            update_elements.append(f"<VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>")

        if not update_elements:
            return "No update parameters were specified."

        elements_xml = "\n".join(update_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER ACTION="Alter">
                        <MASTERID>{master_id}</MASTERID>
                        {elements_xml}
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def cancel_voucher(self, company_name, master_id):
        """
        Cancel a voucher in Tally using its master ID.

        Args:
            company_name (str): Company name.
            master_id (str): Voucher master ID.

        Returns:
            str: XML response confirming cancellation.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>Vouchers</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <VOUCHER ACTION="Cancel">
                        <MASTERID>{master_id}</MASTERID>
                    </VOUCHER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    # -------------------- Group Management --------------------

    def create_group(self, company_name, group_name, parent_group,
                     enable_bill_wise=None, is_addable=True):
        """
        Create a new account group in Tally.

        Args:
            company_name (str): Company name.
            group_name (str): Group name.
            parent_group (str): Parent group name.
            enable_bill_wise (bool): Enable bill-wise details. Default: None (inherit)
            is_addable (bool): Allow direct entries to this group. Default: True

        Returns:
            str: XML response confirming group creation.
        """
        bill_wise_element = ""
        if enable_bill_wise is not None:
            bill_wise_element = f"<ISBILLWISEON>{'Yes' if enable_bill_wise else 'No'}</ISBILLWISEON>"

        is_addable_value = "Yes" if is_addable else "No"

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <GROUP NAME="{group_name}" ACTION="Create">
                        <PARENT>{parent_group}</PARENT>
                        {bill_wise_element}
                        <ISADDABLE>{is_addable_value}</ISADDABLE>
                    </GROUP>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def update_group(self, company_name, group_name, parent_group=None,
                     enable_bill_wise=None, is_addable=None):
        """
        Update an existing account group in Tally.

        Args:
            company_name (str): Company name.
            group_name (str): Group name to update.
            parent_group (str): New parent group name. Default: None (no change)
            enable_bill_wise (bool): Enable bill-wise details. Default: None (no change)
            is_addable (bool): Allow direct entries. Default: None (no change)

        Returns:
            str: XML response confirming the update.
        """
        update_elements = []

        if parent_group is not None:
            update_elements.append(f"<PARENT>{parent_group}</PARENT>")
        if enable_bill_wise is not None:
            update_elements.append(f"<ISBILLWISEON>{'Yes' if enable_bill_wise else 'No'}</ISBILLWISEON>")
        if is_addable is not None:
            update_elements.append(f"<ISADDABLE>{'Yes' if is_addable else 'No'}</ISADDABLE>")

        if not update_elements:
            return "No update parameters were specified."

        elements_xml = "\n".join(update_elements)

        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <GROUP NAME="{group_name}" ACTION="Alter">
                        {elements_xml}
                    </GROUP>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def delete_group(self, company_name, group_name):
        """
        Delete an account group from Tally.

        Args:
            company_name (str): Company name.
            group_name (str): Group name to delete.

        Returns:
            str: XML response confirming deletion.
        """
        xml_request = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <GROUP NAME="{group_name}" ACTION="Delete">
                    </GROUP>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>"""
        return self._send_request(xml_request)

    def list_tally_companies(self):
        """
        Retrieve all companies currently loaded in Tally.

        Returns:
            list: Sorted list of company name strings, or None on error.
        """
        tally_url = self.endpoint
        frappe.logger("tally").info("Retrieving list of companies from Tally.")
        headers = {'Content-Type': 'application/xml'}
        request_xml = """
        <ENVELOPE>
            <HEADER>
                <VERSION>1</VERSION>
                <TALLYREQUEST>Export</TALLYREQUEST>
                <TYPE>Collection</TYPE>
                <ID>List of Companies</ID>
            </HEADER>
            <BODY>
                <DESC>
                    <STATICVARIABLES>
                        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    </STATICVARIABLES>
                    <FETCHLIST>
                    <FETCH>Name</FETCH>
                    </FETCHLIST>
                </DESC>
            </BODY>
        </ENVELOPE>
        """

        try:
            response = requests.post(tally_url, data=request_xml.encode('utf-8'), headers=headers, timeout=20)
            response_xml = response.text
            frappe.logger("tally").debug(f"Company list raw response:\n{response_xml}")

            if not response_xml or not response_xml.strip().startswith('<ENVELOPE>'):
                frappe.logger("tally").warning(
                    f"Unexpected response format while retrieving company list: {response_xml[:100]}"
                )
                return None

            companies = []
            try:
                root = ET.fromstring(response_xml)

                status = root.findtext('.//HEADER/STATUS')
                if status and status.strip() != '1':
                    error_nodes = root.findall('.//BODY/DATA/LINEERROR')
                    if error_nodes:
                        error_details = ", ".join(
                            err.text.strip() for err in error_nodes if err.text
                        )
                        frappe.logger("tally").error(
                            f"Tally reported errors during company list retrieval: {error_details}"
                        )
                    else:
                        frappe.logger("tally").error(
                            f"Tally returned status {status} during company list retrieval. "
                            f"Response: {response_xml[:200]}"
                        )
                    return None

                name_elements = root.findall('.//COLLECTION/COMPANY/NAME')
                if not name_elements:
                    name_elements = root.findall('.//NAME')

                for name_element in name_elements:
                    if name_element.text:
                        companies.append(name_element.text.strip())

                companies = sorted(set(companies))
                frappe.logger("tally").info(f"Company list retrieved successfully: {companies}")
                return companies

            except ET.ParseError as parse_error:
                frappe.logger("tally").error(
                    f"XML parse error while processing company list: {parse_error}"
                )
                frappe.logger("tally").error(f"Response snippet:\n{response_xml[:500]}")
                return None
            except Exception:
                frappe.logger("tally").exception("Unexpected error while processing company list XML.")
                return None

        except requests.exceptions.ConnectionError:
            frappe.logger("tally").error(
                f"Connection refused. Verify that Tally is running and accessible at {tally_url}."
            )
            return None
        except requests.exceptions.Timeout:
            frappe.logger("tally").error(
                f"Request timed out while connecting to Tally at {tally_url}."
            )
            return None
        except requests.exceptions.RequestException as req_exc:
            extra_detail = ""
            if req_exc.response is not None:
                extra_detail = (
                    f" HTTP status: {req_exc.response.status_code}. "
                    f"Response: {req_exc.response.text[:200]}"
                )
            frappe.logger("tally").error(
                f"Request exception during company list retrieval: {req_exc}{extra_detail}"
            )
            return None
        except Exception:
            frappe.logger("tally").exception("Unexpected error occurred while retrieving company list.")
            return None

    def select_tally_company(self, company_name):
        """
        Set the active company in Tally.

        Args:
            company_name (str): Exact company name to activate.

        Returns:
            bool: True if the company was selected successfully, False otherwise.
        """
        tally_url = self.endpoint
        frappe.logger("tally").info(f"Attempting to select company: '{company_name}'.")
        headers = {'Content-Type': 'application/xml'}
        request_xml = f"""
        <ENVELOPE>
            <HEADER>
                <VERSION>1</VERSION>
                <TALLYREQUEST>Export</TALLYREQUEST>
                <TYPE>Data</TYPE>
                <ID>Trial Balance</ID>
            </HEADER>
            <BODY>
                <DESC>
                    <STATICVARIABLES>
                        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                    </STATICVARIABLES>
                </DESC>
            </BODY>
        </ENVELOPE>
        """

        try:
            response = requests.post(
                tally_url, data=request_xml.encode('utf-8'), headers=headers, timeout=25
            )
            response_xml = response.text
            frappe.logger("tally").debug(
                f"Select company '{company_name}' raw response:\n{response_xml}"
            )

            if response_xml.strip() == "<ENVELOPE></ENVELOPE>":
                frappe.logger("tally").info(
                    f"Empty envelope received. Company '{company_name}' selected successfully."
                )
                return True

            frappe.logger("tally").warning(
                f"Unexpected response while selecting company '{company_name}': {response_xml[:200]}"
            )

            try:
                root = ET.fromstring(response_xml)
                status = root.findtext('.//HEADER/STATUS')
                error_nodes = root.findall('.//BODY/DATA/LINEERROR')
                error_text = ", ".join(e.text.strip() for e in error_nodes if e.text)
                frappe.logger("tally").warning(
                    f"Company selection failed for '{company_name}'. "
                    f"Status: {status}. Errors: {error_text}"
                )
            except ET.ParseError:
                frappe.logger("tally").warning(
                    f"Company selection failed for '{company_name}'. Response was not valid XML."
                )
            except Exception as inner_exc:
                frappe.logger("tally").warning(
                    f"Company selection failed for '{company_name}'. "
                    f"Error processing response: {inner_exc}"
                )

            return False

        except requests.exceptions.ConnectionError:
            frappe.logger("tally").error(
                f"Connection refused while selecting '{company_name}'. "
                f"Verify that Tally is running at {tally_url}."
            )
            return False
        except requests.exceptions.Timeout:
            frappe.logger("tally").error(
                f"Request timed out while selecting '{company_name}' at {tally_url}."
            )
            return False
        except requests.exceptions.RequestException as req_exc:
            extra_detail = ""
            if req_exc.response is not None:
                extra_detail = (
                    f" HTTP status: {req_exc.response.status_code}. "
                    f"Response: {req_exc.response.text[:200]}"
                )
            frappe.logger("tally").error(
                f"Request exception while selecting company '{company_name}': {req_exc}{extra_detail}"
            )
            return False
        except Exception:
            frappe.logger("tally").exception(
                f"Unexpected error occurred while selecting company '{company_name}'."
            )
            return False

    def get_last_xml_request(self):
        """
        Return the last XML request sent to Tally, for debugging purposes.

        Returns:
            str: Last XML request string, or None if no request has been made.
        """
        return self.last_xml_request
