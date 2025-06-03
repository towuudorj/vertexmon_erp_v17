# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools


class ResCompany(models.Model):
    _inherit = "res.company"
    
    vat_code = fields.Char(string='Tin code')