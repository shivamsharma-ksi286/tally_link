// Copyright (c) 2025, SVNIX Solutions and contributors
// Tally integration override for Payment Entry

frappe.ui.form.on("Payment Entry", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Push to Tally"), function () {
				frappe.call({
					method: "tally_link.tally.api.push_payment_entry_to_tally",
					args: { payment_entry_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Pushing to Tally..."),
					callback(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __("Payment Entry pushed to Tally successfully"),
								indicator: "green"
							}, 7);
							frm.reload_doc();
						} else {
							const msg = (r.message && r.message.message) || __("Unknown error. Check Error Log.");
							frappe.msgprint({
								title: __("Tally Push Failed"),
								message: msg,
								indicator: "red"
							});
						}
					}
				});
			});
		}
	}
});
