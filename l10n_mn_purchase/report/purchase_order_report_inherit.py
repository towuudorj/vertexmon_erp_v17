# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
    
class PurchaseReport(models.Model):
    _inherit = 'purchase.report'

    order_currency_id = fields.Many2one('res.currency', 'Order Currency', readonly=True)
    order_currency_rate = fields.Float('Currency Rate', readonly=True)
    partner_type_id = fields.Many2one('partner.type.register', string='Partner type', readonly=True)


    def _select(self):
        return super(PurchaseReport, self)._select() + ", po.currency_id as order_currency_id, po.currency_rate as order_currency_rate, po.partner_type as partner_type_id"


    def _group_by(self):
        return super(PurchaseReport, self)._group_by() + ", po.currency_id, po.currency_rate, po.partner_type"

    