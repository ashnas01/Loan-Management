import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar

class LoanApplication(Document):
    def validate(self):
        self.validate_dates()
        self.validate_installment_count()
        self.calculate_amounts()
        self.set_title()
    def validate_dates(self):
        """Validate that all repayment dates are after posting date"""
        posting_date = datetime.strptime(str(self.posting_date), "%Y-%m-%d")
        
        if self.loan_type == "Advance" and self.advance_repayment_month:
            # Convert month string to last day of month
            last_day = self.get_last_day_of_month(self.advance_repayment_month)
            repayment_date = datetime.strptime(last_day, "%Y-%m-%d")
            
            if repayment_date <= posting_date:
                frappe.throw(_("Advance repayment month must be after posting date"))
                
        elif self.loan_type == "Loan":
            for schedule in self.repayment_schedule:
                if schedule.repayment_date:
                    repayment_date = datetime.strptime(str(schedule.repayment_date), "%Y-%m-%d")
                    if repayment_date < posting_date:
                        frappe.throw(_("All repayment dates must be after posting date"))
    
    def validate_installment_count(self):
        """Validate that selected repayment months match installment count for loans"""
        if self.loan_type == "Loan" and self.installments_count:
            if len(self.repayment_schedule) != self.installments_count:
                frappe.throw(_("Number of selected repayment months ({0}) must match installments count ({1})").format(
                    len(self.repayment_schedule), self.installments_count
                ))
    
    def calculate_amounts(self):
        """Calculate total amount, installment amount and remaining balance"""
        if self.loan_type == "Advance":
            self.total_amount = self.advance_amount or 0
        elif self.loan_type == "Loan":
            self.total_amount = self.loan_amount or 0
            if self.installments_count and self.loan_amount:
                self.installment_amount = self.loan_amount / self.installments_count
                
        self.remaining_balance = (self.total_amount or 0) - (self.repaid_amount or 0)
    
    def set_title(self):
        """Set document title for better identification"""
        if self.employee_name and self.loan_type:
            self.title = f"{self.employee_name} - {self.loan_type}"
    
    def before_save(self):
        """Set initial loan_status and ensure repayment schedule"""
        if self.is_new():
            self.loan_status = "Draft"
        self.ensure_repayment_schedule()
    
    def on_submit(self):
        """Only allow submission when fully repaid"""
        if self.remaining_balance > 0:
            frappe.throw(_("Cannot submit loan application until all repayments are completed. Remaining balance: {0}").format(self.remaining_balance))
        
        if self.loan_status != "Fully Repaid":
            frappe.throw(_("Cannot submit loan application. loan_status must be 'Fully Repaid'"))
    
    def on_cancel(self):
        """Actions to perform when document is cancelled"""
        self.loan_status = "Cancelled"
        # Reset any unpaid repayment schedules
        for schedule in self.repayment_schedule:
            if not schedule.is_paid:
                schedule.is_paid = 0
                schedule.paid_amount = 0
    
    def ensure_repayment_schedule(self):
        """Ensure repayment schedule exists with proper month/year display"""
        if self.loan_type == "Advance" and self.advance_repayment_month:
            # Check if schedule already exists
            if not any(schedule for schedule in self.repayment_schedule):
                last_day = self.get_last_day_of_month(self.advance_repayment_month)
                month_year_display = self.format_month_year_display(self.advance_repayment_month)
                
                self.append("repayment_schedule", {
                    "repayment_month_year": month_year_display,
                    "repayment_date": last_day,
                    "installment_amount": self.advance_amount
                })
        
        elif self.loan_type == "Loan":
            # Update installment amounts and month/year display in existing schedule
            for schedule in self.repayment_schedule:
                schedule.installment_amount = self.installment_amount
                # Update month/year display if not already set
                if schedule.repayment_date and not schedule.repayment_month_year:
                    month_str = str(schedule.repayment_date)[:7]  # Extract YYYY-MM
                    schedule.repayment_month_year = self.format_month_year_display(month_str)
    
    def get_last_day_of_month(self, month_str):
        """Get last day of month from YYYY-MM string"""
        year, month = map(int, month_str.split('-'))
        last_day = calendar.monthrange(year, month)[1]
        return f"{year}-{month:02d}-{last_day:02d}"
    
    def format_month_year_display(self, month_str):
        """Format YYYY-MM to 'MMM YYYY' for display"""
        year, month = map(int, month_str.split('-'))
        month_name = calendar.month_abbr[month]
        return f"{month_name} {year}"
    
    def update_repaid_amount(self, paid_amount, schedule_name):
        """Update repaid amount when payment is made - called from payroll hooks"""
        self.repaid_amount = (self.repaid_amount or 0) + paid_amount
        self.remaining_balance = self.total_amount - self.repaid_amount
        
        # Update loan_status based on repayment progress
        if self.remaining_balance <= 0:
            self.loan_status = "Fully Repaid"
            # Auto-submit when fully repaid (if not already submitted)
            if self.docstatus == 0:
                self.submit()
        else:
            self.loan_status = "Partially Repaid"
            # Set to approved loan_status if this is the first payment
            if self.loan_status == "Draft":
                self.loan_status = "Approved"
        
        # Update specific schedule item
        for schedule in self.repayment_schedule:
            if schedule.name == schedule_name:
                schedule.paid_amount = paid_amount
                schedule.is_paid = 1
                break
        
        self.save()

    def approve_loan(self):
        """Approve the loan application - can be called by HR"""
        if self.docstatus != 0:
            frappe.throw(_("Loan application is already processed"))
        
        self.loan_status = "Approved"
        self.save()
        
        frappe.msgprint(_("Loan application has been approved. Employee can now receive deductions in payroll."))

