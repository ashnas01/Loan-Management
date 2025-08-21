frappe.query_reports["Loan Summary"] = {
	"filters": [
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee"
		},
		{
			fieldname: "department", 
			label: __("Department"),
			fieldtype: "Link",
			options: "Department"
		},
		{
			fieldname: "loan_type",
			label: __("Loan Type"),
			fieldtype: "Select",
			options: "\nAdvance\nLoan"
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select", 
			options: "\nApproved\nPartially Repaid\nFully Repaid"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		}
	]
};
