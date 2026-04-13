frappe.ui.form.on("Pennylane Customer Quote", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.sync_status === "Deleted") {
			frm.add_custom_button(__("Delete"), () => pennylane_delete_doc(frm))
				.addClass("btn-danger");
		} else {
			frm.add_custom_button(__("Sync"), () => pennylane_sync_now(frm));
		}

		if (frm.doc.pennylane_id) {
			frm.add_custom_button(__("Open in Pennylane"), () => {
				frappe.db.get_single_value("Pennylane Settings", "company_id").then(company_id => {
					if (!company_id) {
						frappe.throw(__("Company ID not configured in Pennylane Settings."));
						return;
					}
					window.open(
						`https://app.pennylane.com/companies/${company_id}/clients/customer_estimates?estimate_id=${frm.doc.pennylane_id}`,
						"_blank"
					);
				});
			});
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
