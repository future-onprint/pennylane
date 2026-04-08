frappe.ui.form.on("Pennylane Customer", {
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

function update_full_name(frm) {
	if (frm.doc.customer_type !== "individual") return;
	const full = [frm.doc.first_name, frm.doc.last_name].filter(Boolean).join(" ");
	if (full) frm.set_value("customer_name", full);
}
