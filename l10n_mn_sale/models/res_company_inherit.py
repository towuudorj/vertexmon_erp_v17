# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    company_stamp = fields.Binary(string='Company stamp')
    account_stamp = fields.Binary(string='Account stamp')
    report_image = fields.Binary(string='Report image')