# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from .kpi_template import effective_achievement


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

    # Ажлын гүйцэтгэлийг дүгнэх хуудас (KPI) — хэвлэх болон ажлын төлөвлөгөөтэй холбох талбарууд
    job_title = fields.Char(string="Албан тушаал", compute="_compute_titles", store=True, readonly=False)
    manager_title = fields.Char(string="Шууд удирдлагын албан тушаал", compute="_compute_titles", store=True, readonly=False)
    manager_user_id = fields.Many2one("res.users", related="manager_employee_id.user_id", store=True)
    user_id = fields.Many2one("res.users", related="employee_id.user_id", store=True)
    approver_id = fields.Many2one("hr.employee", string="Батлах удирдлага", compute="_compute_from_template",
                                  store=True, readonly=False)
    approver_title = fields.Char(string="Батлах удирдлагын албан тушаал", compute="_compute_from_template",
                                 store=True, readonly=False)
    kpi_amount_note = fields.Char(string="KPI 100%-д ногдох мөнгөн дүн", compute="_compute_from_template",
                                  store=True, readonly=False)
    min_score = fields.Float(string="KPI олгох босго үнэлгээ", compute="_compute_from_template", store=True,
                             readonly=False)
    date_evaluation = fields.Date(string="Үнэлгээ хийсэн огноо")
    is_eligible = fields.Boolean(string="KPI олгох", compute="_compute_is_eligible", store=True)
    period_label = fields.Char(string="Хугацаа", compute="_compute_period_label")
    work_plan_ids = fields.Many2many("kpi.work.plan", string="Ажлын төлөвлөгөө", compute="_compute_work_plan_ids")

    def _prepare_template_line_commands(self, template, preserve_existing=False):
        self.ensure_one()
        commands = [(5, 0, 0)]
        existing_map = {}
        if preserve_existing:
            existing_map = {
                line.template_line_id.id: (line.achieved_percentage, line.achievement)
                for line in self.line_ids
                if line.template_line_id
            }
        if not template:
            return commands
        for line in template.line_ids.sorted(key=lambda rec: (rec.sequence, rec.id)):
            achieved, achievement = existing_map.get(line.id, (0.0, 0.0))
            commands.append((0, 0, {
                'template_line_id': line.id,
                'achieved_percentage': achieved,
                'achievement': achievement,
            }))
        return commands

    def _prepare_create_line_commands(self, template, line_commands=None):
        self.ensure_one()
        if not template:
            return [(5, 0, 0)]

        achieved_by_template_line = {}
        achievement_by_template_line = {}
        positional_achievements = []
        for command in line_commands or []:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or command[0] != 0:
                continue
            values = command[2] or {}
            achieved_percentage = values.get('achieved_percentage', 0.0)
            template_line_id = values.get('template_line_id')
            if template_line_id:
                achieved_by_template_line[template_line_id] = achieved_percentage
                achievement_by_template_line[template_line_id] = values.get('achievement', 0.0)
            else:
                positional_achievements.append(achieved_percentage)

        commands = [(5, 0, 0)]
        positional_iter = iter(positional_achievements)
        for line in template.line_ids.sorted(key=lambda rec: (rec.sequence, rec.id)):
            commands.append((0, 0, {
                'template_line_id': line.id,
                'achieved_percentage': achieved_by_template_line.get(line.id, next(positional_iter, 0.0)),
                'achievement': achievement_by_template_line.get(line.id, 0.0),
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

    # ------------------------------------------------------------------
    # Ажлын гүйцэтгэлийг дүгнэх хуудас (KPI)
    # ------------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_titles(self):
        for rec in self:
            emp = rec.employee_id
            rec.job_title = emp.job_title or emp.job_id.name
            rec.manager_title = emp.parent_id.job_title or emp.parent_id.job_id.name

    @api.depends('kpi_template_id')
    def _compute_from_template(self):
        for rec in self:
            tmpl = rec.kpi_template_id
            rec.approver_id = tmpl.approver_id
            rec.approver_title = tmpl.approver_title or 'Гүйцэтгэх захирал'
            rec.kpi_amount_note = tmpl.kpi_amount_note
            rec.min_score = tmpl.min_score or 0.8

    @api.depends('total_achieved_percentage', 'min_score')
    def _compute_is_eligible(self):
        for rec in self:
            rec.is_eligible = rec.total_achieved_percentage >= rec.min_score

    def _get_period_quarters(self):
        """KPI-ийн хугацаанд хамаарах ([улирлууд], сар)"""
        self.ensure_one()
        if self.date_type == 'month' and self.period_month:
            return [str((int(self.period_month) - 1) // 3 + 1)], self.period_month
        if self.date_type == 'session' and self.period_session:
            return [self.period_session[1:]], False
        if self.date_type == 'half_year' and self.period_half:
            return (['1', '2'] if self.period_half == 'first_half' else ['3', '4']), False
        return [], False

    @api.depends('date_type', 'period_year', 'period_month', 'period_session', 'period_half')
    def _compute_period_label(self):
        half = {'first_half': 'эхний хагас жил', 'second_half': 'сүүлийн хагас жил'}
        for rec in self:
            if rec.date_type == 'month' and rec.period_month:
                rec.period_label = '%s оны %s-р сар' % (rec.period_year, rec.period_month)
            elif rec.date_type == 'session' and rec.period_session:
                rec.period_label = '%s оны %s-р улирал' % (rec.period_year, rec.period_session[1:])
            elif rec.date_type == 'half_year' and rec.period_half:
                rec.period_label = '%s оны %s' % (rec.period_year, half[rec.period_half])
            else:
                rec.period_label = str(rec.period_year or '')

    @api.depends('employee_id', 'date_type', 'period_year', 'period_month', 'period_session', 'period_half')
    def _compute_work_plan_ids(self):
        Plan = self.env['kpi.work.plan']
        for rec in self:
            quarters, month = rec._get_period_quarters() if rec.employee_id else ([], False)
            if not quarters:
                rec.work_plan_ids = False
                continue
            plans = Plan.search([('employee_id', '=', rec.employee_id.id), ('year', '=', rec.period_year),
                                 ('quarter', 'in', quarters)], order='quarter, period_type desc, month')
            if month:
                monthly = plans.filtered(lambda p: p.period_type == 'month' and p.month == month)
                plans = monthly or plans.filtered(lambda p: p.period_type == 'quarter')
            rec.work_plan_ids = plans

    def action_compute_from_plans(self):
        """Ажлын төлөвлөгөөний үнэлгээг KPI мөрүүд рүү татна."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Батлагдсан KPI-г өөрчлөх боломжгүй.'))
            plans = rec.work_plan_ids.filtered(lambda p: p.state in ('submitted', 'done'))
            if not plans:
                raise UserError(_('%s: тухайн хугацаанд гүйцэтгэл илгээсэн / дүгнэгдсэн ажлын төлөвлөгөө алга.')
                                % rec.employee_id.name)
            planned = plans.mapped('line_ids')
            extra = plans.mapped('extra_line_ids')
            # Ажлын төлөвлөгөөнд 0-100, KPI-д бутархай
            plan_score = sum(planned.mapped('rating')) / len(planned) / 100.0 if planned else 0.0
            extra_score = sum(extra.mapped('rating')) / len(extra) / 100.0 if extra else None
            for line in rec.line_ids:
                if line.source_type == 'work_plan':
                    line.achievement = plan_score
                elif line.source_type == 'extra' and extra_score is not None:
                    line.achievement = extra_score
            if not rec.date_evaluation:
                rec.date_evaluation = fields.Date.context_today(rec)

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
    _order = "sequence, id"

    employee_kpi_id = fields.Many2one("employee.kpi", string="Employee KPI", required=True, ondelete="cascade")
    template_line_id = fields.Many2one("kpi.template.line", string="Template Line", required=True, ondelete="restrict")
    name = fields.Many2one("kpi.line.section", related="template_line_id.name", string="KPI Section", store=True, readonly=True)
    weight_percentage = fields.Float(related="template_line_id.weight_percentage", string="Weight Percentage", store=True, readonly=True)
    achieved_percentage = fields.Float(string="Achieved Percentage")
    sequence = fields.Integer(related="template_line_id.sequence", store=True)
    criteria = fields.Html(related="template_line_id.criteria")
    source = fields.Char(related="template_line_id.source")
    target = fields.Text(related="template_line_id.target")
    source_type = fields.Selection(related="template_line_id.source_type")
    calc_method = fields.Selection(related="template_line_id.calc_method")
    evaluator = fields.Char(related="template_line_id.evaluator")
    achievement = fields.Float(string="Тайлант хугацааны гүйцэтгэл",
                               help="Оруулбал жинлэсэн оноог (Achieved Percentage) автоматаар тооцно.")

    def _score_from_achievement(self, achievement):
        self.ensure_one()
        return self.weight_percentage * effective_achievement(achievement, self.calc_method)

    @api.onchange("achievement")
    def _onchange_achievement(self):
        for line in self:
            line.achieved_percentage = line._score_from_achievement(line.achievement)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            if vals.get("achievement") and "achieved_percentage" not in vals:
                line.achieved_percentage = line._score_from_achievement(line.achievement)
        return lines

    def write(self, vals):
        res = super().write(vals)
        if "achievement" in vals and "achieved_percentage" not in vals:
            for line in self:
                super(EmployeeKpiLine, line).write(
                    {"achieved_percentage": line._score_from_achievement(line.achievement)})
        return res

    @api.constrains("achieved_percentage", "weight_percentage")
    def _check_achieved_percentage(self):
        for record in self:
            if record.achieved_percentage < 0:
                raise ValidationError("Achieved Percentage cannot be negative.")
            if record.achieved_percentage > record.weight_percentage:
                raise ValidationError("Achieved Percentage cannot be greater than Weight Percentage.")
