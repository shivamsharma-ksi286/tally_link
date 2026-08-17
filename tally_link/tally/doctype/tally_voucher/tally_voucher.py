# Copyright (c) 2025, SVNIX Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TallyVoucher(Document):
	"""Tally Voucher - 1:1 representation of Tally Voucher in ERPNext"""

	def validate(self):
		"""Validate Tally Voucher"""
		self.calculate_totals()
		self.check_balanced()

	def calculate_totals(self):
		"""Calculate total debit and credit from ledger entries"""
		self.total_debit = 0
		self.total_credit = 0

		for entry in self.ledger_entries:
			if entry.is_debit:
				self.total_debit += entry.amount
			else:
				self.total_credit += entry.amount

	def check_balanced(self):
		"""Check if voucher is balanced"""
		if abs(self.total_debit - self.total_credit) < 0.01:
			self.is_balanced = 1
		else:
			self.is_balanced = 0
			frappe.msgprint(
				_("Voucher is not balanced. Debit: {0}, Credit: {1}").format(
					self.total_debit, self.total_credit
				),
				indicator="orange"
			)

	def on_submit(self):
		"""Handle voucher submission and sync to Tally"""
		if self.auto_sync and self.sync_direction in ["ERP to Tally", "Bidirectional"]:
			frappe.enqueue(
				"tally_link.tally.doctype_sync.sync_voucher_to_tally",
				queue="short",
				timeout=300,
				voucher_name=self.name,
				operation="create"
			)

	def on_cancel(self):
		"""Handle voucher cancellation"""
		self.is_cancelled = 1
		if self.auto_sync and self.sync_direction in ["ERP to Tally", "Bidirectional"]:
			frappe.enqueue(
				"tally_link.tally.doctype_sync.cancel_voucher_in_tally",
				queue="short",
				timeout=300,
				voucher_name=self.name
			)
