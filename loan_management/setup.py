import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
	"""Setup function to run after app installation"""
	create_salary_components()
	create_custom_fields_for_salary_detail()
	create_reports()
	frappe.db.commit()

def create_salary_components():
	"""Create default salary components for loan deductions"""
	components = [
		{
			"salary_component": "Loan Deduction - Advance",
			"type": "Deduction",
			"is_tax_applicable": 0,
			"is_flexible_benefit": 0
		},
		{
			"salary_component": "Loan Deduction - Loan", 
			"type": "Deduction",
			"is_tax_applicable": 0,
			"is_flexible_benefit": 0
		}
	]
	
	for component in components:
		if not frappe.db.exists("Salary Component", component["salary_component"]):
			doc = frappe.new_doc("Salary Component")
			doc.update(component)
			doc.save(ignore_permissions=True)

def create_custom_fields_for_salary_detail():
	"""Create custom fields in Salary Detail for loan tracking"""
	custom_fields = {
		"Salary Detail": [
			{
				"fieldname": "loan_application",
				"label": "Loan Application",
				"fieldtype": "Link",
				"options": "Loan Application",
				"insert_after": "salary_component",
				"read_only": 1,
				"hidden": 1
			},
			{
				"fieldname": "loan_schedule", 
				"label": "Loan Schedule",
				"fieldtype": "Link",
				"options": "Loan Repayment Schedule",
				"insert_after": "loan_application",
				"read_only": 1,
				"hidden": 1
			}
		]
	}
	
	create_custom_fields(custom_fields, update=True)

def create_reports():
	"""Create custom reports for loan management"""
	reports = [
		{
			"report_name": "Loan Summary",
			"report_type": "Script Report",
			"ref_doctype": "Loan Application",
			"module": "Loan Management",
			"is_standard": "Yes"
		},
		{
			"report_name": "Employee Loan Statement",
			"report_type": "Script Report", 
			"ref_doctype": "Loan Application",
			"module": "Loan Management",
			"is_standard": "Yes"
		}
	]
	
	for report in reports:
		if not frappe.db.exists("Report", report["report_name"]):
			doc = frappe.new_doc("Report")
			doc.update(report)
			doc.save(ignore_permissions=True)
