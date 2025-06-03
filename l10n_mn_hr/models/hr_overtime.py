from odoo import models, fields, api, _

class HrOvertime(models.Model):
    _name = 'hr.overtime'
    _description = 'Overtime'
    _inherit = ['mail.thread']
    
    def _employee_get(self):        
        emp_id = context.get('default_employee_id', False)
        if emp_id:
            return emp_id
        ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if ids:
            return ids[0]
        return False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id
        else:
            self.job_id = False
            self.department_id = False

    """
    def requested(self):
        self.ensure_one()
        if self.state == 'requested':
            self.state = 'allowed'
            self.message_post(body=_('Overtime requested.'))
            self.employee_id.message_post(body=_('Overtime requested.'))
        else:
            self.state = 'requested'
            self.message_post(body=_('Overtime request sent.'))
            self.employee_id.message_post(body=_('Overtime request sent.'))
    """
    
    def allowed(self):
        self.ensure_one()
        if self.state == 'requested':
            self.state = 'allowed'
            self.message_post(body=_('Overtime request allowed.'))
        else:
            self.state = 'requested'
            self.message_post(body=_('Overtime request sent.'))

    def approved(self):
        self.ensure_one()
        if self.state == 'allowed':
            self.state = 'approved'


    def cancelled(self):
        self.ensure_one()
        if self.state == 'approved' or self.state == 'allowed':
            self.state = 'cancelled'
        else:
            self.state = 'cancelled'
            self.message_post(body=_('Overtime request cancelled.'))
            

    name = fields.Text('Илүү цагаар ажиллах шалтгаан', required=True)
    employee_id = fields.Many2one('hr.employee', 'Ажилтан', track_visibility='onchange', default = lambda self: self.env.user.employee_ids.id)
    company_id = fields.Many2one('res.company', 'Компани')
    department_id = fields.Many2one('hr.department', 'Алба')
    job_id = fields.Many2one('hr.job', 'Албан тушаал')
    date_start = fields.Datetime('Бүртгэсэн огноо', copy=False)
    #date_end = fields.Datetime('Дуусах огноо', copy=False,)
    hours = fields.Float('Илүү ажилласан цаг', copy=False)
    headsman_id = fields.Many2one('hr.employee', 'Баталсан ажилтан', copy=False)
    manager_id = fields.Many2one('hr.employee', 'Зөвшөөрсөн ажилтан', copy=False)
    
    #in_time = fields.Float('Ирсэн цаг')
    #out_time = fields.Float('Явсан цаг')
    
    state = fields.Selection([('requested', 'Хүсэлт илгээсэн'),
                              ('allowed', 'Зөвшөөрсөн'),
                              ('approved', 'Батлагдсан'),
                              ('cancelled', 'Цуцлагдсан')
                              ], 'Төлөв', track_visibility='onchange', default='requested')
    #is_no_limit = fields.Boolean('Ажлын цагийн хязгаар үйлчлэхгүй')

