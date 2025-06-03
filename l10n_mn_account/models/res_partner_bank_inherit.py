# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class ResPartnerBank(models.Model):
     _inherit = 'res.partner.bank'

     iban = fields.Char(string='IBAN')
     swift = fields.Char(string='SWIFT')