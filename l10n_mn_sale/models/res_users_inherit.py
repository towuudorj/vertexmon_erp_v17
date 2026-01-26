# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    signature_image = fields.Binary(string='Signature image')
    is_purchase_manager = fields.Boolean(string='Is purchase manager')
    sq_number = fields.Char(string='SQ number')
    name_image = fields.Binary(string='Name image')