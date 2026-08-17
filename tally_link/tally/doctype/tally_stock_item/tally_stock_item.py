# Copyright (c) 2025, SVNIX Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TallyStockItem(Document):
	"""Tally Stock Item - 1:1 representation of Tally Stock Item in ERPNext"""

	def validate(self):
		"""Validate Tally Stock Item"""
		if not self.item_name:
			frappe.throw(_("Item Name is required"))

	def on_update(self):
		"""Handle updates and sync to Tally if auto_sync is enabled"""
		if self.auto_sync and self.sync_direction in ["ERP to Tally", "Bidirectional"]:
			if self.has_value_changed("item_name") or self.has_value_changed("category"):
				frappe.enqueue(
					"tally_link.tally.doctype_sync.sync_stock_item_to_tally",
					queue="short",
					timeout=300,
					item_name=self.name,
					operation="update"
				)

	def after_insert(self):
		"""Handle new item creation"""
		if self.auto_sync and self.sync_direction in ["ERP to Tally", "Bidirectional"]:
			frappe.enqueue(
				"tally_link.tally.doctype_sync.sync_stock_item_to_tally",
				queue="short",
				timeout=300,
				item_name=self.name,
				operation="create"
			)
