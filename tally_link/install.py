# Copyright (c) 2026, Ksolves India Limited and contributors
# For license information, please see license.txt

"""
Install / migrate hooks for Tally Link.
"""

import frappe


def ensure_no_setup_wizard():
	"""
	Force this app's entry in Installed Applications to have
	has_setup_wizard = 0, so it always appears on the desk Apps screen
	(add_to_apps_screen) regardless of how the underlying record was
	populated on a given deployment.
	"""
	try:
		doc = frappe.get_single("Installed Applications")
		changed = False
		for row in doc.installed_applications:
			if row.app_name == "tally_link" and (row.has_setup_wizard or row.is_setup_complete):
				row.has_setup_wizard = 0
				row.is_setup_complete = 0
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.clear_cache()
	except Exception:
		frappe.log_error(title="Tally Link: failed to fix Installed Applications entry")


def after_install():
	ensure_no_setup_wizard()


def after_migrate():
	ensure_no_setup_wizard()
