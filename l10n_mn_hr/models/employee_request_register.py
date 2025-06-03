# -*- coding: utf-8 -*-
from odoo import api, fields, models

class EmployeeRequestRegister(models.Model):
    _name = 'employee.request.register'
    _description = 'Employee Request Register'
    _inherit = ['mail.thread']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_review', 'HR Review'),
        ('director_review', 'Director Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='State', default='draft', tracking=1)

    number = fields.Char(string='Request Number', required=True, copy=False, readonly=True, index=True, default='New')
    name = fields.Char(string='Request Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    reg_date = fields.Date(string='Registration Date', required=True, default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    job_id = fields.Many2one('hr.job', string='Position')
    request_type = fields.Selection([
        ('salary_specification', 'Salary Specification'),
        ('employment_statement', 'Statement of Employment'),
        ('loan_request', 'Loan Request'),
        ('product_credit_request', 'Product Credit Request'),
        ('other', 'Other')
    ], string='Request Type', required=True)
    description = fields.Text(string='Description')
    suggestion = fields.Text(string='Suggestion')

    @api.model
    def create(self, vals):
        if vals.get('number', 'New') == 'New':
            vals['number'] = self.env['ir.sequence'].next_by_code('employee.request.register') or 'New'
        return super(EmployeeRequestRegister, self).create(vals)

    #def submit_request(self):
    #    self.write({'state': 'hr_review'})

    def hr_review(self):
        self.write({'state': 'director_review'})

    def director_review(self):
        self.write({'state': 'director_approve'})

    def approve_request(self):
        self.write({'state': 'approved'})

    def reject_request(self):
        self.write({'state': 'rejected'})

    def action_approve(self):
        self.write({'state':'hr_review'})

    def action_hr(self):
        self.state = 'director_review'

    def action_director(self):
        self.state = 'approved'

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_draft(self):
        self.write({'state': 'draft'})


    def action_return(self):
        for line in self:
            if line.state == 'hr_review':
                line.write({'state': 'draft'})
            elif line.state == 'director_review':
                line.write({'state': 'hr_review'})
            elif line.state == 'approved':
                line.write({'state': 'director_review'})

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            employee_obj = self.env['hr.employee']
            emp_id = employee_obj.search([('id', '=', self.employee_id.id)])
            if emp_id:
                res['employee_id'] = emp_id.id
                res['company_id'] = emp_id.company_id.id
                res['department_id'] = emp_id.department_id.id
                res['job_id'] = emp_id.job_id.id
        else:
            res['employee_id'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['job_id'] = False
            
        return {'value':res}
