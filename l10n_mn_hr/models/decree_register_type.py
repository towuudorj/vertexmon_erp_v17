from odoo import models, fields

class DecreeRegisterType(models.Model):
    _name = 'decree.register.type'
    _description = 'Decree Register'

    reg_user_id = fields.Many2one(
        'res.users', 
        string='Registered User', 
        required=True, 
        default=lambda self: self.env.user)
    code = fields.Char(string='Code')
    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True, 
        default=lambda self: self.env.user.company_id)
    active = fields.Boolean(string='Active', default=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    description = fields.Text(string='Description')
    hr_employee_id = fields.Many2one('hr.employee', 'Employee')