frappe.ui.form.on('Loan Application', {
    refresh: function(frm) {  
        // Set custom buttons and actions 
        if (frm.doc.docstatus === 0 && frm.doc.loan_status === 'Draft') { 
            frm.add_custom_button(__('Approve Loan'), function() { 
                frappe.call({ 
                    method: 'loan_management.loan_management.doctype.loan_application.loan_application.approve_loan_application', 
                    args: { loan_name: frm.doc.name }, 

                    callback: function(r) { 
                        if (r.message) { 
                            frappe.msgprint(r.message.message); 
                            frm.reload_doc(); 
                        } 
                    } 
                }); 
            }, ); 
        } 
        // Add custom button to view salary slips
        if (frm.doc.docstatus === 0 && frm.doc.loan_status !== 'Draft') { 
            frm.add_custom_button(__('View Salary Slips'), function() { 
                frappe.route_options = { 
                    "employee": frm.doc.employee, 
                    "docstatus": 1 
                }; 
                frappe.set_route("List", "Salary Slip"); 
            }); 
        } 

        // Show submission info 
        if (frm.doc.remaining_balance > 0 && frm.doc.loan_status !== 'Draft') { 
            frm.dashboard.add_comment( __('Document can only be submitted when all repayments are completed. Remaining balance: {0}', [format_currency(frm.doc.remaining_balance)]), 'blue', true ); 
        } 

        // Initialize month selection container 
        if (!$('#month-selection-container').length) { 
            $(frm.fields_dict['repayment_schedule'].wrapper).after('<div id="month-selection-container"></div>'); 
        } 

        // Re-setup month selection if needed 
        if (frm.doc.loan_type === 'Loan' && frm.doc.installments_count && frm.doc.posting_date) { 
            setTimeout(() => { 
                setup_month_selection_interface(frm);
            }, 100); 
        } 
        
    },

    loan_type: function(frm) {
        // Clear dependent fields when loan type changes
        if (frm.doc.loan_type === 'Advance') {
            frm.set_value('loan_amount', 0);
            frm.set_value('installments_count', 0);
            frm.set_value('installment_amount', 0);
            frm.fields_dict['advance_repayment_month'].df.options = '';
            frm.refresh_field('advance_repayment_month');
            setup_advance_month_options(frm);
        } else if (frm.doc.loan_type === 'Loan') {
            frm.set_value('advance_amount', 0);
            frm.set_value('advance_repayment_month', '');
        }
        
        // Clear repayment schedule
        frm.clear_table('repayment_schedule');
        frm.refresh_field('repayment_schedule');
        
        // Clear month selection interface
        if (frm.doc.loan_type !== 'Loan') {
            $('#month-selection-container').empty();
        }
    },

    posting_date: function(frm) {
        if (frm.doc.loan_type === 'Advance') {
            setup_advance_month_options(frm);
        } else if (frm.doc.loan_type === 'Loan' && frm.doc.installments_count) {
            setup_month_selection_interface(frm);
        }
    },

    advance_amount: function(frm) {
        if (frm.doc.loan_type === 'Advance') {
            frm.set_value('total_amount', frm.doc.advance_amount);
            calculate_remaining_balance(frm);
        }
    },

    advance_repayment_month: function(frm) {
        if (frm.doc.loan_type === 'Advance' && frm.doc.advance_repayment_month) {
            // Clear existing schedule
            frm.clear_table('repayment_schedule');
            
            // Get last day of selected month
            frappe.call({
                method: 'loan_management.loan_management.doctype.loan_application.loan_application.get_available_months',
                args: {
                    posting_date: frm.doc.posting_date,
                    months_ahead: 24
                },
                callback: function(r) {
                    if (r.message) {
                        let selected_month = r.message.find(m => m.value === frm.doc.advance_repayment_month);
                        if (selected_month) {
                            let child = frm.add_child('repayment_schedule');
                            child.repayment_month_year = selected_month.label;
                            child.repayment_date = selected_month.last_day;
                            child.installment_amount = frm.doc.advance_amount;
                            frm.refresh_field('repayment_schedule');
                        }
                    }
                }
            });
        }
    },

    loan_amount: function(frm) {
        if (frm.doc.loan_type === 'Loan') {
            frm.set_value('total_amount', frm.doc.loan_amount);
            calculate_installment_amount(frm);
            calculate_remaining_balance(frm);
        }
    },

    installments_count: function(frm) {
        calculate_installment_amount(frm);
        
        if (frm.doc.loan_type === 'Loan' && frm.doc.installments_count && frm.doc.posting_date) {
            setup_month_selection_interface(frm);
        }
    },

    repaid_amount: function(frm) {
        calculate_remaining_balance(frm);
    }
});

frappe.ui.form.on('Loan Repayment Schedule', {
    repayment_schedule_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (frm.doc.loan_type === 'Loan' && frm.doc.installment_amount) {
            frappe.model.set_value(cdt, cdn, 'installment_amount', frm.doc.installment_amount);
        }
    },

    repayment_date: function(frm, cdt, cdn) {
        // Validate repayment date
        let row = locals[cdt][cdn];
        if (row.repayment_date && frm.doc.posting_date) {
            if (frappe.datetime.get_diff(row.repayment_date, frm.doc.posting_date) <= 0) {
                frappe.msgprint(__('Repayment date must be after posting date'));
                frappe.model.set_value(cdt, cdn, 'repayment_date', '');
            }
        }
    }
});

