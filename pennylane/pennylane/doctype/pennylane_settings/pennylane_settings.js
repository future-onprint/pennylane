frappe.ui.form.on("Pennylane Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), () => {
			frm.call("test_connection").then((r) => {
				const status = r.message;
				frappe.show_alert({
					message: __("Connection status: {0}", [status]),
					indicator: status === "Connected" ? "green" : "red",
				});
				frm.reload_doc();
			});
		}, __("Actions"));

		frm.add_custom_button(__("Run Full Sync"), () => {
			const anySelected =
				frm.doc.force_sync_customers ||
				frm.doc.force_sync_invoices ||
				frm.doc.force_sync_quotes ||
				frm.doc.force_sync_products;

			if (!anySelected) {
				frappe.msgprint(__("Select at least one resource to sync in the Force Full Sync section."));
				return;
			}

			frappe.confirm(
				__("This will re-import all selected resources from Pennylane. Continue?"),
				() => {
					frm.call("run_full_sync").then((r) => {
						const jobs = r.message?.queued || [];
						frappe.show_alert({
							message: __("Full sync queued for: {0}", [jobs.join(", ") || "nothing"]),
							indicator: "blue",
						});
						frm.reload_doc();
					});
				}
			);
		}, __("Actions"));
	},
});
