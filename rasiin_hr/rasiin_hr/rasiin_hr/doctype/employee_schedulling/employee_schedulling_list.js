frappe.listview_settings['Employee Schedulling'] = {
    onload(listview) {
        listview.page.add_menu_item(__('Import Schedule'), () => {
            let d = new frappe.ui.Dialog({
                title: "Upload Schedule Excel File",
                fields: [
                    {
                        label: "Excel File",
                        fieldname: "file",
                        fieldtype: "Attach",
                        reqd: true
                    }
                ],
                primary_action_label: "Import",
                primary_action(values) {
                    frappe.call({
                        method: "his.his.doctype.employee_schedulling.importer.import_schedule",
                        args: {
                            file_url: values.file
                        },
                        freeze: true,
                        freeze_message: "Importing schedule…",
                        callback: function (r) {
                            if (!r.exc) {
                                frappe.msgprint("✔ Schedule Imported Successfully!");
                                d.hide();
                                listview.refresh();
                            }
                        }
                    });
                }
            });

            d.show();
        });
    }
};
