# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time


class SalaryMonthRange(models.Model):
    _name = 'salary.month.range'
    _description = 'Salary Month Range'
    _inherit = ['mail.thread']
    _order = 'year DESC, month ASC'

    name = fields.Char(compute='_compute_name')
    year = fields.Integer('Year', tracking=True)
    month = fields.Integer('Month', tracking=True)
    date_from = fields.Date('From', tracking=True)
    date_to = fields.Date('To', tracking=True)


    def _compute_name(self):
        for obj in self:
            obj.name = str(obj.year) + '-' + str(obj.month)