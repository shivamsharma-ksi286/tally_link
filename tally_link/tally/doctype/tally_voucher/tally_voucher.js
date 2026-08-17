// Copyright (c) 2025, SVNIX Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tally Voucher", {
	refresh(frm) {
		frm.trigger("apply_sync_status_indicator");
		frm.trigger("toggle_tally_cancel_action");

		if (!frm.is_new() && frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Push to Tally"), function () {
				frm.trigger("transmit_to_tally");
			}, __("Actions"));
		}

		if (!frm.is_new()) {
			frm.add_custom_button(__("View Sync Logs"), function () {
				frappe.route_options = {
					entity_name: frm.doc.name,
					entity_type: "Voucher"
				};
				frappe.set_route("List", "Tally Sync Log");
			}, __("Actions"));
		}

		if (frm.doc.is_cancelled) {
			frm.dashboard.set_headline_alert(
				'<span class="indicator red">Cancelled in Tally</span>'
			);
		}
	},

	transmit_to_tally(frm) {
		frappe.confirm(
			__("Transmit voucher <b>{0}</b> to Tally?", [frm.doc.name]),
			function () {
				frappe.call({
					method: "tally_link.tally.doctype_sync.sync_voucher_to_tally",
					args: {
						voucher_name: frm.doc.name,
						operation: "create"
					},
					freeze: true,
					freeze_message: __("Transmitting voucher to Tally. Please wait..."),
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __("Voucher transmitted to Tally successfully."),
								indicator: "green"
							}, 5);
							frm.reload_doc();
						} else {
							frappe.msgprint({
								title: __("Transmission Failed"),
								message: r.message ? r.message.error : __("An unknown error occurred."),
								indicator: "red"
							});
						}
					}
				});
			}
		);
	},

	toggle_tally_cancel_action(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.is_cancelled) {
			frm.add_custom_button(__("Cancel in Tally"), function () {
				frappe.confirm(
					__("This will cancel voucher <b>{0}</b> in Tally. Continue?", [frm.doc.name]),
					function () {
						frappe.call({
							method: "tally_link.tally.doctype_sync.cancel_voucher_in_tally",
							args: { voucher_name: frm.doc.name },
							freeze: true,
							freeze_message: __("Processing cancellation in Tally. Please wait..."),
							callback(r) {
								if (r.message && r.message.success) {
									frappe.show_alert({
										message: __("Voucher has been cancelled in Tally."),
										indicator: "green"
									}, 5);
									frm.reload_doc();
								} else {
									frappe.msgprint({
										title: __("Cancellation Failed"),
										message: r.message ? r.message.error : __("An unknown error occurred."),
										indicator: "red"
									});
								}
							}
						});
					}
				);
			}, __("Actions"));
		}
	},

	apply_sync_status_indicator(frm) {
		const syncStatus = frm.doc.sync_status;
		const statusColourMap = {
			"Synced": "green",
			"Failed": "red",
			"Pending": "orange",
			"Conflict": "yellow"
		};
		if (syncStatus && statusColourMap[syncStatus]) {
			frm.dashboard.set_headline_alert(
				`<span class="indicator ${statusColourMap[syncStatus]}"> ${syncStatus}</span>`
			);
		}
	},

	voucher_type(frm) {
		if (["Journal", "Contra"].includes(frm.doc.voucher_type)) {
			frm.set_value("party_ledger_name", "");
		}
	}
});

frappe.ui.form.on("Tally Voucher Ledger Entry", {
	amount(frm) {
		frm.trigger("recalculate_ledger_totals");
	},

	is_debit(frm) {
		frm.trigger("recalculate_ledger_totals");
	},

	ledger_entries_remove(frm) {
		frm.trigger("recalculate_ledger_totals");
	},

	recalculate_ledger_totals(frm) {
		let total_debit = 0;
		let total_credit = 0;
		(frm.doc.ledger_entries || []).forEach(row => {
			if (row.is_debit) {
				total_debit += flt(row.amount);
			} else {
				total_credit += flt(row.amount);
			}
		});
		frm.set_value("total_debit", total_debit);
		frm.set_value("total_credit", total_credit);
		frm.set_value("is_balanced", Math.abs(total_debit - total_credit) < 0.01);
	}
});
