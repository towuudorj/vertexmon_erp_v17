# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    contract_id = fields.Many2one('sales.contract.register', string='Contract')
    payment_type = fields.Selection([('down_payment', 'Down payment'),
                                     ('progress_payment', 'Progress payment'),
                                     ('final_payment', 'Final payment'),
                                     ('barter', 'Barter transaction'),
                                     ('guarantee_collateral', 'Guarantee and collateral'),
                                     ('penalty', 'Penalty')],
                                    required=False,
                                    default=False,
                                    string='Payment type')
    payment_percent = fields.Float(string='Payment percent')
    line_names = fields.Text(string='Line names', compute='_compute_line_names')
    payment_date = fields.Date(string='Payment date')
    ot_po = fields.Char(string='OT/PO', compute='_compute_ot_po')

    @api.depends('invoice_line_ids')
    def _compute_line_names(self):
        for obj in self:
            if obj.invoice_line_ids and obj.payment_type:
                obj.line_names = ',\n'.join([l.name for l in obj.invoice_line_ids])
            else:
                obj.line_names = ''

    @api.onchange('line_ids')
    def _compute_ot_po(self):
        for obj in self:
            if obj.sale_order_count == 1:
                obj.ot_po = obj.line_ids.sale_line_ids.order_id.ot_po
            else:
                obj.ot_po = ''

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    month = fields.Selection([('01','1'),
                                ('02','2'),
                                ('03','3'),
                                ('04','4'),
                                ('05','5'),
                                ('06','6'),
                                ('07','7'),
                                ('08','8'),
                                ('09','9'),
                                ('10','10'),
                                ('11','11'),
                                ('12','12')],string=u'Сар')
    
    