# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class WorkCategory(models.Model):
    _name = 'work.category'
    _description = 'Work category'

    company_id = fields.Many2one('res.company',string='Company',
                                 default=lambda self: self.env.user.company_id)
    name = fields.Char(string='Work category')
    code = fields.Char(string='Code')
    parent_id = fields.Many2one('work.category',string='Parent category')