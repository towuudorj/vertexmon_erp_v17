# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo import tools
from odoo.exceptions import ValidationError


class EmployeeTransfer(models.Model):
    _name = 'employee.transfer'
    _description = 'Transfer Register'
    _inherit = ['mail.thread']
    
    name = fields.Char(string='№', readonly=True, 
                        default=lambda self: self.env['ir.sequence'].next_by_code('employee.transfer'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    from_company_id = fields.Many2one('res.company', string='From Company')
    to_company_id = fields.Many2one('res.company', string='To Company')
    from_department_id = fields.Many2one('hr.department', string='From Department')
    to_department_id = fields.Many2one('hr.department', string='To Department')
    transfer_date = fields.Date(string='Transfer Date', required=True)
    is_archived = fields.Boolean(string='Is Archived', default=False)
    note = fields.Text('Note')
    state = fields.Selection([
                            ('draft', 'Draft'),
                            ('transfered', 'Transfered'),
                            ('cancelled', 'Cancelled'),
                            ], 'State', default = 'draft', tracking=1)
    transfer_type = fields.Selection([
                            ('company', 'Company'),
                            ('department', 'Department'),
                            ('both', 'Company and Department'),
                            ], string='Transfer Type')
    department_id = fields.Many2one('hr.department', string='Department')
    transfer_decree_id = fields.Many2one('hr.decree', string='Transfer Decree')
    position_id = fields.Many2one('hr.job', string='Position')

    def action_create_decree(self):
        if not self.employee_id:
            raise ValidationError(_('Please select an employee!'))
        if self.transfer_type == 'company' and not self.to_company_id:
            raise ValidationError(_('Please select a target company for the transfer!'))
        if self.transfer_type == 'department' and not self.to_department_id:
            raise ValidationError(_('Please select a target department for the transfer!'))

        decree_vals = {
            'name': _('%s-н шилжилтийн тушаал') % self.employee_id.name,
            'date': fields.Date.today(),
            'employee_id': self.employee_id.id,
            'department_id': self.to_department_id.id if self.transfer_type == 'department' else self.employee_id.department_id.id,
            'decree_type': 'staff',
            'position_id': self.employee_id.job_id.id,
            'company_id': self.to_company_id.id if self.transfer_type == 'company' else self.employee_id.company_id.id,
            'transfer_id': self.id,
            'transfer_type': self.transfer_type,
        }
        new_decree = self.env['hr.decree'].create(decree_vals)
        self.transfer_decree_id = new_decree.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Transfer Decree'),
            'res_model': 'hr.decree',
            'view_mode': 'form',
            'res_id': new_decree.id,
            'target': 'current',
        }
        
    def action_draft(self):
        self.state = 'draft'
    
    def action_to_cancel(self):
        self.write({'state': 'cancelled'})
        return True
        
    def action_to_transfer(self):
        self.write({'state': 'transfered'})
        return True
    

    @api.model
    def create(self, vals): # Хамгийн сүүлд шилжсэн компанийг архивлах
        recent_transfer = self.search([
            ('employee_id', '=', vals['employee_id']),
            ('is_archived', '=', False)
        ], order='transfer_date desc', limit=1)
        
        if recent_transfer:
            recent_transfer.write({'is_archived': True})

        return super(EmployeeTransfer, self).create(vals)

    @api.model
    def get_transfer_history(self, employee_id): # Ажилтны шилжилтийн түүхийг харах
        transfers = self.search([
            ('employee_id', '=', employee_id)
        ], order='transfer_date')
        
        return transfers

    @api.model
    def get_recent_transfer_company(self, employee_id): # Тухайн ажилтны хамгийн сүүлд шилжсэн архивлагдаагүй компанийг үзүүлэх
        recent_transfer = self.search([
            ('employee_id', '=', employee_id),
            ('is_archived', '=', False)
        ], order='transfer_date desc', limit=1)
        
        if recent_transfer:
            return recent_transfer.to_company_id
        return None


    @api.onchange('employee_id')
    def onchange_employee_id(self):
        res = {}
        list = []
        if self.employee_id:
            if self.employee_id:
                res['employee_id'] = self.employee_id.id
                res['company_id'] = self.employee_id.company_id.id
                res['department_id'] = self.employee_id.department_id.id
                res['position_id'] = self.employee_id.job_id.id
        else:
            res['employee_id'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['position_id'] = False
            
        return {'value':res}
