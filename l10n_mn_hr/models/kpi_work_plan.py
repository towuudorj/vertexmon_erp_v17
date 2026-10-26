# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KpiWorkPlan(models.Model):
    _name = 'kpi.work.plan'
    _description = 'Ажлын төлөвлөгөө'
    _inherit = ['kpi.period.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'year desc, quarter desc, month desc, employee_id'

    name = fields.Char('Нэр', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', 'Ажилтан', required=True, tracking=True, index=True,
                                  default=lambda self: self.env.user.employee_id)
    user_id = fields.Many2one('res.users', 'Хэрэглэгч', related='employee_id.user_id', store=True)
    job_title = fields.Char('Албан тушаал', compute='_compute_job_title', store=True, readonly=False)
    manager_id = fields.Many2one('hr.employee', 'Шууд удирдлага', compute='_compute_manager_id', store=True,
                                 readonly=False, tracking=True)
    manager_user_id = fields.Many2one('res.users', related='manager_id.user_id', store=True)
    company_id = fields.Many2one('res.company', 'Компани', required=True, default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Төлөвлөж буй'),
        ('to_approve', 'Батлуулахаар илгээсэн'),
        ('approved', 'Батлагдсан / Хэрэгжиж буй'),
        ('submitted', 'Гүйцэтгэл илгээсэн'),
        ('done', 'Дүгнэгдсэн'),
    ], string='Төлөв', default='draft', required=True, tracking=True, copy=False)
    date_approved = fields.Date('Баталсан огноо', readonly=True, copy=False)
    date_submitted = fields.Date('Гүйцэтгэл илгээсэн огноо', readonly=True, copy=False)
    date_evaluated = fields.Date('Дүгнэсэн огноо', readonly=True, copy=False)
    note = fields.Html('Удирдлагын тайлбар')

    line_ids = fields.One2many('kpi.work.plan.line', 'plan_id', string='Төлөвлөгөөт ажлууд',
                               domain=[('is_extra', '=', False)], copy=True)
    extra_line_ids = fields.One2many('kpi.work.plan.line', 'plan_id', string='Бусад ажлын биелэлт',
                                     domain=[('is_extra', '=', True)])
    progress_avg = fields.Float('Гүйцэтгэл (%)', compute='_compute_scores', store=True, group_operator='avg')
    rating_avg = fields.Float('Үнэлгээ (%)', compute='_compute_scores', store=True, group_operator='avg')
    extra_progress_avg = fields.Float('Бусад ажил - гүйцэтгэл (%)', compute='_compute_scores', store=True)
    extra_rating_avg = fields.Float('Бусад ажил - үнэлгээ (%)', compute='_compute_scores', store=True)
    task_count = fields.Integer('Даалгавар', compute='_compute_task_count')

    is_employee = fields.Boolean(compute='_compute_user_role')
    is_manager = fields.Boolean(compute='_compute_user_role')

    @api.depends('employee_id', 'period_label')
    def _compute_name(self):
        for plan in self:
            plan.name = '%s - %s' % (plan.employee_id.name or '', plan.period_label or '')

    @api.depends('employee_id')
    def _compute_job_title(self):
        for plan in self:
            plan.job_title = plan.employee_id.job_title or plan.employee_id.job_id.name

    @api.depends('employee_id')
    def _compute_manager_id(self):
        for plan in self:
            plan.manager_id = plan.employee_id.parent_id

    @api.depends('line_ids.progress', 'line_ids.rating', 'extra_line_ids.progress', 'extra_line_ids.rating')
    def _compute_scores(self):
        def avg(values):
            return sum(values) / len(values) if values else 0.0
        for plan in self:
            plan.progress_avg = avg(plan.line_ids.mapped('progress'))
            plan.rating_avg = avg(plan.line_ids.mapped('rating'))
            plan.extra_progress_avg = avg(plan.extra_line_ids.mapped('progress'))
            plan.extra_rating_avg = avg(plan.extra_line_ids.mapped('rating'))

    def _compute_task_count(self):
        data = self.env['dev.task'].sudo()._read_group(
            [('plan_line_id.plan_id', 'in', self.ids)], ['plan_line_id'], ['__count'])
        counts = {}
        for line, count in data:
            counts[line.plan_id.id] = counts.get(line.plan_id.id, 0) + count
        for plan in self:
            plan.task_count = counts.get(plan.id, 0)

    @api.depends_context('uid')
    @api.depends('employee_id', 'manager_id')
    def _compute_user_role(self):
        is_admin = self.env.user.has_group('l10n_mn_hr.group_dev_task_manager')
        for plan in self:
            plan.is_employee = plan.employee_id.user_id == self.env.user
            plan.is_manager = is_admin or plan.manager_id.user_id == self.env.user

    @api.constrains('employee_id', 'year', 'period_type', 'month', 'quarter')
    def _check_period(self):
        for plan in self:
            if plan.period_type == 'month' and not plan.month:
                raise ValidationError(_('Сарыг сонгоно уу.'))
            if plan.period_type == 'quarter' and not plan.quarter:
                raise ValidationError(_('Улирлыг сонгоно уу.'))
            domain = [('id', '!=', plan.id), ('employee_id', '=', plan.employee_id.id),
                      ('year', '=', plan.year), ('period_type', '=', plan.period_type)]
            domain += [('month', '=', plan.month)] if plan.period_type == 'month' else [('quarter', '=', plan.quarter)]
            if self.sudo().search_count(domain):
                raise ValidationError(_('%s ажилтны %s-ны ажлын төлөвлөгөө аль хэдийн бүртгэгдсэн байна!')
                                      % (plan.employee_id.name, plan.period_label))

    # ------------------------------------------------------------------
    # Эрхийн шалгалт
    # ------------------------------------------------------------------
    def _check_employee(self):
        for plan in self:
            if not plan.is_employee and not self.env.user.has_group('l10n_mn_hr.group_dev_task_manager'):
                raise UserError(_('Энэ үйлдлийг зөвхөн төлөвлөгөөний эзэн ажилтан хийнэ.'))

    def _check_manager(self):
        for plan in self:
            if not plan.is_manager:
                raise UserError(_('Энэ үйлдлийг зөвхөн шууд удирдлага (%s) хийнэ.') % (plan.manager_id.name or '-'))

    def _check_state(self, allowed):
        for plan in self:
            if plan.state not in allowed:
                raise UserError(_('%s төлөвлөгөөний төлөв энэ үйлдэлд тохирохгүй байна.') % plan.name)

    def _notify_user(self, user, summary):
        for plan in self:
            if user:
                plan.activity_schedule('mail.mail_activity_data_todo', user_id=user.id, summary=summary)

    # ------------------------------------------------------------------
    # Төлөвийн шилжилт
    # ------------------------------------------------------------------
    def action_send_approval(self):
        self._check_state(['draft'])
        self._check_employee()
        for plan in self:
            if not plan.line_ids:
                raise UserError(_('Төлөвлөгөөт ажил оруулна уу.'))
            if not plan.manager_id.user_id:
                raise UserError(_('%s ажилтны шууд удирдлага (хэрэглэгчтэй) тохируулаагүй байна.')
                                % plan.employee_id.name)
        self.write({'state': 'to_approve'})
        for plan in self:
            plan._notify_user(plan.manager_id.user_id, _('Ажлын төлөвлөгөө батлах'))

    def action_approve(self):
        self._check_state(['to_approve'])
        self._check_manager()
        self.activity_feedback(['mail.mail_activity_data_todo'])
        self.write({'state': 'approved', 'date_approved': fields.Date.context_today(self)})

    def action_reject(self):
        self._check_state(['to_approve', 'submitted'])
        self._check_manager()
        self.activity_unlink(['mail.mail_activity_data_todo'])
        for plan in self:
            new_state = 'draft' if plan.state == 'to_approve' else 'approved'
            plan.write({'state': new_state})
            plan._notify_user(plan.employee_id.user_id, _('Ажлын төлөвлөгөө буцаагдсан'))

    def action_submit(self):
        """Ажилтан гүйцэтгэлээ оруулаад удирдлагад илгээнэ. Үнэлгээг гүйцэтгэлээр урьдчилан бөглөнө."""
        self._check_state(['approved'])
        self._check_employee()
        for plan in self:
            for line in plan.line_ids | plan.extra_line_ids:
                if not line.rating:
                    line.rating = line.progress
        self.write({'state': 'submitted', 'date_submitted': fields.Date.context_today(self)})
        for plan in self:
            plan._notify_user(plan.manager_id.user_id, _('Ажлын гүйцэтгэл дүгнэх'))

    def action_evaluate(self):
        self._check_state(['submitted'])
        self._check_manager()
        self.activity_feedback(['mail.mail_activity_data_todo'])
        self.write({'state': 'done', 'date_evaluated': fields.Date.context_today(self)})

    def action_reset_draft(self):
        if not self.env.user.has_group('l10n_mn_hr.group_dev_task_manager'):
            raise UserError(_('Зөвхөн KPI менежер ноорог болгоно.'))
        self.write({'state': 'draft'})

    def action_view_tasks(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('l10n_mn_hr.action_dev_task')
        action['domain'] = [('plan_line_id.plan_id', '=', self.id)]
        action['context'] = {}
        return action

    # ------------------------------------------------------------------
    # Тайлан
    # ------------------------------------------------------------------
    def _get_report_groups(self):
        """Хэвлэх үед 'Ерөнхий ажил'-аар бүлэглэж rowspan тооцоолно."""
        self.ensure_one()
        groups = []
        for line in self.line_ids.sorted(lambda l: (l.sequence, l.id)):
            key = (line.general_work or '').strip()
            if groups and groups[-1]['name'] == key:
                groups[-1]['lines'] |= line
            else:
                groups.append({'name': key, 'lines': line})
        return groups


class KpiWorkPlanLine(models.Model):
    _name = 'kpi.work.plan.line'
    _description = 'Ажлын төлөвлөгөөний мөр'
    _order = 'plan_id, is_extra, sequence, id'

    plan_id = fields.Many2one('kpi.work.plan', 'Төлөвлөгөө', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    is_extra = fields.Boolean('Төлөвлөгөөнөөс бусад ажил', default=False,
                              help='Ажлын төлөвлөгөөнд тусгагдаагүй, удирдлагаас өгсөн үүрэг даалгавар')
    general_work = fields.Char('Ерөнхий ажил')
    name = fields.Text('Хийгдэх ажил', required=True)
    result = fields.Text('Үр дүн (шинэчлэлт)')
    date_deadline = fields.Date('Хийгдсэн байх сүүлийн хугацаа')
    status = fields.Selection([
        ('not_started', '-'),
        ('in_progress', 'Хийгдэж байгаа'),
        ('done', 'Бүрэн хийгдсэн'),
    ], string='Төлөв', default='not_started')
    progress = fields.Float('Гүйцэтгэл (%)')
    rating = fields.Float('Үнэлгээ (%)')
    task_ids = fields.One2many('dev.task', 'plan_line_id', string='Даалгаврууд')
    task_count = fields.Integer('Даалгавар', compute='_compute_task_count')

    @api.depends('task_ids')
    def _compute_task_count(self):
        for line in self:
            line.task_count = len(line.task_ids)

    @api.onchange('progress')
    def _onchange_progress(self):
        if self.progress >= 100:
            self.status = 'done'
        elif self.progress > 0:
            self.status = 'in_progress'

    @api.constrains('progress', 'rating')
    def _check_percent(self):
        for line in self:
            if not (0 <= line.progress <= 100) or not (0 <= line.rating <= 100):
                raise ValidationError(_('Гүйцэтгэл, үнэлгээ 0-100% хооронд байна.'))

    @api.depends('plan_id.name', 'name')
    def _compute_display_name(self):
        for line in self:
            text = (line.name or '').split('\n')[0]
            line.display_name = '[%s] %s' % (line.general_work, text) if line.general_work else text
