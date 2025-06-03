# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _

class DismissedRegister(models.Model):
    _name = 'dismissed.employee'
    _description = 'Dismiss Register'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    dismissal_date = fields.Date(string='Dismissal Date', required=True)
    reason = fields.Text(string='Reason for Dismiss')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('dismissed', 'Dismissed'),
        ('rehired', 'Rehired'),
        ('blacklist', 'Blacklisted'),
        ('cancel', 'Cancelled'),
    ], string='State', default='draft', tracking=1)
    archived_info = fields.Text(string='Archived Information')
    name = fields.Char(string='Code', required=True)
    
    def action_draft(self):
        self.state = 'draft'


    def action_rehire(self):
        self.state = 'rehired'
        self.employee_id.active = True
    

    def action_blacklist(self):
        self.state = 'blacklist'


    def action_dismiss(self):
        self.state = 'dismissed'
        self.employee_id.active = False


    def action_cancel(self):
        self.state = 'cancel'


    @api.model
    def rehire_dismissed_employee(self, employee_id):
        dismissed_employee = self.search([
            ('employee_id', '=', employee_id),
            ('state', '!=', 'rehired')
        ], limit=1, order='id desc')
        
        if dismissed_employee:
            employee = self.env['hr.employee'].search([('id', '=', employee_id)], limit=1)
            employee.write({
                'name': dismissed_employee.employee_id.name,
                'work_email': dismissed_employee.employee_id.work_email,
                'work_phone': dismissed_employee.employee_id.work_phone,
                'state': 'rehired'
            })
            
            return employee
        return None

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            if self.employee_id:
                res['employee_id'] = self.employee_id.id
                res['company_id'] = self.employee_id.company_id.id
                res['department_id'] = self.employee_id.department_id.id
                res['position_id'] = self.employee_id.job_id.id
        else:
            res['employee_id'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['position_id'] = False
            
        return {'value':res}
