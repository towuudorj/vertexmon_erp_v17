# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_SHARED_CONTACT_SQL = """
    SELECT work_contact_id
      FROM hr_employee
     WHERE active IS TRUE AND work_contact_id IS NOT NULL
  GROUP BY work_contact_id
    HAVING COUNT(*) > 1
"""


def _shared_contact_ids(env):
    env.cr.execute(_SHARED_CONTACT_SQL)
    return [r[0] for r in env.cr.fetchall()]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    shared_work_contact = fields.Boolean(
        string='Ажлын контакт давхардсан', compute='_compute_shared_work_contact',
        search='_search_shared_work_contact')

    @api.depends('work_contact_id')
    def _compute_shared_work_contact(self):
        shared = set(_shared_contact_ids(self.env))
        for employee in self:
            employee.shared_work_contact = employee.work_contact_id.id in shared

    def _search_shared_work_contact(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError(_('Unsupported search operation'))
        positive = (operator == '=') == value
        return [('work_contact_id', 'in' if positive else 'not in', _shared_contact_ids(self.env))]

    @api.constrains('work_contact_id', 'active')
    def _check_unique_work_contact(self):
        for employee in self.filtered(lambda e: e.active and e.work_contact_id):
            other = self.sudo().with_context(active_test=True).search([
                ('work_contact_id', '=', employee.work_contact_id.id),
                ('id', '!=', employee.id),
            ], limit=1)
            if other:
                raise ValidationError(_(
                    'Ажлын контакт "%(contact)s" нь "%(other)s" ажилтанд аль хэдийн холбогдсон байна. '
                    'Ажилтан бүр өөр ажлын контактай байх ёстой.',
                    contact=employee.work_contact_id.display_name, other=other.name))


class ResPartner(models.Model):
    _inherit = 'res.partner'

    has_multiple_employees = fields.Boolean(
        string='Олон ажилтантай', compute='_compute_has_multiple_employees',
        search='_search_has_multiple_employees')

    def _compute_has_multiple_employees(self):
        shared = set(_shared_contact_ids(self.env))
        for partner in self:
            partner.has_multiple_employees = partner.id in shared

    def _search_has_multiple_employees(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise ValueError(_('Unsupported search operation'))
        positive = (operator == '=') == value
        return [('id', 'in' if positive else 'not in', _shared_contact_ids(self.env))]
