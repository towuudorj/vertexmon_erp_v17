# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class JobAppointmentRegister(models.Model):
    _name = 'job.appointment.register'
    _description = 'Vacancy Request Register'
    _inherit = ['mail.thread']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_department_manager_review', 'Department Manager Review'),
        ('operations_manager_review', 'Operations Manager Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='State', default='draft')
    reg_user_id = fields.Many2one('res.users', string='Registered User', required=True)
    number = fields.Char(string='Request Number', required=True, copy=False, readonly=True, index=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id) 
    name = fields.Char(string='Request Name', required=True)
    reg_date = fields.Date(string='Registration Date', required=True, default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    description = fields.Text(string='Description')
    vacancy = fields.Integer(string='Vacancy')
    

    @api.model
    def create(self, vals):
        if vals.get('number', _('New')) == _('New'):
            vals['number'] = self.env['ir.sequence'].next_by_code('job.appointment.register') or _('New')
        return super(JobAppointmentRegister, self).create(vals)


    def hr_department_manager_review(self):
        self.write({'state': 'hr_department_manager_review'})

    def operations_manager_review(self):
        self.write({'state': 'operations_manager_review'})

    def approve_request(self):
        self.write({'state': 'approved'})

    def reject_request(self):
        self.write({'state': 'rejected'})

    def action_approve(self):
        self.state = 'hr_department_manager_review'

    def action_hr(self):
        self.state = 'operations_manager_review'

    def action_director(self):
        self.state = 'approved'

    def action_reject(self):
        self.state = 'rejected'
        
    def action_return(self):
        self.state = 'returned'

    def action_draft(self):
        self.state = 'draft'

    def action_return(self):
        for line in self:
            if line.state == 'hr_department_manager_review':
                line.state = 'draft'
            elif line.state == 'operations_manager_review':
                line.state = 'hr_department_manager_review'
            elif line.state == 'approved':
                line.state = 'operations_manager_review'

    @api.depends('department_id')
    def _compute_vacancy(self):
        for record in self:
            if record.department_id:
                recruitments = self.env['hr.applicant'].search_count([
                    ('department_id', '=', record.department_id.id),
                    ('state', '=', 'recruit')
                ])
                record.vacancy = recruitments
            else:
                record.vacancy = 0