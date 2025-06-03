# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    workplace_id = fields.Many2one('workplace.register', string="Workplace")
    surname = fields.Char(string='Surname', required=True)
    attendance = fields.Boolean(string='Attended?')
    date = fields.Date('Date')
    meeting_type = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
    ], string='Meeting type', required=True)
    refuse_reason = fields.Many2one('hr.applicant.refuse.reason', string="Refuse Reason")



    def _get_employee_create_vals(self):
        self.ensure_one()
        address_id = self.partner_id.address_get(['contact'])['contact']
        address_sudo = self.env['res.partner'].sudo().browse(address_id)
        return {
            'name': self.partner_name or self.partner_id.display_name,
            'work_contact_id': self.partner_id.id,
            'job_id': self.job_id.id,
            'job_title': self.job_id.name,
            'private_street': address_sudo.street,
            'private_street2': address_sudo.street2,
            'private_city': address_sudo.city,
            'private_state_id': address_sudo.state_id.id,
            'private_zip': address_sudo.zip,
            'private_country_id': address_sudo.country_id.id,
            'private_phone': address_sudo.phone,
            'lang': address_sudo.lang,
            'department_id': self.department_id.id,
            'last_name':self.surname,
            'address_id': self.company_id.partner_id.id,
            'work_email': self.department_id.company_id.email or self.email_from, # To have a valid email address by default
            'work_phone': self.department_id.company_id.phone,
            'applicant_id': self.ids,
            'private_phone': self.partner_phone or self.partner_mobile,
            'private_email': self.email_from,
            'accession_date': self.date_closed
        }

    
    def action_contract(self):
            contract_obj = self.env['hr.contract']
            for line in self:
                print('line.partner_id', line.employee_id.id)
                contract_id = contract_obj.search([('employee_id', '=', line.employee_id.id)])
                if contract_id:
                    raise UserError(_('Contract already exists for this employee.'))
                contract_vals = {
                    'name': _('Contract for %s') % line.partner_name,
                    'employee_id': line.employee_id.id,
                    'job_id': line.job_id.id,
                    'department_id': line.department_id.id,
                    'state': 'draft',
                    'wage': 0.0,
                }
                new_contract = contract_obj.create(contract_vals)
                
            return {
                'type': 'ir.actions.act_window',
                'name': _('Contract'),
                'res_model': 'hr.contract',
                'view_mode': 'form',
                'res_id': new_contract.id,
                'target': 'current',
            }