frappe.ui.form.on("Pennylane Product", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.sync_status === "Deleted") {
			frm.add_custom_button(__("Delete"), () => pennylane_delete_doc(frm))
				.addClass("btn-danger");
		} else {
			frm.add_custom_button(__("Sync"), () => pennylane_sync_now(frm));
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
				if (r.message.status === "deleted") {
					frappe.show_alert({
						message: __("This record no longer exists in Pennylane and has been marked as Deleted."),
						indicator: "orange",
					});
				} else {
					frappe.show_alert({ message: __("Synced successfully"), indicator: "green" });
				}
			}
		},
	});
}

function pennylane_delete_doc(frm) {
	frappe.confirm(
		__("Permanently delete this record from Frappe?"),
		() => {
			frappe.call({
				method: "pennylane.pennylane.api.delete_doc",
				args: { doctype: frm.doctype, docname: frm.docname },
				freeze: true,
				freeze_message: __("Deleting…"),
				callback(r) {
					if (!r.exc) {
						frappe.set_route("List", frm.doctype);
					}
				},
			});
		}
	);
}
