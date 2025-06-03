# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import json, requests

class AccountMove(models.Model):
    _inherit = "account.move"

    landed_costs = fields.Boolean(compute='_compute_landed_cost', string='Landed Costs', store=True)


    @api.depends('line_ids', 'line_ids.is_landed_costs_line')
    def _compute_landed_cost(self):
        for account_move in self:
            if account_move.landed_costs_ids:
                account_move.landed_costs = True
            else:
                account_move.landed_costs = False