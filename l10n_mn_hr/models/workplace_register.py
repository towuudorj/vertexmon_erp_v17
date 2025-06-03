from odoo import models, fields, api, _

class WorkplaceRegister(models.Model):
    _name = 'workplace.register'
    _description = 'Workplace Register'

    code = fields.Char(string='Code')
    name = fields.Char(string='Workplace Name', required=True)
    eng_name = fields.Char(string='English Name')
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', required=True)
    #work_category_id = fields.Many2one('work.category', string='Work Category', required=True)
    job_title = fields.Selection([
        ('general_director', 'General Director'),
        ('executive_director', 'Executive Director'),
        ('manager', 'Manager'),
        ('ordinary_employee', 'Ordinary Employee')
    ], string='Job Title', required=True)
    #position_id = fields.Many2one('hr.job', string='Position', required=True)
    employees_working = fields.Integer(string='Number of Employees Working', default=0)
    employees_left = fields.Integer(string='Number of Employees Left', default=0)
    struct_id = fields.Many2one(
    'hr.payroll.structure', 
    string='Structure', 
    required=True,)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id and self.struct_id and self.struct_id.company_id != self.company_id:
            self.struct_id = False
