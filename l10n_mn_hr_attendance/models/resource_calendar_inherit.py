# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
    
class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    total_work_time = fields.Float(string='Total work time')