import frappe
from frappe import _
from frappe.utils import getdate
import calendar
import traceback

def process_loan_deductions(doc, method):
    """Process loan deductions for all employees in payroll entry"""
    for employee_detail in doc.employees:
        # Fetch the Salary Slip for this employee from Payroll Entry
        salary_slip_name = frappe.db.get_value(
            "Salary Slip",
            {"payroll_entry": doc.name, "employee": employee_detail.employee, "docstatus": 1},
            "name"
        )

        if not salary_slip_name:
            continue  # No slip yet, skip

        add_loan_deductions_to_slip(
            frappe.get_doc("Salary Slip", salary_slip_name),
            method="payroll_entry"
        )

def add_loan_deductions_to_slip(doc, method):
    """Add loan deductions to salary slip (only append rows, no updates yet)"""
    if not doc.employee or not doc.start_date or not doc.end_date:
        return

    payroll_date = getdate(doc.end_date)
    pending_loans = get_pending_loans_for_payroll(doc.employee, payroll_date)

    for loan in pending_loans:
        salary_component = get_or_create_loan_salary_component(loan.loan_type)

        exists = any(
            d.salary_component == salary_component
            and d.get("loan_application") == loan.name
            and d.get("loan_schedule") == loan.schedule_name
            for d in doc.deductions
        )

        if not exists:
            doc.append("deductions", {
                "salary_component": salary_component,
                "amount": loan.installment_amount,
                "loan_application": loan.name,
                "loan_schedule": loan.schedule_name
            })

def update_repayments_after_submit(doc, method):
    """Update repayment schedules after Salary Slip is submitted (safe to link now)"""
    payroll_date = getdate(doc.posting_date)
    pending_loans = get_pending_loans_for_payroll(doc.employee, payroll_date)

    frappe.logger().info(f"🔎 Hook triggered for Salary Slip: {doc.name}, Loans: {len(pending_loans)}")

    for loan in pending_loans:
        frappe.logger().info(f"👉 Processing loan: {loan.name} for employee: {doc.employee}")
        update_loan_repayment_status(loan, doc.name, payroll_date)
        frappe.logger().info(f"✅ Loan updated: {loan.name}")

def get_pending_loans_for_payroll(employee, payroll_date):
    # print("$"*85)
    """Get pending loan repayments for an employee for a specific payroll period"""
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

def get_or_create_loan_salary_component(loan_type):
    """Get or create salary component for loan deductions"""
    component_name = f"Loan Deduction - {loan_type}"

    if not frappe.db.exists("Salary Component", component_name):
        salary_component = frappe.new_doc("Salary Component")
        salary_component.salary_component = component_name
        salary_component.type = "Deduction"
        salary_component.is_tax_applicable = 0
        salary_component.is_flexible_benefit = 0
        salary_component.save(ignore_permissions=True)
        frappe.db.commit()

    return component_name

def update_loan_repayment_status(loan_info, salary_slip_name, payroll_date):
    """Update loan repayment schedule and loan status with actual payment date"""
    import traceback

    try:
        # print("$"*85)
        # Update repayment schedule
        schedule_doc = frappe.get_doc("Loan Repayment Schedule", loan_info.schedule_name)
        schedule_doc.paid_amount = loan_info.installment_amount
        schedule_doc.is_paid = 1
        schedule_doc.salary_slip = salary_slip_name
        schedule_doc.payment_date = payroll_date
        schedule_doc.repayment_date = payroll_date
        schedule_doc.repayment_month_year = (
            f"{payroll_date.strftime('%b %Y')} (Paid: {payroll_date.strftime('%d-%b-%Y')})"
        )
        schedule_doc.save(ignore_permissions=True)

        # Update loan application
        loan_doc = frappe.get_doc("Loan Application", loan_info.name)
        loan_doc.repaid_amount = (loan_doc.repaid_amount or 0) + loan_info.installment_amount
        loan_doc.remaining_balance = loan_doc.total_amount - loan_doc.repaid_amount

        # ✅ Do NOT reset advance_repayment_month here
        if loan_doc.remaining_balance <= 0:
            loan_doc.loan_status = "Fully Repaid"
        else:
            loan_doc.loan_status = "Partially Repaid"

        loan_doc.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(
            message=f"""
            Loan Repayment Update Error
            Loan: {loan_info}
            Salary Slip: {salary_slip_name}
            Error: {str(e)}
            Trace: {traceback.format_exc()}
            """,
            title="Loan Repayment Error"
        )
        frappe.throw(_("Error processing loan deduction: {0}").format(str(e)))
