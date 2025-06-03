# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import json, requests

class AccountJournal(models.Model):
    _inherit = "account.journal"

    xacbank_config_id = fields.Many2one('xacbank.configure', string="Xacbank configure")
    xacbank_cgw_connect = fields.Boolean(string='Xacbank CGW connect')
    is_income = fields.Boolean(string=u'Зөвхөн орлого татах', default=False)
