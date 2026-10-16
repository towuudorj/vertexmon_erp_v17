# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
        domain="[('department_id', '=', dep_id)] if dep_id else []"
    )
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Created employees',
        default=lambda self: self.env.context.get('active_id')
        if self.env.context.get('active_model') == 'hr.payslip.run' else False
    )
    created_emp_ids = fields.Many2many(
        'hr.employee',
        string='Payslip Batch',
        compute='_compute_created_emp_ids',
    )
    dep_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='payslip_run_id.dep_id',
        readonly=True
    )

    def compute_sheet(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note'])
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'month': self.payslip_run_id.month,
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'company_id': employee.company_id.id,
            }
            payslips += self.env['hr.payslip'].create(res)
        payslips.compute_sheet()
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('payslip_run_id')
    def _compute_created_emp_ids(self):
        for obj in self:
            if self.env.context.get('active_model') == 'hr.payslip.run':
                slip_run = self.env['hr.payslip.run'].browse(self.env.context.get('active_id'))
                obj.created_emp_ids = slip_run.slip_ids.mapped('employee_id')
            else:
                obj.created_emp_ids = False