frappe.ui.form.on("Pennylane Customer Quote", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Sync"), () => pennylane_sync_now(frm), __("Pennylane"));
		}
	},
});

function pennylane_sync_now(frm) {
	frappe.call({
		method: "pennylane.pennylane.api.sync_now",
		args: { doctype: frm.doctype, docname: frm.docname },
		freeze: true,
		freeze_message: __("Syncing with Pennylane…"),
		callback(r) {
			if (!r.exc) {
				frm.reload_doc();
				frappe.show_alert({ message: __("Synced successfully"), indicator: "green" });
			}
		},
	});
}
