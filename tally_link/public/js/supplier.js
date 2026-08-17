// Copyright (c) 2026, Ksolves India Limited and contributors
// Tally integration override for Supplier

frappe.ui.form.on("Supplier", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Push to Tally"), function () {
				frappe.call({
					method: "tally_link.tally.api.push_supplier_to_tally",
					args: { supplier_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Pushing to Tally..."),
					callback(r) {
						if (r.message && r.message.success) {
							if (r.message.warning) {
								frappe.msgprint({
									title: __("Pushed with a Warning"),
									message: r.message.warning,
									indicator: "orange"
								});
							} else {
								frappe.show_alert({
									message: __("Supplier pushed to Tally successfully"),
									indicator: "green"
								}, 7);
							}
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
