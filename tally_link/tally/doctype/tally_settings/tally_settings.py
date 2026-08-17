# Copyright (c) 2025, SVNIX Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TallySettings(Document):
	"""Tally Settings DocType for managing Tally integration configuration"""

	def validate(self):
		"""Validate Tally settings"""
		if self.enabled:
			if not self.host:
				frappe.throw(_("Tally Server Host is required when Tally integration is enabled"))
			if not self.port:
				frappe.throw(_("Tally Server Port is required when Tally integration is enabled"))

	def on_update(self):
		"""Clear cache when settings are updated"""
		frappe.cache().delete_value("tally_settings")
