# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class AssetLocation(models.Model):
    _name = 'asset.location'
    _description = 'Asset location'

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    name = fields.Char(string='Asset location', required=True)
