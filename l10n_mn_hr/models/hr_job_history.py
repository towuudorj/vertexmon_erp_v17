from odoo import models, fields, api, _

class HrJobHistory(models.Model):
    _name = 'hr.job.history'
    _description = 'Job History'

    job_id = fields.Many2one('hr.job', string='Job Position', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    reason_left = fields.Selection([
        ('sick', 'Sick'),
        ('resigned', 'Resigned'),
        ('terminated', 'Terminated'),
        ('retired', 'Retired'),
        ('other', 'Other'),
    ], string='Reason Left')
    turnover = fields.Float(string='Turnover', compute='_compute_turnover')

    @api.depends('start_date', 'end_date')
    def _compute_turnover(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.turnover = delta.days / 365.0
            else:
                record.turnover = 0.0

    

    class HrJob(models.Model):
        _inherit = 'hr.job'

        job_history_ids = fields.One2many('hr.job.history', 'job_id', string='Job History')
        total_employees =fields.Integer(string='Total Employees', compute='_compute_total_employees')
        reasons_left = fields.Text(string='Reasons Left', compute='_compute_reasons_left')
        average_turnover = fields.Float(string='Average Turnover', compute='_compute_average_turnover')

        @api.depends('job_history_ids')
        def _compute_total_employees(self):
            for job in self:
                job.total_employees = len(job.job_history_ids)

        @api.depends('job_history_ids')
        def _compute_reasons_left(self):
            for job in self:
                reasons = job.job_history_ids.mapped('reason_left')
                job.reasons_left = ', '.join([_(reason) for reason in reasons if reason])
                

        @api.depends('job_history_ids')
        def _compute_average_turnover(self):
            for job in self:
                total_turnover = sum(job.job_history_ids.mapped('turnover'))
                job.average_turnover = total_turnover / len(job.job_history_ids) if job.job_history_ids else 0.0
        
