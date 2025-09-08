import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 120
		},
		{
			"fieldname": "loan_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "repaid_amount",
			"label": _("Repaid Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "remaining_balance",
			"label": _("Remaining Balance"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "loan_status",
			"label": _("Loan Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		}
	]

def get_data(filters):
	conditions = []
	values = []
	
	if filters.get("employee"):
		conditions.append("la.employee = %s")
		values.append(filters.get("employee"))
	
	if filters.get("department"):
		conditions.append("la.department = %s")
		values.append(filters.get("department"))
	
	if filters.get("loan_type"):
		conditions.append("la.loan_type = %s")
		values.append(filters.get("loan_type"))
	
	if filters.get("loan_status"):
		conditions.append("la.loan_status = %s")
		values.append(filters.get("loan_status"))
	
	if filters.get("from_date"):
		conditions.append("la.posting_date >= %s")
		values.append(filters.get("from_date"))
	
	if filters.get("to_date"):
		conditions.append("la.posting_date <= %s")
		values.append(filters.get("to_date"))
	
	where_clause = ""
	if conditions:
		where_clause = "AND " + " AND ".join(conditions)
	
	return frappe.db.sql(f"""
		SELECT 
			la.employee,
			la.employee_name,
			la.department,
			la.loan_type,
			la.total_amount,
			la.repaid_amount,
			la.remaining_balance,
			la.loan_status,
			la.posting_date
		FROM `tabLoan Application` la
		WHERE la.docstatus != 2 {where_clause}
		ORDER BY la.posting_date DESC
	""", values, as_dict=1)
