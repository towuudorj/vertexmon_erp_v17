# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    desc = fields.Text(string=u'Гүйлгээний утга')
    
