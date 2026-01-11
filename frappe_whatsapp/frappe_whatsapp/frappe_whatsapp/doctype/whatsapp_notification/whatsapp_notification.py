"""Notification."""

import json
import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals, safe_exec
from frappe.integrations.utils import make_post_request
from frappe.desk.form.utils import get_pdf_link
from frappe.utils import add_to_date, nowdate, datetime
import requests
from frappe.utils.pdf import get_pdf


class WhatsAppNotification(Document):
    """Notification."""

    # def validate(self):
    #     """Validate."""
    #     if self.notification_type == "DocType Event":
    #         fields = frappe.get_doc("DocType", self.reference_doctype).fields
    #         fields += frappe.get_all(
    #             "Custom Field",
    #             filters={"dt": self.reference_doctype},
    #             fields=["fieldname"]
    #         )
    #         if not any(field.fieldname == self.field_name for field in fields): # noqa
    #             frappe.throw(f"Field name {self.field_name} does not exists")
    #     if self.custom_attachment:
    #         if not self.attach and not self.attach_from_field:
    #             frappe.throw("Either <b>Attach</b> a file or add a <b>Attach from field</b> to send attachemt")

    def send_scheduled_message(self) -> dict:
        """Specific to API endpoint Server Scripts."""
        doc_data = self.as_dict()
        safe_exec(
            self.condition, get_safe_globals(), dict(doc=self)
        )
        language_code = frappe.db.get_value(
            "WhatsApp Templates", self.template,
            # fieldname='language_code'
            fieldname='language'
        )
        template_actual_name = frappe.db.get_value(
            "WhatsApp Templates", self.template,
            # fieldname='actual_name'
            fieldname='template_name'
        )
        

        pdf_path = generate_sales_register_pdf()
        
        if not pdf_path:
            frappe.throw("Failed to generate the Sales Register PDF.")

        file_doc = frappe.get_doc({
        "doctype": "File",
        "file_url": pdf_path,
        "file_name": "Sales_Register_Report.pdf",
        "is_private": 0, 
        })
        file_doc.save()
        pdf_url = frappe.utils.get_url(file_doc.file_url)
        

        if language_code:
            for contact in self.numbers:
                phone_number = contact.phone_number
                data = {
                    "messaging_product": "whatsapp",
                    # "to": contact,
                    "to": phone_number,
                    "type": "template",
                    "template": {
                        "name": template_actual_name,
                        "language": {
                            "code": language_code
                        },
                        "components": [
                             {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "document",
                                "document": {
                                    "link": pdf_url,
                                    "filename": "Sales_Register_Report.pdf"
                                }
                            }
                        ]
                    }
                        ]
                    }
                }
                self.content_type = data['template'].get("header_type", "text").lower()
                self.notify(data, doc_data)


        # return _globals.frappe.flags

    def send_template_message(self, doc: Document):
        """Specific to Document Event triggered Server Scripts."""
        if self.disabled:
            return

        doc_data = doc.as_dict()
        if self.condition:
            # check if condition satisfies
            if not frappe.safe_eval(
                self.condition, get_safe_globals(), dict(doc=doc_data)
            ):
                return

        template = frappe.db.get_value(
            "WhatsApp Templates", self.template,
            fieldname='*'
        )

        if template:
            data = {
                "messaging_product": "whatsapp",
                "to": self.format_number(doc_data[self.field_name]),
                "type": "template",
                "template": {
                    "name": template.actual_name,
                    "language": {
                        "code": template.language_code
                    },
                    "components": []
                }
            }

            # Pass parameter values
            if self.fields:
                parameters = []
                for field in self.fields:
                    value = doc_data[field.field_name]
                    if isinstance(doc_data[field.field_name], (datetime.date, datetime.datetime)):
                        value = str(doc_data[field.field_name])
                    parameters.append({
                        "type": "text",
                        "text": value
                    })

                data['template']["components"] = [{
                    "type": "body",
                    "parameters": parameters
                }]

            if self.attach_document_print:
                # frappe.db.begin()
                key = doc.get_document_share_key()  # noqa
                frappe.db.commit()
                print_format = "Standard"
                doctype = frappe.get_doc("DocType", doc_data['doctype'])
                if doctype.custom:
                    if doctype.default_print_format:
                        print_format = doctype.default_print_format
                else:
                    default_print_format = frappe.db.get_value(
                        "Property Setter",
                        filters={
                            "doc_type": doc_data['doctype'],
                            "property": "default_print_format"
                        },
                        fieldname="value"
                    )
                    print_format = default_print_format if default_print_format else print_format
                link = get_pdf_link(
                    doc_data['doctype'],
                    doc_data['name'],
                    print_format=print_format
                )

                filename = f'{doc_data["name"]}.pdf'
                url = f'{frappe.utils.get_url()}{link}&key={key}'

            elif self.custom_attachment:
                filename = self.file_name

                if self.attach_from_field:
                    file_url = doc_data[self.attach_from_field]
                    if not file_url.startswith("http"):
                        # get share key so that private files can be sent
                        key = doc.get_document_share_key()
                        file_url = f'{frappe.utils.get_url()}{file_url}&key={key}'
                else:
                    file_url = self.attach

                if file_url.startswith("http"):
                    url = f'{file_url}'
                else:
                    url = f'{frappe.utils.get_url()}{file_url}'

            if template.header_type == 'DOCUMENT':
                data['template']['components'].append({
                    "type": "header",
                    "parameters": [{
                        "type": "document",
                        "document": {
                            "link": url,
                            "filename": filename
                        }
                    }]
                })
            elif template.header_type == 'IMAGE':
                data['template']['components'].append({
                    "type": "header",
                    "parameters": [{
                        "type": "image",
                        "image": {
                            "link": url
                        }
                    }]
                })
            self.content_type = template.header_type.lower()
            # self.notify(data, doc_data)

            is_static = self.static_numbers
            if is_static:
                for number in self.numbers:
                    # frappe.errprint(f'number------: {number.phone_number}')
                    phone_number = number.phone_number
                    data['to'] = phone_number
                 
                    self.notify(data, doc_data)
                    # frappe.errprint(f'data------: {data}')
            else:
                self.notify(data, doc_data)

  

    def notify(self, data, doc_data):
        """Send text (with placeholders) AND then optionally send a PDF document to WhatsApp."""
        # frappe.errprint(f"[notify] data => {data}")

        settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
        token = settings.get_password("token")

        # Collect placeholders from doc_data
        parameters = {}
        if self.fields:
            for field in self.fields:
                # Use .get(...) with an empty-string fallback
                value = doc_data.get(field.field_name, "")
                if isinstance(value, (datetime.date, datetime.datetime)):
                    value = str(value)
                # If it's None or empty, we can default to something or keep it blank
                if value is None:
                    value = ""

                parameters[field.field_name] = value

        # The text template (e.g. "Kusoo dhawoow Hodan Hospital Mudane/Marwo {patient_name}")
        template_str = self.code or ""

        try:
            # STEP A: Send the TEXT MESSAGE
            text_message = template_str.format(**parameters)

            chat_url = f"{settings.url}/messages/chat"
            chat_payload = {
                "token": token,
                "to": data.get("to"),
                "body": text_message or "Hello"
            }
            # frappe.errprint(f"[notify] Sending text => {chat_payload}")
            chat_headers = {"content-type": "application/json"}
            chat_resp = requests.post(chat_url, json=chat_payload, headers=chat_headers)
            # frappe.errprint(f"[notify] Chat response => {chat_resp.text}")
            chat_resp.raise_for_status()

            # STEP B: Check if there's a PDF document to send
            try:
                first_component = data.get("template", {}).get("components", [])
                if first_component:
                    first_param = first_component[0].get("parameters", [])
                    if first_param and "document" in first_param[0]:
                        document_param = first_param[0]["document"]
                        doc_link = document_param["link"]
                        doc_filename = document_param.get("filename", "file.pdf")

                        doc_url = f"{settings.url}/messages/document"
                        doc_payload_str = (
                            f"token={token}"
                            f"&to={data.get('to')}"
                            f"&filename={doc_filename}"
                            f"&document={doc_link}"
                            f"&caption=Document attached"
                        )

                        # frappe.errprint(f"[notify] Document payload => {doc_payload_str}")
                        doc_headers = {"content-type": "application/x-www-form-urlencoded"}

                        doc_resp = requests.post(doc_url, data=doc_payload_str, headers=doc_headers)
                        # frappe.errprint(f"[notify] Document response => {doc_resp.text}")
                        doc_resp.raise_for_status()
                    else:
                        pass
                        # frappe.errprint("[notify] No 'document' parameter found; skipping PDF send.")
                else:
                    pass
                    # frappe.errprint("[notify] No 'components' found in template data; skipping PDF.")

            except Exception as doc_ex:
                frappe.throw(msg=f"Error sending PDF document: {doc_ex}", title="WhatsApp Notification Error")

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "WhatsApp Notification Error")
            frappe.throw(msg=f"Failed to send WhatsApp message: {e}", title="WhatsApp Notification Error")




    def on_trash(self):
        """On delete remove from schedule."""
        frappe.cache().delete_value("whatsapp_notification_map")

    # def format_number(self, number):
    #     """Format number."""
    #     if (number.startswith("+")):
    #         number = number[1:len(number)]

    def format_number(self, number):

        if not number:
            frappe.throw("Phone number is missing or empty.")
        
        if number.startswith("+"):
            number = number[1:]

        return number
   



    def get_documents_for_today(self):
        """get list of documents that will be triggered today"""
        docs = []

        diff_days = self.days_in_advance
        if self.doctype_event == "Days After":
            diff_days = -diff_days

        reference_date = add_to_date(nowdate(), days=diff_days)
        reference_date_start = reference_date + " 00:00:00.000000"
        reference_date_end = reference_date + " 23:59:59.000000"

        doc_list = frappe.get_all(
            self.reference_doctype,
            fields="name",
            filters=[
                {self.date_changed: (">=", reference_date_start)},
                {self.date_changed: ("<=", reference_date_end)},
            ],
        )

        for d in doc_list:
            doc = frappe.get_doc(self.reference_doctype, d.name)
            self.send_template_message(doc)
            # print(doc.name)