@frappe.whitelist()
def get_pending_loans(employee, payroll_date):
    """Get pending loan repayments for an employee for a specific payroll period"""
    from frappe.utils import getdate
    payroll_date = getdate(payroll_date)
    
    return frappe.db.sql("""
        SELECT 
            la.name,
            la.employee,
            la.loan_type,
            lrs.name as schedule_name,
            lrs.installment_amount,
            lrs.repayment_date,
            lrs.repayment_month_year
        FROM `tabLoan Application` la
        INNER JOIN `tabLoan Repayment Schedule` lrs ON lrs.parent = la.name
        WHERE la.employee = %s
            AND la.loan_status IN ('Approved', 'Partially Repaid')
            AND lrs.is_paid = 0
            AND MONTH(lrs.repayment_date) = %s
            AND YEAR(lrs.repayment_date) = %s
            AND la.docstatus = 0
    """, (employee, payroll_date.month, payroll_date.year), as_dict=1)

@frappe.whitelist()
def approve_loan_application(loan_name):
    """Approve a loan application"""
    loan_doc = frappe.get_doc("Loan Application", loan_name)
    loan_doc.approve_loan()
    return {"message": f"Loan application {loan_name} approved successfully"}

@frappe.whitelist()
def get_available_months(posting_date, months_ahead=24):
    """
    Get available months for selection - includes current month and future months
    """
    from frappe.utils import getdate, add_months

    # ensure types are correct
    posting_date = getdate(posting_date)
    months_ahead = int(months_ahead)

    months = []
    
    # Start from current month (0 months ahead) instead of next month
    for i in range(0, months_ahead + 1):
        month_date = add_months(posting_date, i)
        month_str = month_date.strftime("%Y-%m")
        display_name = month_date.strftime("%b %Y")

        months.append({
            "value": month_str,
            "label": display_name,
            "last_day": get_last_day_of_month_util(month_str)
        })

    return months

def get_last_day_of_month_util(month_str):
    """Utility function to get last day of month"""
    year, month = map(int, month_str.split('-'))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-{last_day:02d}"
