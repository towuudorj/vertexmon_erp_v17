# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    timely_id = fields.Integer('Timely ID')

class EmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    timely_id = fields.Integer('Timely ID', related='employee_id.timely_id', compute_sudo=True)