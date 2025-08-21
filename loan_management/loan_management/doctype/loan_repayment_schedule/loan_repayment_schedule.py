import frappe
from frappe.model.document import Document

class LoanRepaymentSchedule(Document):
	def validate(self):
		if self.paid_amount > self.installment_amount:
			frappe.throw("Paid amount cannot be greater than installment amount")
