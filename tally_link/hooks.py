app_name = "tally_link"
app_title = "Tally Link"
app_publisher = "Ksolves India Limited"
app_description = "Tally Integration for ERPNext"
app_email = "sales@ksolves.com"
app_license = "gpl-3.0"
app_logo_url = "/assets/tally_link/images/image.png"
app_home = "/tally_link"

# This app does not require a setup wizard
setup_wizard_not_required = 1

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "tally_link",
		"logo": "/assets/tally_link/images/image.png",
		"title": "Tally Link",
		"route": "/tally_link"
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tally_link/css/tally_link.css"
app_include_js = "/assets/tally_link/js/tally_bulk_actions.js"

# include js, css files in header of web template
# web_include_css = "/assets/tally_link/css/tally_link.css"
# web_include_js = "/assets/tally_link/js/tally_link.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tally_link/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Sales Invoice": "public/js/sales_invoice.js",
	"Purchase Invoice": "public/js/purchase_invoice.js",
	"Payment Entry": "public/js/payment_entry.js",
	"Customer": "public/js/customer.js",
	"Supplier": "public/js/supplier.js",
}
doctype_list_js = {
	"Sales Invoice": "public/js/sales_invoice_list.js",
	"Purchase Invoice": "public/js/purchase_invoice_list.js",
	"Payment Entry": "public/js/payment_entry_list.js",
	"Customer": "public/js/customer_list.js",
	"Supplier": "public/js/supplier_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tally_link/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "tally_link.utils.jinja_methods",
# 	"filters": "tally_link.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "tally_link.install.before_install"
after_install = "tally_link.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tally_link.uninstall.before_uninstall"
# after_uninstall = "tally_link.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tally_link.utils.before_app_install"
# after_app_install = "tally_link.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tally_link.utils.before_app_uninstall"
# after_app_uninstall = "tally_link.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tally_link.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Customer": {
		"after_insert": "tally_link.tally.events.customer_after_insert",
		"on_update": "tally_link.tally.events.customer_on_update",
	},
	"Supplier": {
		"after_insert": "tally_link.tally.events.supplier_after_insert",
		"on_update": "tally_link.tally.events.supplier_on_update",
	},
	"Item": {
		"after_insert": "tally_link.tally.events.item_after_insert",
		"on_update": "tally_link.tally.events.item_on_update",
	},
	"Sales Invoice": {
		"on_submit": "tally_link.tally.events.sales_invoice_on_submit",
		"on_cancel": "tally_link.tally.events.sales_invoice_on_cancel",
	},
	"Purchase Invoice": {
		"on_submit": "tally_link.tally.events.purchase_invoice_on_submit",
		"on_cancel": "tally_link.tally.events.purchase_invoice_on_cancel",
	},
	"Payment Entry": {
		"on_submit": "tally_link.tally.events.payment_entry_on_submit",
		"on_cancel": "tally_link.tally.events.payment_entry_on_cancel",
	},
	"Tally Ledger": {
		"after_insert": "tally_link.tally.events.tally_ledger_after_insert",
	},
	"Tally Stock Item": {
		"on_update": "tally_link.tally.events.tally_stock_item_on_update",
	},
}

# Migration
# ---------
# Ensures this app's Installed Applications entry never marks it as
# needing a setup wizard, so it reliably appears on the desk Apps screen
# (add_to_apps_screen) on every deployment, including Frappe Cloud.
after_migrate = [
	"tally_link.install.after_migrate"
]

# Scheduled Tasks
# ---------------

scheduler_events = {
	# Sync from Tally every 1 minute
	"cron": {
		"* * * * *": [
			"tally_link.tally.scheduled_sync.sync_all_from_tally"
		]
	}
}

# Testing
# -------

# before_tests = "tally_link.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tally_link.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tally_link.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tally_link.utils.before_request"]
# after_request = ["tally_link.utils.after_request"]

# Job Events
# ----------
# before_job = ["tally_link.utils.before_job"]
# after_job = ["tally_link.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"tally_link.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

