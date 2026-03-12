# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    timely_id = fields.Integer('Timely ID')