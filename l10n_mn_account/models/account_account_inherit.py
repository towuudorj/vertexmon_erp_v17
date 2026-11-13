# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero
from odoo.tools.sql import SQL
from bisect import bisect_left
from collections import defaultdict
import re

ACCOUNT_CODE_REGEXN = re.compile(r'^[A-Za-z0-9-]+$')

class AccountAccount(models.Model):
    _inherit = "account.account"

    cash_move_type_id = fields.Many2one('account.cash.move.type', string='Cash Move Type')
    partner_not_required = fields.Boolean(
        string='Харилцагч заавал биш', default=False, tracking=True,
        help='Сонговол авлага/өглөгийн төрөлтэй энэ данс бүхий журналын мөрийг '
             'харилцагчгүйгээр батлахыг зөвшөөрнө.')

    @api.constrains('code')
    def _check_account_code(self):
        for account in self:
            if not re.match(ACCOUNT_CODE_REGEXN, account.code):
                raise ValidationError(_(
                    "The account code can only contain alphanumeric characters and dots."
                ))