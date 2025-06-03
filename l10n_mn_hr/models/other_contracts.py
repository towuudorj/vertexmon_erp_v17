# -*- coding: utf-8 -*-
from odoo import models, fields, api

class OtherContracts(models.Model):
    _name = 'other.contracts'
    _description = 'Other Contracts'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id) 
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    job_id = fields.Many2one('hr.job', string='Job', required=True)                            
    name = fields.Char(string='Contract name', required=True)
    employee_id = fields.Many2one('hr.employee', string='Contract employee', required=True)
    contract_type_id = fields.Many2one('contract.type.register', string='Contract type', required=True)
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date(string='End Date', required=True)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled')
        ], string='State', default='draft', tracking=1)
    reg_user_id = fields.Many2one('res.users', string='Registered User', required=True,
                                  default=lambda self: self.env.user)
    contract_number = fields.Char(string='Contract Number', readonly=True, default='/')
    reg_date = fields.Date(string='Registration Date', required=True, default=fields.Date.today)
    note = fields.Text('Тэмдэглэл/Тайлбар')


    def action_confirm(self):
        self.state = 'confirmed'
        self.contract_number = self.env['ir.sequence'].next_by_code('other.contracts')

    def action_cancel(self):
        self.state = 'cancelled'
        self.contract_number = self.env['ir.sequence'].next_by_code('other.contracts')

    def send_email(self):
        self.write({'state': 'email_sent'})

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            employee_obj = self.env['hr.employee']
            emp_id = employee_obj.search([('id', '=', self.employee_id.id)])
            if emp_id:
                res['employee_id'] = emp_id.id
                res['company_id'] = emp_id.company_id.id
                res['department_id'] = emp_id.department_id.id
                res['job_id'] = emp_id.job_id.id
        else:
            res['employee_id'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['job_id'] = False
            
        return {'value':res}