function setup_advance_month_options(frm) {
    if (!frm.doc.posting_date) return;
    
    frappe.call({
        method: 'loan_management.loan_management.doctype.loan_application.loan_application.get_available_months',
        args: {
            posting_date: frm.doc.posting_date,
            months_ahead: 24
        },
        callback: function(r) {
            if (r.message) {
                let options = r.message.map(month => month.value).join('\n');
                frm.fields_dict['advance_repayment_month'].df.options = '\n' + options;
                frm.refresh_field('advance_repayment_month');
            }
        }
    });
}

function setup_month_selection_interface(frm) {
    if (!frm.doc.posting_date || !frm.doc.installments_count) return;

    frappe.call({
        method: 'loan_management.loan_management.doctype.loan_application.loan_application.get_available_months',
        args: {
            posting_date: frm.doc.posting_date,
            months_ahead: 24
        },
        callback: function(r) {
            if (r.message) {
                // Store form reference globally for event handlers
                window.current_loan_form = frm;

                let html = `
                    <div style="border: 1px solid #d1d8dd; padding: 15px; border-radius: 5px; background-color: #f8f9fa; margin-top: 10px;">
                        <h6 style="margin-bottom: 10px; color: #6c757d;">
                            Select exactly ${frm.doc.installments_count} months for repayment:
                        </h6>
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; max-height: 200px; overflow-y: auto;" id="month-grid">
                `;

                r.message.forEach(month => {
                    html += `
                        <label style="display: flex; align-items: center; padding: 5px; border: 1px solid #e9ecef; border-radius: 3px; cursor: pointer; font-size: 12px; background-color: white;">
                            <input type="checkbox" 
                                   value="${month.value}" 
                                   data-last-day="${month.last_day}" 
                                   data-label="${month.label}" 
                                   class="month-checkbox" 
                                   style="margin-right: 5px;">
                            ${month.label}
                        </label>
                    `;
                });

                html += `
                        </div>
                        <div id="selection-count" style="margin-top: 10px; font-size: 11px; color: #6c757d;">
                            Selected: 0 / ${frm.doc.installments_count}
                        </div>
                    </div>
                `;

                $('#month-selection-container').html(html);

                // Attach event handlers using jQuery event delegation
                $(document).off('change', '.month-checkbox');
                $(document).on('change', '.month-checkbox', function() {
                    handle_month_selection(frm);
                });

                // Pre-select existing months
                setTimeout(() => {
                    frm.doc.repayment_schedule.forEach(schedule => {
                        if (schedule.repayment_date) {
                            let month_str = schedule.repayment_date.substring(0, 7);
                            $(`.month-checkbox[value="${month_str}"]`).prop('checked', true);
                        }
                    });
                    update_selection_count(frm);
                }, 100);
            }
        }
    });
}

function handle_month_selection(frm) {
    if (!frm) {
        frm = window.current_loan_form || cur_frm;
    }
    
    if (!frm || !frm.doc) return;
    
    let checked_boxes = $('.month-checkbox:checked');
    let required_count = frm.doc.installments_count;
    
    // Limit selection to required count
    if (checked_boxes.length > required_count) {
        // Uncheck the last checked box
        checked_boxes.last().prop('checked', false);
        checked_boxes = $('.month-checkbox:checked');
        frappe.msgprint(__(`You can only select ${required_count} months`));
        return;
    }
    
    // Clear and rebuild repayment schedule
    frm.clear_table('repayment_schedule');
    
    let selected_months = [];
    checked_boxes.each(function() {
        let month_value = $(this).val();
        let last_day = $(this).data('last-day');
        let label = $(this).data('label');
        
        selected_months.push({
            month_value: month_value,
            last_day: last_day,
            label: label
        });
    });
    
    // Sort by date
    selected_months.sort((a, b) => new Date(a.last_day) - new Date(b.last_day));
    
    // Add to repayment schedule
    selected_months.forEach(month => {
        let child = frm.add_child('repayment_schedule');
        child.repayment_month_year = month.label;
        child.repayment_date = month.last_day;
        child.installment_amount = frm.doc.installment_amount || 0;
    });
    
    frm.refresh_field('repayment_schedule');
    update_selection_count(frm);
}

function update_selection_count(frm) {
    if (!frm) {
        frm = window.current_loan_form || cur_frm;
    }
    
    if (!frm || !frm.doc) return;
    
    let selected_count = $('.month-checkbox:checked').length;
    let required_count = frm.doc.installments_count;
    let count_display = `Selected: ${selected_count} / ${required_count}`;
    
    let count_element = $('#selection-count');
    if (count_element.length) {
        if (selected_count === required_count) {
            count_display += ` ✓`;
            count_element.css('color', '#28a745');
        } else {
            count_element.css('color', '#6c757d');
        }
        count_element.text(count_display);
    }
}

function calculate_installment_amount(frm) {
    if (frm.doc.loan_type === 'Loan' && frm.doc.loan_amount && frm.doc.installments_count) {
        let installment_amount = frm.doc.loan_amount / frm.doc.installments_count;
        frm.set_value('installment_amount', installment_amount);
        
        // Update existing schedule rows
        frm.doc.repayment_schedule.forEach(function(row) {
            frappe.model.set_value(row.doctype, row.name, 'installment_amount', installment_amount);
        });
        frm.refresh_field('repayment_schedule');
    }
}

function calculate_remaining_balance(frm) {
    if (frm.doc.total_amount) {
        let remaining = frm.doc.total_amount - (frm.doc.repaid_amount || 0);
        frm.set_value('remaining_balance', remaining);
    }
}