# -*- coding: utf-8 -*-
import json

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class DevTaskType(models.Model):
    _name = 'dev.task.type'
    _description = 'Даалгаврын төрөл'
    _order = 'sequence, name'

    name = fields.Char('Нэр', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    department_id = fields.Many2one('hr.department', 'Алба нэгж',
                                    help='Хоосон бол бүх албанд харагдана.')
    color = fields.Integer('Өнгө')


class DevTask(models.Model):
    _name = 'dev.task'
    _description = 'Даалгавар'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, id desc'

    name = fields.Char('Дугаар', required=True, copy=False, readonly=True, default='/')
    title = fields.Char('Гарчиг', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', 'Гүйцэтгэх алба', tracking=True, index=True,
                                    default=lambda self: self.env.user.employee_id.department_id)
    type_id = fields.Many2one('dev.task.type', 'Төрөл', required=True, tracking=True,
                              domain="['|', ('department_id', '=', False), ('department_id', '=', department_id)]")
    type_color = fields.Integer(related='type_id.color')
    state = fields.Selection([
        ('new', 'Шинэ'),
        ('in_progress', 'Хийгдэж буй'),
        ('review', 'Шалгах'),
        ('done', 'Дууссан'),
    ], string='Төлөв', required=True, default='new', copy=False, tracking=True, group_expand='_group_expand_state')
    priority = fields.Selection([
        ('0', 'Энгийн'),
        ('1', 'Чухал'),
        ('2', 'Яаралтай'),
    ], string='Ач холбогдол', default='0', tracking=True)
    description = fields.Html('Тайлбар')
    result_note = fields.Html('Гүйцэтгэлийн тайлбар')

    requester_id = fields.Many2one('res.users', 'Даалгавар үүсгэсэн', required=True, readonly=True, copy=False,
                                   default=lambda self: self.env.user, tracking=True)
    assignee_id = fields.Many2one('res.users', 'Гүйцэтгэгч', tracking=True, index=True,
                                  domain="[('id', 'in', allowed_assignee_ids)]",
                                  help='Гүйцэтгэх албаны ажилтнууд харагдана.')
    allowed_assignee_ids = fields.Many2many('res.users', compute='_compute_allowed_assignee_ids')
    reviewer_id = fields.Many2one('res.users', 'Шалгах ажилтан', tracking=True,
                                  domain="[('share', '=', False)]",
                                  help='Хоосон бол даалгавар үүсгэсэн ажилтан шалгана.')
    review_user_id = fields.Many2one('res.users', 'Шалгагч', compute='_compute_review_user_id', store=True,
                                     index=True)
    plan_line_id = fields.Many2one('kpi.work.plan.line', 'Ажлын төлөвлөгөөний ажил', tracking=True, index=True,
                                   domain="[('plan_id.user_id', '=', assignee_id), "
                                          "('plan_id.state', 'in', ('draft', 'to_approve', 'approved'))]",
                                   help='Гүйцэтгэгчийн KPI ажлын төлөвлөгөөний аль ажилд хамаарах')
    company_id = fields.Many2one('res.company', 'Компани', required=True, default=lambda self: self.env.company)
    module_name = fields.Char('Модуль / Цэс / Ажлын хүрээ')

    date_deadline = fields.Date('Дуусгах хугацаа', tracking=True)
    date_start = fields.Datetime('Эхэлсэн огноо', readonly=True, copy=False)
    date_review = fields.Datetime('Шалгуулсан огноо', readonly=True, copy=False)
    date_done = fields.Datetime('Дууссан огноо', readonly=True, copy=False)
    is_overdue = fields.Boolean('Хугацаа хэтэрсэн', compute='_compute_is_overdue')
    is_on_time = fields.Boolean('Хугацаандаа дууссан', compute='_compute_is_on_time', store=True)

    is_reviewer = fields.Boolean(compute='_compute_user_rights')
    is_assignee = fields.Boolean(compute='_compute_user_rights')

    def init(self):
        """Хуучин хувилбараас үлдсэн талбаруудыг цэвэрлэнэ (upgrade бүрт ажиллана).

        - developer_id -> assignee_id утгыг шилжүүлнэ.
        - Кодоос хасагдсан tracking-тэй талбарыг Odoo устгахдаа mail модуль registry-ээс хайж
          KeyError өгдөг тул түүхийг field_info-д урьдчилан хадгалж, tracking-ийг унтраана.
        """
        cr = self.env.cr
        cr.execute("""SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'dev_task' AND column_name = 'developer_id'""")
        if cr.fetchone():
            cr.execute("UPDATE dev_task SET assignee_id = developer_id "
                       "WHERE assignee_id IS NULL AND developer_id IS NOT NULL")
        cr.execute("""SELECT id, name, field_description, ttype FROM ir_model_fields
                       WHERE model = %s AND tracking IS NOT NULL""", (self._name,))
        for field_id, name, desc, ttype in cr.fetchall():
            if name in self._fields:
                continue
            if isinstance(desc, dict):
                desc = desc.get('mn_MN') or desc.get('en_US') or name
            cr.execute("""UPDATE mail_tracking_value SET field_info = %s
                           WHERE field_id = %s AND field_info IS NULL""",
                       (json.dumps({'desc': desc, 'name': name, 'sequence': 100, 'type': ttype}), field_id))
            cr.execute("UPDATE ir_model_fields SET tracking = NULL WHERE id = %s", (field_id,))
        # Загвар анх noupdate="1" блокоос үүссэн тул ir_model_data.noupdate=True үлдэж, XML-ээс
        # шинэчлэгдэхгүй байсан. Тэмдгийг арилгаснаар upgrade бүрт XML-ийн агуулгаар шинэчлэгдэнэ.
        cr.execute("""
            UPDATE ir_model_data SET noupdate = FALSE
             WHERE module = 'l10n_mn_hr' AND name = 'mail_template_dev_task_review' AND noupdate
        """)
        # "Шалгана уу" имэйлийн загварын хуучин хэлний хувилбаруудыг (mn_MN гэх мэт) арилгана.
        # body_html орчуулагддаг тул upgrade зөвхөн en_US-г шинэчилдэг; текст нь монголоор бичигдсэн
        # тул бүх хэл en_US утгыг ашиглана.
        cr.execute("""
            UPDATE mail_template t
               SET body_html = jsonb_build_object('en_US', t.body_html->'en_US'),
                   subject = jsonb_build_object('en_US', t.subject->'en_US')
              FROM ir_model_data d
             WHERE d.model = 'mail.template' AND d.res_id = t.id
               AND d.module = 'l10n_mn_hr' AND d.name = 'mail_template_dev_task_review'
        """)
        # Хасагдсан талбараар хадгалсан шүүлтүүр (Favorites) алдаа өгөхөөс сэргийлнэ
        cr.execute("""DELETE FROM ir_filters WHERE model_id = %s
                       AND (context ILIKE '%%task_type%%' OR domain ILIKE '%%task_type%%'
                            OR context ILIKE '%%developer_id%%' OR domain ILIKE '%%developer_id%%')""",
                   (self._name,))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('dev.task') or '/'
        return super().create(vals_list)

    @api.model
    def _group_expand_state(self, states, domain, order):
        return [key for key, _label in self._fields['state'].selection]

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.type_id.department_id and self.type_id.department_id != self.department_id:
            self.type_id = False

    @api.depends('department_id')
    def _compute_allowed_assignee_ids(self):
        Users = self.env['res.users']
        for task in self:
            if task.department_id:
                employees = self.env['hr.employee'].sudo().search([('department_id', '=', task.department_id.id)])
                task.allowed_assignee_ids = employees.mapped('user_id')
            else:
                task.allowed_assignee_ids = Users.search([('share', '=', False)])

    @api.depends('reviewer_id', 'requester_id')
    def _compute_review_user_id(self):
        for task in self:
            task.review_user_id = task.reviewer_id or task.requester_id

    @api.onchange('department_id')
    def _onchange_department_assignee(self):
        if self.assignee_id and self.assignee_id not in self.allowed_assignee_ids:
            self.assignee_id = False

    @api.onchange('assignee_id')
    def _onchange_assignee_id(self):
        if self.plan_line_id and self.plan_line_id.plan_id.user_id != self.assignee_id:
            self.plan_line_id = False

    @api.depends('date_deadline', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for task in self:
            task.is_overdue = bool(task.date_deadline and task.state != 'done' and task.date_deadline < today)

    @api.depends('date_deadline', 'date_done', 'state')
    def _compute_is_on_time(self):
        for task in self:
            task.is_on_time = task.state == 'done' and (
                not task.date_deadline or (task.date_done and task.date_done.date() <= task.date_deadline))

    @api.depends_context('uid')
    @api.depends('review_user_id', 'assignee_id')
    def _compute_user_rights(self):
        is_manager = self.env.user.has_group('l10n_mn_hr.group_dev_task_manager')
        for task in self:
            task.is_reviewer = task.review_user_id == self.env.user
            task.is_assignee = task.assignee_id == self.env.user or is_manager

    # ------------------------------------------------------------------
    # Эрхийн шалгалт
    # ------------------------------------------------------------------
    def _is_manager(self):
        return self.env.user.has_group('l10n_mn_hr.group_dev_task_manager')

    def _check_assignee(self):
        for task in self:
            if task.assignee_id != self.env.user and not self._is_manager():
                raise UserError(_('%s даалгаврыг зөвхөн гүйцэтгэгч (%s) шилжүүлнэ.')
                                % (task.name, task.assignee_id.name or '-'))

    def _check_reviewer(self):
        for task in self:
            if task.review_user_id != self.env.user and not self._is_manager():
                raise UserError(_('%s даалгаврыг зөвхөн шалгах ажилтан (%s) шалгаж дуусгана.')
                                % (task.name, task.review_user_id.name))

    def _check_state(self, allowed):
        for task in self:
            if task.state not in allowed:
                raise UserError(_('%s даалгаврын төлөв энэ үйлдэлд тохирохгүй байна.') % task.name)

    # ------------------------------------------------------------------
    # Төлөвийн шилжилт
    # ------------------------------------------------------------------
    def action_start(self):
        """Шинэ -> Хийгдэж буй (гүйцэтгэгч). Гүйцэтгэгчгүй бол дарсан хүн гүйцэтгэгч болно."""
        self._check_state(['new'])
        self.filtered('assignee_id')._check_assignee()
        for task in self:
            vals = {'state': 'in_progress', 'date_start': fields.Datetime.now()}
            if not task.assignee_id:
                vals['assignee_id'] = self.env.user.id
            task.write(vals)

    def action_review(self):
        """Хийгдэж буй -> Шалгах (гүйцэтгэгч). Шалгах ажилтан өөр хүн бол имэйл илгээнэ."""
        self._check_state(['in_progress'])
        self._check_assignee()
        self.write({'state': 'review', 'date_review': fields.Datetime.now()})
        self._send_review_mail()

    def action_done(self):
        """Шалгах -> Дууссан (шалгах ажилтан, хоосон бол үүсгэсэн ажилтан)"""
        self._check_state(['review'])
        self._check_reviewer()
        self.write({'state': 'done', 'date_done': fields.Datetime.now()})

    def action_return(self):
        """Шалгах -> Хийгдэж буй: шалгах ажилтан засвар шаардаж буцаана."""
        self._check_state(['review'])
        self._check_reviewer()
        self.write({'state': 'in_progress', 'date_review': False})
        for task in self.filtered('assignee_id'):
            task.message_post(
                body=_('Даалгаврыг шалгаад засвар шаардаж буцаалаа.'),
                partner_ids=task.assignee_id.partner_id.ids,
                subtype_xmlid='mail.mt_comment',
            )

    def _send_review_mail(self):
        template = self.env.ref('l10n_mn_hr.mail_template_dev_task_review', raise_if_not_found=False)
        if not template:
            return
        for task in self:
            # Шалгах ажилтан болон даалгавар үүсгэсэн ажилтан руу; шалгуулж буй хүн өөрөө бол илгээхгүй
            recipients = (task.review_user_id | task.requester_id) - self.env.user
            no_email = recipients.filtered(lambda u: not u.email)
            recipients -= no_email
            if no_email:
                task.message_post(body=_('Анхааруулга: %s хэрэглэгчид имэйл хаяг бүртгэгдээгүй тул имэйл илгээгдсэнгүй.')
                                  % ', '.join(no_email.mapped('name')))
            if not recipients:
                continue
            # email_formatted биш: l10n_mn_sale нь бүх харилцагчийн email_formatted-ийг имэйл серверийн
            # хаяг (erp@...) болгодог тул хүлээн авагч бүгд тэр хаяг руу очиж байсан
            emails = ','.join(tools.formataddr((u.name or '', u.email)) for u in recipients)
            template.send_mail(task.id, force_send=True, email_values={'email_to': emails})
            task.message_post(body=_('"Шалгана уу" имэйлийг %s руу илгээлээ.') % ', '.join(recipients.mapped('email')))
