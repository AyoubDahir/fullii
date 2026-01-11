

import frappe
from hrms.payroll.doctype.payroll_entry.payroll_entry import  PayrollEntry
from erpnext.accounts.utils import get_balance_on
from hrms.hr.report.employee_advance_summary.employee_advance_summary import get_advances
from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from frappe.utils import getdate
class customPayrollEntry(PayrollEntry):
	def get_emp_list(self):
			"""
			Returns list of active employees based on selected criteria
			and for which salary structure exists
			"""
			self.check_mandatory()
			filters = self.make_filters()
			cond = get_filter_condition(filters)
			cond += get_joining_relieving_condition(self.start_date, self.end_date)

			condition = ""
			if self.payroll_frequency:
				condition = """and payroll_frequency = '%(payroll_frequency)s'""" % {
					"payroll_frequency": self.payroll_frequency
				}

			sal_struct = get_sal_struct(
				self.company, self.currency, self.salary_slip_based_on_timesheet, condition
			)
			if sal_struct:
				cond += "and t2.salary_structure IN %(sal_struct)s "
				cond += "and t2.payroll_payable_account = %(payroll_payable_account)s "
				cond += "and %(from_date)s >= t2.from_date"
				emp_list = get_emp_list(sal_struct, cond, self.end_date, self.payroll_payable_account)
				emp_list = remove_payrolled_employees(emp_list, self.start_date, self.end_date)
				for em in emp_list:
					em['advance'] = get_advances(em.employee) or 0
					em['receivables'] = get_receivable(em.employee_name) or 0
					salary_s = frappe.get_doc({
				
						"doctype" : "Salary Slip",
						 "employee" : em.employee,
						"start_date" : self.start_date,
						"end_date" : self.end_date,
						"payroll_frequency" : self.payroll_frequency,
						"posting_date" : self.posting_date
					})
					gr = make_salary_slip("Emp Salary" , salary_s) or 0
					emp_sl = frappe.db.get_value("Employee" , em.employee , "amount") or 0
					em['att_ded'] = emp_sl - gr.net_pay 
					total_diduction =  em['advance'] + em['receivables']  + em['att_ded']
					em['base_salary'] = emp_sl
					em['net_total'] = emp_sl - total_diduction
					em['total_deduction'] = total_diduction 
					em['allowance'] = frappe.db.get_value("Employee" , em.employee , "allowance") or 0
					em['net_total'] = em['net_total'] + em['allowance']
					
					# frappe.errprint(gr.gross_pay)
				return emp_list

def get_filter_condition(filters):
	cond = ""
	for f in ["company", "branch", "department", "designation"]:
		if filters.get(f):
			cond += " and t1." + f + " = " + frappe.db.escape(filters.get(f))

	return cond



def get_joining_relieving_condition(start_date, end_date):
	cond = """
		and ifnull(t1.date_of_joining, '1900-01-01') <= '%(end_date)s'
		and ifnull(t1.relieving_date, '2199-12-31') >= '%(start_date)s'
	""" % {
		"start_date": start_date,
		"end_date": end_date,
	}
	return cond



def get_sal_struct(
	company: str, currency: str, salary_slip_based_on_timesheet: int, condition: str
):
	return frappe.db.sql_list(
		"""
		select
			name from `tabSalary Structure`
		where
			docstatus = 1 and
			is_active = 'Yes'
			and company = %(company)s
			and currency = %(currency)s and
			ifnull(salary_slip_based_on_timesheet,0) = %(salary_slip_based_on_timesheet)s
			{condition}""".format(
			condition=condition
		),
		{
			"company": company,
			"currency": currency,
			"salary_slip_based_on_timesheet": salary_slip_based_on_timesheet,
		},
	)


def remove_payrolled_employees(emp_list, start_date, end_date):
	new_emp_list = []
	for employee_details in emp_list:
		if not frappe.db.exists(
			"Salary Slip",
			{
				"employee": employee_details.employee,
				"start_date": start_date,
				"end_date": end_date,
				"docstatus": 1,
			},
		):
			new_emp_list.append(employee_details)

	return new_emp_list

def get_emp_list(sal_struct, cond, end_date, payroll_payable_account):
	return frappe.db.sql(
		"""
			select
				distinct t1.name as employee, t1.employee_name, t1.department, t1.designation
			from
				`tabEmployee` t1, `tabSalary Structure Assignment` t2
			where
				t1.name = t2.employee
				and t2.docstatus = 1
				and t1.status != 'Inactive'
		%s order by t2.from_date desc
		"""
		% cond,
		{
			"sal_struct": tuple(sal_struct),
			"from_date": end_date,
			"payroll_payable_account": payroll_payable_account,
		},
		as_dict=True,
	)



@frappe.whitelist()
def get_receivable(customer):
	# frappe.msgprint(customer)
	bal= get_balance_on(company = frappe.defaults.get_user_default("Company"),
						party_type ="Customer",
						party =frappe.db.get_value("Customer",{"customer_name":customer , "customer_group" : "Employee"}, "name"),
						date = getdate())
	
	return bal
@frappe.whitelist()
def get_advances(emp):
	empl =frappe.db.get_value("Employee",{"employee_name":emp}, "name")
	bal= get_balance_on(company = frappe.defaults.get_user_default("Company"),
						party_type ="Employee",
						party =emp,
						date = getdate()
			
			)
	
	return bal
	
	# advance= frappe.db.sql(
	#     f"""select name, employee, paid_amount, status, advance_amount, claimed_amount, company,
	#     posting_date, purpose
	#     from `tabEmployee Advance`
	#     where docstatus<2 and employee='{emp}' order by posting_date, name desc""",
		
	#     as_dict=1,
	# )
	# advanced=0
	# for i in advance:
	#     advanced= i.advance_amount
		
	# return advanced
