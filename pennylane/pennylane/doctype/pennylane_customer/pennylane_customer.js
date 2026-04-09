frappe.ui.form.on("Pennylane Customer", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Sync"), () => pennylane_sync_now(frm));
		}
	},
	first_name(frm) {
		update_full_name(frm);
	},
	last_name(frm) {
		update_full_name(frm);
	},
	customer_type(frm) {
		update_full_name(frm);
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

function update_full_name(frm) {
	if (frm.doc.customer_type !== "individual") return;
	const full = [frm.doc.first_name, frm.doc.last_name].filter(Boolean).join(" ");
	if (full) frm.set_value("customer_name", full);
}