@frappe.whitelist()
def call_trigger_notifications():
    """Trigger notifications."""
    try:
        # Directly call the trigger_notifications function
        trigger_notifications()  
    except Exception as e:
        # Log the error but do not show any popup or alert
        frappe.log_error(frappe.get_traceback(), "Error in call_trigger_notifications")
        # Optionally, you could raise the exception to be handled elsewhere if needed
        raise e

def trigger_notifications(method="daily"):
    if frappe.flags.in_import or frappe.flags.in_patch:
        # don't send notifications while syncing or patching
        return

    if method == "daily":
        doc_list = frappe.get_all(
            "WhatsApp Notification", filters={"doctype_event": ("in", ("Days Before", "Days After")), "disabled": 0}
        )
        for d in doc_list:
            alert = frappe.get_doc("WhatsApp Notification", d.name)
            alert.get_documents_for_today()

from frappe.utils import formatdate, getdate
import psutil
from frappe.utils.pdf import get_pdf

def generate_sales_register_pdf():
    # Define filters for the Sales Register report
    filters = {
        "from_date": "2025-01-01",  # Replace with desired start date
        "to_date": "2025-01-25",    # Replace with desired end date
        "company": "Hodan Hospital"  # Replace with your company name
    }

    # Get the Sales Register report
    report_name = "Sales Register"
    report_doc = frappe.get_doc("Report", report_name)
    if not report_doc:
        frappe.throw(f"Report {report_name} not found.")

    # Generate report data
    columns, data = report_doc.get_data(filters=filters, as_dict=True)

    # Map the data rows to column fieldnames
    mapped_data = []
    for row in data:
        row["doctype"] = "Sales Invoice"  # Add 'doctype' for Frappe formatting
        row["name"] = row.get("invoice_number", "Unknown")  # Adjust based on your actual data

        # Format date fields
        for col in columns:
            fieldname = col.get("fieldname")
            fieldtype = col.get("fieldtype")

            # Format Date fields
            if fieldtype == "Date" and row.get(fieldname):
                try:
                    row[fieldname] = formatdate(getdate(row[fieldname]))
                except Exception:
                    frappe.throw(f"Invalid date format in field '{fieldname}': {row[fieldname]}")

        mapped_data.append(row)

    # Render the HTML using Frappe's template
    html = frappe.render_template("frappe/templates/includes/print_table.html", {
        "columns": columns,
        "data": mapped_data,
        "filters": filters,
        "title": report_name
    })

    # Convert the HTML to PDF
    pdf_content = get_pdf(html)

    # Save the PDF file
    file_name = "sales_register.pdf"
    file_path = frappe.utils.get_site_path("public", "files", file_name)

    with open(file_path, "wb") as f:
        f.write(pdf_content)

    # Get the first non-loopback IPv4 address
    eth_ip = next(
        (addr.address for addrs in psutil.net_if_addrs().values()
         for addr in addrs if addr.family == 2 and addr.address != "127.0.0.1"),
        None  # Default to None if no valid IP is found
    )

    # Construct the public URL
    if eth_ip:
        public_url = f"http://{eth_ip}/files/{file_name}"
    else:
        # Fallback to Frappe's default URL if no valid IP is found
        public_url = frappe.utils.get_url(f"/files/{file_name}")

    return public_url
