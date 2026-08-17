import frappe


def get_context(context):
	context.no_cache = 1
	context.show_sidebar = False

	if not frappe.session.user or frappe.session.user == "Guest":
		frappe.throw("You must be logged in to access Tally Link.", frappe.PermissionError)

	settings = {}
	conn_status = "Not Configured"
	sync_enabled = False

	if frappe.db.exists("Tally Settings", "Tally Settings"):
		doc = frappe.get_doc("Tally Settings", "Tally Settings")
		sync_enabled = bool(doc.get("enabled"))
		host = doc.get("host") or ""
		port = doc.get("port") or ""
		conn_status = doc.get("connection_status") or ("Connected" if sync_enabled else "Disabled")
		settings = {"host": host, "port": port}

	context.sync_enabled = sync_enabled
	context.conn_status = conn_status
	context.settings = settings

	context.stats = {
		"ledgers": frappe.db.count("Tally Ledger"),
		"stock_items": frappe.db.count("Tally Stock Item"),
		"vouchers": frappe.db.count("Tally Voucher"),
		"sync_logs": frappe.db.count("Tally Sync Log"),
	}

	context.recent_logs = frappe.get_all(
		"Tally Sync Log",
		fields=["name", "entity_type", "entity_name", "status", "direction", "sync_date"],
		order_by="sync_date desc",
		limit=10,
	)
