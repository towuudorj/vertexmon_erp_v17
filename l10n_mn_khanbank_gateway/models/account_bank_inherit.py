# -*- coding: utf-8 -*-
import time
import math

from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import float_compare, float_is_zero
from dateutil.relativedelta import relativedelta
import calendar

class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'
    
    
    

    
    
    