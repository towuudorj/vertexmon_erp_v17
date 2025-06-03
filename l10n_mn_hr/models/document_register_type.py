from odoo import models, fields

class DocumentRegisterType(models.Model):
    _name = 'document.register.type'
    _description = 'Document Register Type'

    reg_user_id = fields.Many2one('res.users', string='Registered User', required=True, default=lambda self: self.env.user)
    code = fields.Char(string='Code')
    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    date = fields.Date(string='Date', default=fields.Date.today)