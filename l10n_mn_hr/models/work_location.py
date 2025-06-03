# -*- coding: utf-8 -*-
from odoo import models, fields, models, api, SUPERUSER_ID, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class HrDepartment(models.Model):
    _inherit = 'hr.work.location'

    code = fields.Char('Code', required=True)