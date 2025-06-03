# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ReferenceRegister(models.Model):
    _name = 'reference.register'
    _description = 'Reference Register'
    _inherit = ['mail.thread']

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Reference', required=True)
    reference_number = fields.Char(string='Reference Number', required=True)
    date = fields.Date(string='Date', required=True)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled')
        ], string='State', default='draft', tracking=1)
    reg_user_id = fields.Many2one('res.users', string='Registered User', required=True,
                            default=lambda self: self.env.user)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string='Department')
    reg_date = fields.Date(string='Registration Date', required=True, default=fields.Date.today)
    where_to = fields.Char(string='Where to', required=True)
    reference_type_id = fields.Many2one('reference.register.type', string='Reference Type')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id

    def action_confirm(self):
        self.state = 'confirmed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'

    