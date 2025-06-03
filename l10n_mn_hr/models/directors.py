from odoo import models, fields

class Directors(models.Model):
    _name = 'directors'
    _description = 'Directors'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name', required=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    executive_director = fields.Many2one('hr.employee', string='Executive Director', required=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    active = fields.Boolean(string='Active', default=True)
    parent_id = fields.Many2one('directors', string='Parent Director')
    child_ids = fields.One2many('directors', 'parent_id', string='Child Directors')