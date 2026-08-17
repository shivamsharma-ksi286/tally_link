// Copyright (c) 2025, SVNIX Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tally Sync Log", {
	refresh(frm) {
		const syncStatus = frm.doc.status;
		const statusColourMap = {
			"Success": "green",
			"Failed": "red",
			"Partial": "orange"
		};
		if (syncStatus && statusColourMap[syncStatus]) {
			frm.dashboard.set_headline_alert(
				`<span class="indicator ${statusColourMap[syncStatus]}"> ${syncStatus}</span>`
			);
		}

		if (frm.doc.reference_doctype && frm.doc.reference_name) {
			frm.add_custom_button(
				__("Open {0}", [frm.doc.reference_name]),
				function () {
					frappe.set_route("Form", frm.doc.reference_doctype, frm.doc.reference_name);
				}
			);
		}

		if (frm.doc.status === "Failed" && frm.doc.reference_doctype === "Tally Ledger" && frm.doc.reference_name) {
			frm.add_custom_button(__("Retry Sync"), function () {
				frappe.call({
					method: "tally_link.tally.doctype_sync.sync_ledger_to_tally",
					args: {
						ledger_name: frm.doc.reference_name,
						operation: frm.doc.operation ? frm.doc.operation.toLowerCase() : "update"
					},
					freeze: true,
					freeze_message: __("Retrying synchronisation..."),
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({ message: __("Synchronisation completed successfully."), indicator: "green" }, 5);
						} else {
							frappe.show_alert({
								message: __("Synchronisation failed: ") + (r.message ? r.message.error : ""),
								indicator: "red"
							}, 7);
						}
					}
				});
			}, __("Actions"));
		}

		frm.disable_save();
	}
});
