# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _
from datetime import date, datetime, time, timedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
               
class ResourceCalendar(models.Model): 
    _inherit = 'resource.calendar'
    
    # is_holiday_time_out = fields.Boolean(string='Holiday time out')
    work_time = fields.Float(string='Working hour')
    lunchtime_start = fields.Float(string='Lunch time start')
    lunchtime_end = fields.Float(string='Lunch time end', compute='_compute_lunchtime_end')

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to', 'two_weeks_calendar')
    def _compute_hours_per_day(self):
        super(ResourceCalendar, self)._compute_hours_per_day()
        for obj in self:
            if obj.work_time:
                obj.hours_per_day = obj.work_time

    @api.onchange('lunchtime_start')
    def _compute_lunchtime_end(self):
        for obj in self:
            if obj.lunchtime_start:
                obj.lunchtime_end = obj.lunchtime_start + 1
            else:
                obj.lunchtime_end = None


class hr_contract(models.Model):
    _inherit = 'hr.contract'
    
    phone_add = fields.Float(string='Phone add')
    administration_add = fields.Float(string='Administration add')
    food_and_vehicle_add = fields.Float(string='Food and vehicle add')
    long_year_add = fields.Float(string='Long year add')
    health_insurance = fields.Float(string='Health insurance')
    accident_insurance = fields.Float(string='Accident insurance')
    voucher = fields.Float(string='Voucher')
    abnormal_add = fields.Float(string='Abnormal add')
    trial_end_date = fields.Float(string='Trial End Date') 

    
class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    dep_id = fields.Many2one('hr.department', string='Department')
    


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    dep_id = fields.Many2one('hr.department', string='Department')  
    
    def refund_sheet(self):
        for payslip in self:
            if  payslip.credit_note == True:
                raise UserError(_(u'Буцаалт хийгдсэн тул дахин буцаалт хийхгүй.'))
            copied_payslip = payslip.copy({'credit_note': True, 'name': _('Refund: ') + payslip.name})
            copied_payslip.compute_sheet()
            copied_payslip.action_payslip_done()
            payslip.write({'is_return':True})
        formview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_form', False)
        treeview_ref = self.env.ref('hr_payroll_community.view_hr_payslip_tree', False)
        
        return {
            'name': ("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % copied_payslip.ids,
            'views': [(treeview_ref and treeview_ref.id or False, 'tree'), (formview_ref and formview_ref.id or False, 'form')],
            'context': {}
        }

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """
        res = super(HrPayslip, self).get_worked_day_lines(contracts, date_from, date_to)
        res = [line for line in res if line.get('code') != 'WORK100']

        if self.employee_id:
            start_date = self.date_from
            end_date = self.date_to
            hr_hour_record = self.env['hr.hour.record'].new({
                'start_date': datetime.combine(start_date, time(0, 1)) - timedelta(hours=8),
                'end_date': datetime.combine(end_date, time(23, 59)) - timedelta(hours=8),
                'company_id': self.employee_id.company_id.id
            })
            line_vals = hr_hour_record.hour_record(employee_id=self.employee_id)
            must_work = {
                'name': _("Must work"),
                'sequence': 1,
                'code': 'MUST_WORK',
                'number_of_days': line_vals['due_day'],
                'number_of_hours': round(line_vals['due_time'], 2),
                'contract_id': contracts.id
            }
            worked = {
                'name': _("Worked"),
                'sequence': 1,
                'code': 'WORK100',
                'number_of_days': line_vals['work_day'],
                'number_of_hours': round(line_vals['work_time'] + line_vals['free_time1'], 2),
                'contract_id': contracts.id
            }

            res.append(must_work)
            res.append(worked)
        return res