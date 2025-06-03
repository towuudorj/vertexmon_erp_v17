# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo import tools, _
from odoo.exceptions import ValidationError, AccessError, UserError
from odoo import api, fields, models, SUPERUSER_ID, tools
from datetime import date, datetime, time


class WorkHandoverAct(models.Model):
    _name = 'work.handover.act'
    _description = 'Work handover act'
    _inherit = ['mail.thread']


    name = fields.Char(string='№', readonly=True, 
                        default = lambda self: self.env['ir.sequence'].next_by_code('work.handover.act'))
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    employee_id = fields.Many2one('hr.employee', 'Employee', copy=False)
    job_id = fields.Many2one('hr.job', 'Job')
    accession_date = fields.Date('Accession date')
    left_date = fields.Date('Left date')
    last_name = fields.Char('Last name')
    handover_date = fields.Date('Handover date', default = datetime.today())
    slip_line_id = fields.One2many('handover.act.line', 'work_handover_id', 'Line')
    state = fields.Selection([('work_handover_act_draft', 'Work handover act draft'),  # Ажил хүлээлцэх акт
                                    ('handover_act_ended', 'Work handover act ended'),  # Ажил хүлээлцэх акт дууссан
                                    ('left_job', 'Left job'),  # Ажлаас гарсан
                                    ('cancel', 'Cancelled'),  # Цуцалсан
                                    ], 'State', default = 'work_handover_act_draft', tracking=1)  # Төлөв
    routing_slip_id = fields.Many2one('routing.slip', string='Routing Slip')
    routing_slip_count= fields.Integer(string='Routing slip', compute='_compute_routing_slip_count')
    
    #survey_id = fields.Many2one('survey.survey', string='Survey')

    _sql_constraints = [
        ('employee_id', 'unique(employee_id,out_reason_id)', 'Field employee_id and out_reason_id must be unique.'),
        ]
    
    
    def confirm_quit(self):
        self.ensure_one()
        if self.employee_id:
            employee = self.employee_id
            for contract in employee.contract_ids:
                contract.write({'state': 'cancel'})
                contract.active = False
            employee.active = False
            if employee.user_id:
                employee.user_id.active = False
        self.state = 'left_job'
        return True
    
    def action_draft(self):
        self.state = 'work_handover_act_draft'

    def to_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_confirm(self):
        self.state = 'handover_act_ended'
        
    def action_cancel(self):
        self.state = 'cancel'
    
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            employee_obj = self.env['hr.employee']
            emp_id = employee_obj.search([('id', '=', self.employee_id.id)])
            if emp_id:
                res['last_name'] = emp_id.last_name
                res['company_id'] = emp_id.company_id.id
                res['job_id'] = emp_id.job_id.id
                res['accession_date'] = emp_id.accession_date
            if emp_id.job_id:
                rm_obj = self.env['handover.act.master']
                rm_id = rm_obj.search([('job_id', '=', emp_id.job_id.id)])
                rsl_obj = self.env['handover.act.line']
                if rm_id:
                    for line in rm_id.master_line_id:
                        line_values = {
                            'code': line.code,
                            'company_id': line.company_id.id,
                            'job_id': line.job_id.id,
                            'employee_id': line.employee_id.id,
                            'date': line.date,
                            'note': line.note,
                            'signature': line.signature,
                            'handover_category_ids': line.handover_category_ids,
                            }
                        list.append((0,0,line_values))
                        res['slip_line_id'] = list
                else:
                    res['slip_line_id'] = False
        else:
            res['last_name'] = False
            res['company_id'] = False
            res['job_id'] = False
            res['accession_date'] = False
            res['slip_line_id'] = False
        # self.update({'slip_line_id': list })
        return {'value':res}
        

    def refresh_page(self):
        return { 'type': 'ir.actions.client', 'tag': 'reload'}
    
    
    def unlink(self):
        if self.state=='work_handover_act_draft':
            for line in self.slip_line_id:
                line.unlink()
            return super(WorkHandoverAct, self).unlink()
        else:
            raise UserError((u"Батлагдсан байгаа тул устахгүйг анхаарна уу!"))
    
    
    def _compute_routing_slip_count(self):
        for rec in self:
            rec.routing_slip_count = self.env['routing.slip'].search_count([('work_handover_act_id', '=', rec.id)
            ])

    def action_to_routing(self, routing=False):
        if not routing:
            routing = self.mapped('routing_slip_id')
        action = self.env['ir.actions.actions']._for_xml_id('l10n_mn_hr.action_routing_slip')
        if len(routing) > 1:
            action['domain'] = [('id', 'in', routing.ids)]

        elif len(routing) == 1:
            form_view = [(self.env.ref('l10n_mn_hr.routing_slip_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = routing.id
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
    
    @api.depends('routing_slip_id')
    def _compute_routing_slip_count(self):
        for record in self:
            record.routing_slip_count = 1 if record.routing_slip_id else 0
    



class handover_act_line(models.Model):
    _name = 'handover.act.line'
    _description = 'Handover act line'
    
    work_handover_id = fields.Many2one('work.handover.act', 'Work handover act')
    code = fields.Integer('Code')
    company_id = fields.Many2one('res.company', 'Company')
    job_id = fields.Many2one('hr.job', 'Job')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    date = fields.Date('Date')
    handover_category_ids = fields.Many2many(
        'handover.act.category', 'handover_act_category_rel',
        'rout_id', 'handover_category_id', groups="hr.group_hr_manager",
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
                employee_obj = self.env['hr.employee']
                emp_id = employee_obj.search([('job_id', '=', job_id.id)])
                emp = employee_obj.browse(emp_id)
                if len(emp_id) == 1:
                    res['employee_id'] = emp.id
                
            
        return {'value':res}


class handover_act_master(models.Model):
    _name = 'handover.act.master'
    _description = 'Routing master'

    job_id = fields.Many2one('hr.job', 'Job', copy=False)
    master_line_id = fields.One2many('handover.act.master.line', 'handover_master_id', 'Line', copy=False)

    _sql_constraints = [
        ('job_id', 'unique("job_id")', 'Field job_id must be unique.'),
        ]
    def unlink(self, vals):
        obj = self.browse()[0]
        line_obj = self.env['handover.act.master.line']
        for line in obj.master_line_id:
            line_obj.unlink(line.id)
        return super(handover_act_master, self).unlink(vals)


class handover_act_master_line(models.Model):
    _name = 'handover.act.master.line'
    _description = 'Handover act master line'

    handover_master_id = fields.Many2one('handover.act.master', 'Handover act master')
    code = fields.Integer('Code')
    company_id = fields.Many2one('res.company', 'Company')
    job_id = fields.Many2one('hr.job', 'Job', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee')
    date = fields.Date('Date')
    handover_category_ids = fields.Many2many(
        'handover.act.category', 'handover_master_category_rel',
        'master_id', 'handover_act_category_id', groups="hr.group_hr_manager",
        string='Tags')
    note = fields.Char('Note')
    signature = fields.Char('Signature')
    def create(self, vals):
        res = {}
        
        master_id = super(handover_act_master_line, self).create(vals)
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
                employee_obj = self.env['hr.employee']
                emp_id = employee_obj.search([('job_id', '=', job_id.id)])
                emp = employee_obj.browse(emp_id)
                if len(emp_id) == 1:
                    res['employee_id'] = emp.id
            
        return {'value':res}


class handover_act_category(models.Model):
    _name = "handover.act.category"
    _description = "Handover act Category"

    name = fields.Char(string="Tag Name", required=True)
    color = fields.Integer(string='Color Index')
    handover_ids = fields.Many2many('handover.act.line', 'handover_act_category_rel', 'handover_category_id', 'rout_id', string='Handover act category')
    master_ids = fields.Many2many('handover.act.master.line', 'handover_master_category_rel', 'handover_act_category_id', 'master_id', string='Master category')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
