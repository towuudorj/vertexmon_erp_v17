# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
    
class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    loss_time = fields.Float(string='Loss time', compute='_compute_loss_time')
    
    def create_check_in(self, employee_id, lat, long):
        """
        Create a check-in record with the given latitude and longitude.
        """
        self.create({
            'check_in': fields.Datetime.now(),
            'employee_id': employee_id,
            'in_mode':'manual',
        })
    def create_check_out(self, lat, long):
        """
        Create a check-out record with the given latitude and longitude.
        """
        self.write({
            'check_out': fields.Datetime.now(),
        })


    def _compute_loss_time(self):
        for rec in self:
            total_time = 0.0
            rec.loss_time = total_time
