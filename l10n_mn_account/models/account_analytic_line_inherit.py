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

class AccounAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

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
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency")