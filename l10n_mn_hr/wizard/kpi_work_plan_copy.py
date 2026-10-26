# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KpiWorkPlanCopy(models.TransientModel):
    """Ажлын төлөвлөгөөг шинэ хугацаанд хуулбарлах."""
    _name = 'kpi.work.plan.copy'
    _inherit = ['kpi.period.mixin']
    _description = 'Ажлын төлөвлөгөө хуулбарлах'

    plan_id = fields.Many2one('kpi.work.plan', 'Хуулах төлөвлөгөө', required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Ажилтан', required=True)
    copy_lines = fields.Boolean('Төлөвлөгөөт ажлуудыг хуулах', default=True)
    copy_extra = fields.Boolean('Бусад ажлын биелэлтийг хуулах', default=False,
                                help='Төлөвлөгөөнд тусгагдаагүй ажлуудыг шинэ төлөвлөгөөний төлөвлөгөөт ажил болгож хуулна.')
    shift_deadline = fields.Boolean('Хугацааг шинэ хугацаанд шилжүүлэх', default=True,
                                    help='Жишээ нь 3-р улирлаас 4-р улиралд хуулахад 9/30 хугацаа 12/30 болно.')
    line_count = fields.Integer('Хуулах мөрийн тоо', compute='_compute_line_count')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        plan = self.env['kpi.work.plan'].browse(res.get('plan_id') or self.env.context.get('active_id'))
        if not plan.exists():
            return res
        res['plan_id'] = plan.id
        res['employee_id'] = plan.employee_id.id
        res['period_type'] = plan.period_type
        # Анхны утга: дараагийн улирал / сар
        if plan.period_type == 'month' and plan.month:
            month, year = int(plan.month) + 1, plan.year
            if month > 12:
                month, year = 1, year + 1
            res.update(year=year, month=str(month))
        else:
            quarter, year = int(plan.quarter or 1) + 1, plan.year
            if quarter > 4:
                quarter, year = 1, year + 1
            res.update(year=year, quarter=str(quarter))
        return res

    @api.depends('plan_id', 'copy_lines', 'copy_extra')
    def _compute_line_count(self):
        for wiz in self:
            wiz.line_count = (len(wiz.plan_id.line_ids) if wiz.copy_lines else 0) + \
                             (len(wiz.plan_id.extra_line_ids) if wiz.copy_extra else 0)

    def _months_between(self, old_from, new_from):
        return (new_from.year - old_from.year) * 12 + (new_from.month - old_from.month)

    def action_copy(self):
        self.ensure_one()
        plan = self.plan_id
        if self.period_type == 'month' and not self.month:
            raise UserError(_('Сарыг сонгоно уу.'))
        delta = self._months_between(plan.date_from, self.date_from) if (
            self.shift_deadline and plan.date_from and self.date_from) else 0

        source_lines = self.env['kpi.work.plan.line']
        if self.copy_lines:
            source_lines |= plan.line_ids
        if self.copy_extra:
            source_lines |= plan.extra_line_ids
        line_vals = []
        for line in source_lines.sorted(lambda l: (l.is_extra, l.sequence, l.id)):
            deadline = line.date_deadline
            if deadline and delta:
                deadline += relativedelta(months=delta)
            line_vals.append((0, 0, {
                'sequence': line.sequence,
                'is_extra': False,
                'general_work': line.general_work,
                'name': line.name,
                'date_deadline': deadline,
            }))

        new_plan = self.env['kpi.work.plan'].create({
            'employee_id': self.employee_id.id,
            'period_type': self.period_type,
            'year': self.year,
            'quarter': self.quarter,
            'month': self.month,
            'line_ids': line_vals,
        })
        new_plan.message_post(body=_('%s төлөвлөгөөнөөс хуулбарлав.') % plan.name)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'kpi.work.plan',
            'res_id': new_plan.id,
            'view_mode': 'form',
            'target': 'current',
        }
