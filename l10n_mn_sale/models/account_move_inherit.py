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
                                    required=True,
                                    default='down_payment',
                                    string='Payment type')


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
    
    