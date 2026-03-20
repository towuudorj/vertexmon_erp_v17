# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class EmployeeKpi(models.Model):
    _name = "employee.kpi"
    _description = "Employee KPI"
    _inherit = ["mail.thread"]
    _order = "period_year desc, id desc"

    name = fields.Char(string="Record Name", compute="_compute_name", store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
    ], string='State', default='draft', tracking=True)
    can_approve = fields.Boolean(string='Can Approve', compute='_compute_can_approve')
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    manager_employee_id = fields.Many2one('hr.employee', string='Direct Manager', related='employee_id.parent_id', store=True, readonly=True)
    company_id = fields.Many2one("res.company", string="Company", related="employee_id.company_id", store=True, readonly=True)
    department_id = fields.Many2one("hr.department", string="Department", related="employee_id.department_id", store=True, readonly=True)
    job_id = fields.Many2one("hr.job", string="Job Position", related="employee_id.job_id", store=True, readonly=True)
    kpi_template_id = fields.Many2one("kpi.template", string="KPI Template", required=True, tracking=True)
    date_type = fields.Selection(related="kpi_template_id.date_type", string="Period Type", store=True, readonly=True)
    period_year = fields.Integer(string="Period Year", required=True, default=lambda self: fields.Date.today().year, tracking=True)
    period_month = fields.Selection([
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
    ], string="KPI Month", tracking=True)
    period_session = fields.Selection([
        ("q1", "Quarter 1"),
        ("q2", "Quarter 2"),
        ("q3", "Quarter 3"),
        ("q4", "Quarter 4"),
    ], string="KPI Quarter", tracking=True)
    period_half = fields.Selection([
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ], string="KPI Half", tracking=True)
    note = fields.Text(string="Description")
    line_ids = fields.One2many("employee.kpi.line", "employee_kpi_id", string="KPI Lines")
    total_achieved_percentage = fields.Float(string="Total Achieved Percentage", compute="_compute_total_achieved_percentage", store=True)

    def _prepare_template_line_commands(self, template, preserve_existing=False):
        self.ensure_one()
        commands = [(5, 0, 0)]
        existing_map = {}
        if preserve_existing:
            existing_map = {
                line.template_line_id.id: line.achieved_percentage
                for line in self.line_ids
                if line.template_line_id
            }
        if not template:
            return commands
        for line in template.line_ids.sorted(key=lambda rec: rec.id):
            commands.append((0, 0, {
                'template_line_id': line.id,
                'achieved_percentage': existing_map.get(line.id, 0.0),
            }))
        return commands

    def _prepare_create_line_commands(self, template, line_commands=None):
        self.ensure_one()
        if not template:
            return [(5, 0, 0)]

        achieved_by_template_line = {}
        positional_achievements = []
        for command in line_commands or []:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                continue
            values = command[2] or {}
            achieved_percentage = values.get('achieved_percentage', 0.0)
            template_line_id = values.get('template_line_id')
            if template_line_id:
                achieved_by_template_line[template_line_id] = achieved_percentage
            else:
                positional_achievements.append(achieved_percentage)

        commands = [(5, 0, 0)]
        positional_iter = iter(positional_achievements)
        for line in template.line_ids.sorted(key=lambda rec: rec.id):
            commands.append((0, 0, {
                'template_line_id': line.id,
                'achieved_percentage': achieved_by_template_line.get(line.id, next(positional_iter, 0.0)),
            }))
        return commands


    @api.depends('manager_employee_id')
    def _compute_can_approve(self):
        current_employee = self.env.user.employee_id
        for record in self:
            record.can_approve = bool(current_employee and record.manager_employee_id and current_employee == record.manager_employee_id)

    @api.depends("line_ids.achieved_percentage")
    def _compute_total_achieved_percentage(self):
        for record in self:
            record.total_achieved_percentage = sum(record.line_ids.mapped("achieved_percentage"))

    @api.depends("employee_id", "period_year", "period_month", "period_session", "period_half", "date_type")
    def _compute_name(self):
        month_labels = dict(self._fields["period_month"].selection)
        session_labels = dict(self._fields["period_session"].selection)
        half_labels = dict(self._fields["period_half"].selection)
        for record in self:
            period_label = str(record.period_year or "")
            if record.date_type == "month" and record.period_month:
                period_label = "%s %s" % (month_labels.get(record.period_month, record.period_month), record.period_year)
            elif record.date_type == "session" and record.period_session:
                period_label = "%s %s" % (session_labels.get(record.period_session, record.period_session), record.period_year)
            elif record.date_type == "half_year" and record.period_half:
                period_label = "%s %s" % (half_labels.get(record.period_half, record.period_half), record.period_year)
            record.name = "%s - %s" % (record.employee_id.name or "KPI", period_label)

    @api.onchange("date_type")
    def _onchange_date_type(self):
        for record in self:
            if record.date_type != "month":
                record.period_month = False
            if record.date_type != "session":
                record.period_session = False
            if record.date_type != "half_year":
                record.period_half = False

    @api.onchange("kpi_template_id")
    def _onchange_kpi_template_id(self):
        for record in self:
            record.line_ids = record._prepare_template_line_commands(record.kpi_template_id)

    @api.model
    def create(self, vals):
        if vals.get('kpi_template_id'):
            template = self.env['kpi.template'].browse(vals['kpi_template_id'])
            new_record = self.new(vals)
            vals['line_ids'] = new_record._prepare_create_line_commands(template, vals.get('line_ids'))
        return super(EmployeeKpi, self).create(vals)

    def write(self, vals):
        template_changed = vals.get('kpi_template_id') and 'line_ids' not in vals
        res = super(EmployeeKpi, self).write(vals)
        if template_changed:
            for record in self.filtered(lambda rec: rec.state == 'draft'):
                record.line_ids = record._prepare_template_line_commands(
                    record.kpi_template_id,
                    preserve_existing=True,
                )
        return res

    def action_approve(self):
        current_employee = self.env.user.employee_id
        for record in self:
            if record.state != 'draft':
                continue
            if not current_employee or current_employee != record.manager_employee_id:
                raise UserError(_('Only the direct manager can approve this KPI.'))
            record.state = 'approved'

    def action_cancel(self):
        current_employee = self.env.user.employee_id
        for record in self:
            if record.state == 'draft':
                continue
            if not current_employee or current_employee != record.manager_employee_id:
                raise UserError(_('Only the direct manager can approve this KPI.'))
            record.state = 'draft'

    @api.constrains("date_type", "period_month", "period_session", "period_half")
    def _check_period_fields(self):
        for record in self:
            if record.date_type == "month" and not record.period_month:
                raise ValidationError("KPI Month is required for monthly KPI records.")
            if record.date_type == "session" and not record.period_session:
                raise ValidationError("KPI Quarter is required for quarterly KPI records.")
            if record.date_type == "half_year" and not record.period_half:
                raise ValidationError("KPI Half is required for half-year KPI records.")


class EmployeeKpiLine(models.Model):
    _name = "employee.kpi.line"
    _description = "Employee KPI Line"
    _order = "id"

    employee_kpi_id = fields.Many2one("employee.kpi", string="Employee KPI", required=True, ondelete="cascade")
    template_line_id = fields.Many2one("kpi.template.line", string="Template Line", required=True, ondelete="restrict")
    name = fields.Many2one("kpi.line.section", related="template_line_id.name", string="KPI Section", store=True, readonly=True)
    weight_percentage = fields.Float(related="template_line_id.weight_percentage", string="Weight Percentage", store=True, readonly=True)
    achieved_percentage = fields.Float(string="Achieved Percentage")

    @api.constrains("achieved_percentage", "weight_percentage")
    def _check_achieved_percentage(self):
        for record in self:
            if record.achieved_percentage < 0:
                raise ValidationError("Achieved Percentage cannot be negative.")
            if record.achieved_percentage > record.weight_percentage:
                raise ValidationError("Achieved Percentage cannot be greater than Weight Percentage.")
