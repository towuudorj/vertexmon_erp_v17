# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

MONTHS = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']


class AccountIncomePlan(models.Model):
    _name = 'account.income.plan'
    _description = 'Income report annual plan'
    _inherit = ['mail.thread']
    _order = 'year desc, id desc'

    name = fields.Char(string='Name', compute='_compute_name')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.company)
    year = fields.Integer(string='Year', required=True,
                          default=lambda self: fields.Date.today().year, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')],
                             string='State', default='draft', tracking=True)
    line_ids = fields.One2many('account.income.plan.line', 'plan_id', string='Lines', copy=True)

    _sql_constraints = [
        ('company_year_uniq', 'unique(company_id, year)',
         'The plan for this year already exists in this company!'),
    ]

    @api.depends('year', 'company_id')
    def _compute_name(self):
        for plan in self:
            plan.name = _('%(year)s annual plan', year=plan.year)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_draft(self):
        self.write({'state': 'draft'})


class AccountIncomePlanLine(models.Model):
    _name = 'account.income.plan.line'
    _description = 'Income report annual plan line'
    _order = 'income_type_id'

    plan_id = fields.Many2one('account.income.plan', string='Plan', required=True,
                              ondelete='cascade', index=True)
    company_id = fields.Many2one(related='plan_id.company_id', store=True)
    income_type_id = fields.Many2one('account.income.type', string='Income report type',
                                     required=True,
                                     domain="[('company_id', '=', company_id)]")
    m01 = fields.Float(string='January')
    m02 = fields.Float(string='February')
    m03 = fields.Float(string='March')
    m04 = fields.Float(string='April')
    m05 = fields.Float(string='May')
    m06 = fields.Float(string='June')
    m07 = fields.Float(string='July')
    m08 = fields.Float(string='August')
    m09 = fields.Float(string='September')
    m10 = fields.Float(string='October')
    m11 = fields.Float(string='November')
    m12 = fields.Float(string='December')
    q1 = fields.Float(string='Q1', compute='_compute_totals', store=True)
    q2 = fields.Float(string='Q2', compute='_compute_totals', store=True)
    q3 = fields.Float(string='Q3', compute='_compute_totals', store=True)
    q4 = fields.Float(string='Q4', compute='_compute_totals', store=True)
    year_total = fields.Float(string='Year total', compute='_compute_totals', store=True)

    _sql_constraints = [
        ('plan_income_type_uniq', 'unique(plan_id, income_type_id)',
         'This income report type is already in the plan!'),
    ]

    @api.depends(*['m%s' % m for m in MONTHS])
    def _compute_totals(self):
        for line in self:
            line.q1 = line.m01 + line.m02 + line.m03
            line.q2 = line.m04 + line.m05 + line.m06
            line.q3 = line.m07 + line.m08 + line.m09
            line.q4 = line.m10 + line.m11 + line.m12
            line.year_total = line.q1 + line.q2 + line.q3 + line.q4

    def get_planned(self, month_from, month_to):
        """Planned amount between the given months (1..12, inclusive)."""
        self.ensure_one()
        return sum(self['m%02d' % m] for m in range(month_from, month_to + 1))
