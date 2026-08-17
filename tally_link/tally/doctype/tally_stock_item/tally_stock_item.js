// Copyright (c) 2025, SVNIX Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tally Stock Item", {
	refresh(frm) {
		frm.trigger("apply_sync_status_indicator");

		if (!frm.is_new()) {
			frm.add_custom_button(__("Push to Tally"), function () {
				frm.trigger("transmit_to_tally");
			}, __("Actions"));

			frm.add_custom_button(__("View Sync Logs"), function () {
				frappe.route_options = {
					entity_name: frm.doc.item_name,
					entity_type: "Stock Item"
				};
				frappe.set_route("List", "Tally Sync Log");
			}, __("Actions"));

			if (frm.doc.linked_doctype && frm.doc.linked_docname) {
				frm.add_custom_button(__("Open Linked Document"), function () {
					frappe.set_route("Form", frm.doc.linked_doctype, frm.doc.linked_docname);
				}, __("Actions"));
			}
		}
	},

	transmit_to_tally(frm) {
		frappe.confirm(
			__("Transmit stock item <b>{0}</b> to Tally?", [frm.doc.item_name]),
			function () {
				frappe.call({
					method: "tally_link.tally.doctype_sync.sync_stock_item_to_tally",
					args: {
						item_name: frm.doc.name,
						operation: "update"
					},
					freeze: true,
					freeze_message: __("Transmitting to Tally. Please wait..."),
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __("Stock item transmitted to Tally successfully."),
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

	auto_sync(frm) {
		if (frm.doc.auto_sync && !frm.doc.sync_direction) {
			frm.set_value("sync_direction", "Tally to ERP");
		}
	},

	linked_doctype(frm) {
		frm.set_value("linked_docname", "");
	}
});
