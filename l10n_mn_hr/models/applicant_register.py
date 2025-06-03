from odoo import models, fields, api

class ApplicantRegister(models.Model):
    _name = 'applicant.register'
    _description = 'Applicant Register'

    name = fields.Char(string='Applicant Name', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    code = fields.Char(string='Code')
    job_position_id = fields.Many2one('hr.job', string='Job Position', required=True)
    target_number = fields.Integer(string='Target Number', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    hr_employee_id = fields.Many2one('hr.employee', string='HR Employee', required=True)

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_draft(self):
        for record in self:
            record.state = 'draft'

    def submit_job_request(self):
        pass

    def approve_job_request(self):
        pass

    def create_non_full_time_positions(self):
        pass