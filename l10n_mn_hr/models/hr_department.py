# -*- coding: utf-8 -*-
from odoo import models, fields, models, api, SUPERUSER_ID, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    manager_id = fields.Many2one('hr.employee', 'Manager')
    parent_id = fields.Many2one('hr.department', 'Parent Department', ondelete='restrict')
    note = fields.Text('Note')
    code = fields.Char('Code')