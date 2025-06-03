# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, tools, _
from datetime import date, datetime, time


class routing_slip(models.Model):
    _name = 'routing.slip'
    _description = 'Routing slip'
    _order = 'id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='№', readonly=True, 
                        default=lambda self: self.env['ir.sequence'].next_by_code('routing.slip'))
    employee_id = fields.Many2one('hr.employee', 'Employee', copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    job_id = fields.Many2one('hr.job', 'Job')
    accession_date = fields.Date('Accession date')
    left_date = fields.Date('Left date')
    last_name = fields.Char('Last name')
    out_reason_id = fields.Many2one('out.reason', 'Out reason')
    routing_date = fields.Date('Routing date', default = datetime.today())
    slip_line_id = fields.One2many('routing.slip.line', 'routing_slip_id', 'Line')
    state = fields.Selection([('draft', 'Draft'),  # Ноорог
                                    ('send_routing', 'Send routing slip'),  # Тойрох хуудас илгээсэн
                                    ('routing_ended', 'Routing ended'),  # Тойрох зуруулж дууссан
                                    ('left_job', 'Left job'),  # Ажлаас гарсан
                                    ('cancel', 'Cancelled'),  # Цуцлах
                                    ], 'State', default = 'draft', tracking=1)  # Эхлэх төлөв
    survey_id = fields.Many2one('survey.survey', string='Survey')
    work_handover_act_id = fields.Many2one('work.handover.act', 'Work handover act')
    workhandover_count = fields.Integer(string='Work handover act', compute='_compute_workhandover_count')



    _sql_constraints = [
        ('employee_id', 'unique(employee_id,out_reason_id)', 'Field employee_id and out_reason_id must be unique.'),
        ]

        
    def action_draft(self):
        self.state = 'draft'

    def action_send(self):
        self.state = 'send_routing'
    
    def action_cancel(self):
        self.state = 'cancel'

    def _compute_workhandover_count(self):
        for rec in self:
            rec.workhandover_count = self.env['work.handover.act'].search_count([('routing_slip_id', '=', rec.id)])

    def action_to_workhandover_create(self):
        handact_obj = self.env['work.handover.act']
        for line in self:
            hand_id = handact_obj.create({
                                'employee_id': line.employee_id.id,
                                'company_id': line.company_id.id,
                                'routing_slip_id': line.id
                                })
            line.work_handover_act_id = hand_id.id


    def action_to_workhandover_list(self, handact=False):
        if not handact:
            handact = self.mapped('work_handover_act_id')
        action = self.env['ir.actions.actions']._for_xml_id('l10n_mn_hr.action_work_handover_act')
        if len(handact) > 1:
            action['domain'] = [('id', 'in', handact.ids)]

        elif len(handact) == 1:
            form_view = [(self.env.ref('l10n_mn_hr.work_handover_act_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = handact.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
        }
        if len(self) == 1:
            context.update({
                'default_employee_id': self.employee_id.id,
            })
        action['context'] = context
        return action



    def confirm_quit(self):
        self.ensure_one()
        if self.employee_id:
            employee = self.employee_id
            for contract in employee.contract_ids:
                contract.write({'state': 'cancelled'})
                contract.active = False
            employee.active = False
            if employee.user_id:
                employee.user_id.active = False
        self.state = 'left_job'
        return True
    

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            if self.employee_id:
                res['employee_id'] = self.employee_id.id
                res['last_name'] = self.employee_id.last_name
                res['company_id'] = self.employee_id.company_id.id
                res['department_id'] = self.employee_id.department_id.id
                res['job_id'] = self.employee_id.job_id.id
                res['accession_date'] = self.employee_id.accession_date
        else:
            res['employee_id'] = False
            res['last_name'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['job_id'] = False
            res['accession_date'] = False
            
        return {'value':res}


    def refresh_page(self):
        return { 'type': 'ir.actions.client', 'tag': 'reload'}
    
    
    def unlink(self):
        line_obj = self.env['routing.slip.line']
        for line in self.slip_line_id:
            line.unlink()
        return super(routing_slip, self).unlink()


class routing_slip_line(models.Model):
    _name = 'routing.slip.line'
    _description = 'Routing slip line'
    
    routing_slip_id = fields.Many2one('routing.slip', 'Routing slip')
    code = fields.Integer('Code')
    company_id = fields.Many2one('res.company', 'Company')
    job_id = fields.Many2one('hr.job', 'Job')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    date = fields.Date('Date')
    category_ids = fields.Many2many(
        'routing.category', 'routing_category_rel',
        'rout_id', 'category_id', groups="hr.group_hr_manager",
        string='Tags')
    note = fields.Char('Note')
    signature = fields.Char('Signature')

    @api.onchange('job_id')
    def onchange_job_id(self):
        obj = self.browse()
        res = {}
        if self.job_id:
            job_obj = self.env['hr.job']
            job_id = job_obj.search([('id', '=', self.job_id.id)])
            if job_id:
                res['company_id'] = job_id.company_id.id
                res['code'] = job_id.job_code
                # print 'nnnnnnnnnn', job_id
                employee_obj = self.env['hr.employee']
                emp_id = employee_obj.search([('job_id', '=', job_id.id)])
                emp = employee_obj.browse(emp_id)
                if len(emp_id) == 1:
                    res['employee_id'] = emp.id
                    
                # emp = employee_obj.browse(cr, uid, emp_id)
            
        return {'value':res}


class routing_master(models.Model):
    _name = 'routing.master'
    _description = 'Routing master'

    job_id = fields.Many2one('hr.job', 'Job', copy=False)
    master_line_id = fields.One2many('routing.master.line', 'routing_master_id', 'Line', copy=False)

    _sql_constraints = [
        ('job_id', 'unique("job_id")', 'Field job_id must be unique.'),
        ]
    
    def unlink(self, vals):
        obj = self.browse()[0]
        line_obj = self.env['routing.master.line']
        for line in obj.master_line_id:
            line_obj.unlink(line.id)
        return super(routing_master, self).unlink(vals)


class routing_master_line(models.Model):
    _name = 'routing.master.line'
    _description = 'Routing master line'

    routing_master_id = fields.Many2one('routing.master', 'Routing master')
    code = fields.Integer('Code')
    company_id = fields.Many2one('res.company', 'Company')
    job_id = fields.Many2one('hr.job', 'Job', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee')
    date = fields.Date('Date')
    category_ids = fields.Many2many(
        'routing.category', 'master_category_rel',
        'master_id', 'category_id', groups="hr.group_hr_manager",
        string='Tags')
    note = fields.Char('Note')
    signature = fields.Char('Signature')

    def create(self, vals):
        res = {}
        
        master_id = super(routing_master_line, self).create(vals)
        return master_id
    
    @api.onchange('job_id')
    def onchange_job_id(self):
        obj = self.browse()
        res = {}
        if self.job_id:
            job_obj = self.env['hr.job']
            job_id = job_obj.search([('id', '=', self.job_id.id)])
            if job_id:
                res['company_id'] = job_id.company_id.id
                res['code'] = job_id.job_code
                # print 'nnnnnnnnnn', job_id
                employee_obj = self.env['hr.employee']
                emp_id = employee_obj.search([('job_id', '=', job_id.id)])
                emp = employee_obj.browse(emp_id)
                if len(emp_id) == 1:
                    res['employee_id'] = emp.id
            
        return {'value':res}
   

    
class Job(models.Model):
    _inherit = 'hr.job'
    
    job_code = fields.Char('Job code')

    
class out_reason(models.Model):
    _name = 'out.reason'
    _description = 'Left reason'
    
    name = fields.Char('Left reason')
    left_type = fields.Selection([('company_decision', 'Company decision'), ('own_decision', 'Own decision')], 'Left type')
    left_reason_code = fields.Integer('Left reason code')
    hr_employee_id = fields.Many2one('hr.employee', 'Hr employee')


class routing_category(models.Model):
    _name = "routing.category"
    _description = "Routing Category"

    name = fields.Char(string="Tag Name", required=True)
    color = fields.Integer(string='Color Index')
    routing_ids = fields.Many2many('routing.slip.line', 'routing_category_rel', 'category_id', 'rout_id', string='Routing category')
    master_ids = fields.Many2many('routing.master.line', 'master_category_rel', 'category_id', 'master_id', string='Master category')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
