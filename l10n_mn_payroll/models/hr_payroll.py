# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError
from odoo import api, fields, models, tools, _
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
               
class ResourceCalendar(models.Model): 
    _inherit = 'resource.calendar'
    
    is_holiday_time_out = fields.Boolean(string='Holiday time out')
    work_time = fields.Float(string='Working hour')
    

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
    


class hr_payslip(models.Model):
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
        


    