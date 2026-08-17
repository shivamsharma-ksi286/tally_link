// Copyright (c) 2025, SVNIX Solutions and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tally Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), function() {
			frm.trigger("verify_server_connection");
		});
	},

	verify_server_connection(frm) {
		frappe.call({
			method: "tally_link.tally.test_tally_connection",
			args: {
				host: frm.doc.host,
				port: frm.doc.port
			},
			freeze: true,
			freeze_message: __("Verifying connection to Tally server..."),
			callback: function(r) {
				if (r.message) {
					if (r.message.success) {
						frm.set_value("connection_status", r.message.message);
						frappe.show_alert({
							message: r.message.message,
							indicator: "green"
						}, 5);
					} else {
						frm.set_value("connection_status", __("Connection Error: ") + r.message.message);
						frappe.show_alert({
							message: r.message.message,
							indicator: "red"
						}, 5);
					}
				}
			}
		});
	}
});
