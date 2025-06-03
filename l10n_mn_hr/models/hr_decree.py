
# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError, AccessError
from odoo import api, fields, models, SUPERUSER_ID, tools, _

class HrContract(models.Model):
    _inherit = "hr.contract"

    contract_number=fields.Char('Contract number')
    decree_id = fields.Many2one('hr.decree',string='Decree')
    decree_count = fields.Integer('Decree count', compute='_compute_decree_count')


    def _compute_decree_count(self):
        for rec in self:
            rec.decree_count = self.env['hr.decree'].search_count([('contract_id', '=', rec.id)])


    def action_to_decree(self, decree=False):
        if not decree:
            decrees = self.mapped('decree_id')
        action = self.env['ir.actions.actions']._for_xml_id('l10n_mn_hr.action_hr_decree')
        if len(decrees) > 1:
            action['domain'] = [('id', 'in', decrees.ids)]

        elif len(decrees) == 1:
            form_view = [(self.env.ref('l10n_mn_hr.hr_decree_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = decrees.id
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
    


    def action_create_decree(self):
        decree_obj = self.env['hr.decree']
        for line in self:
            decree_id = decree_obj.create({
                                'employee_id': line.employee_id.id,
                                'company_id': line.company_id.id,
                                'department_id': line.department_id.id,
                                'position_id': line.job_id.id,
                                'wage': line.wage,
                                'contract_id': line.id,
                                'phone_add': line.phone_add,})
            line.decree_id = decree_id.id
            


class HrDecreeCategory(models.Model):
    _name = 'hr.decree.category'
    _description = 'HR decree category'
    
    name = fields.Char(string=u'Decree category',required=True)
    company_id = fields.Many2one('res.company', string=u'Company', required=True,
                                 default=lambda self: self.env.user.company_id)

class hr_decree(models.Model):
    _name = 'hr.decree'
    _description = 'HR decree'
    _inherit = ['mail.thread']
    
    name = fields.Char('Decree summary')#Товч утга
    decree_number = fields.Char('Decree number', readonly=True)#Дугаар
    category_id = fields.Many2one('hr.decree.category',string=u'Decree category')
    date = fields.Date('Date')#Огноо
    decree_type = fields.Selection([
                            ('public', 'Public'),#Нийтэд гаргах тушаал
                            ('staff', 'Staff'),#Ажилчдад гаргах тушаал
                            ], string='Decree type') #Тушаалын төрөл
    employee_id = fields.Many2one('hr.employee', 'Employee')#Ажилтан
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.user.company_id)#Компани
    department_id = fields.Many2one('hr.department', 'Department')#Хэлтэс
    position_id = fields.Many2one('hr.job', 'Position')#Албан тушаал
    is_read_decree = fields.Boolean('Is read the Decree')#Тушаалтай танилцсан эсэх
    state = fields.Selection([
                            ('draft', 'Draft'),#Ноорог
                            ('approved', 'Approved'),#Батлагдсан
                            ('cancelled', 'Cancelled'),  # Цуцлагдсан
                            ], string='State', default = 'draft')
    notes = fields.Text('Notes')#Notes
    contract_id = fields.Many2one('hr.contract', string='Contract')
    contract_count = fields.Integer('Contract count', compute='_compute_contract_count')
    hr_employee_id = fields.Many2one('hr.employee', 'Employee')
    decree_template = fields.Many2one('decree.register.type', 'Decree Template')
    transfer_id = fields.Many2one('employee.transfer', string='Transfer')
    transfer_type = fields.Selection([
        ('company', 'Company'),
        ('department', 'Department'),
    ], string='Transfer Type')
    transfer_decree_id = fields.Many2one('hr.decree', string='Transfer Decree')
    transfering_department_id = fields.Many2one('hr.department', string='Transfering Department')
    transfering_company_id = fields.Many2one('res.company', string='Transfering Company')


    """ Цалингийн өөрчлөлт """
    is_salary_change = fields.Boolean('Is Salary Change', compute='_compute_is_salary_change', store=True)
    wage = fields.Monetary('Wage', digits=(16, 2), tracking=True, 
                          help="Employee's monthly gross wage")
    phone_add = fields.Float(string='Phone add')
    administration_add = fields.Float(string='Administration add')
    food_and_vehicle_add = fields.Float(string='Food and vehicle add')
    long_year_add = fields.Float(string='Long year add')
    health_insurance = fields.Float(string='Health insurance')
    accident_insurance = fields.Float(string='Accident insurance')
    voucher = fields.Float(string='Voucher')
    abnormal_add = fields.Float(string='Abnormal add')
    
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
        
    previous_wage = fields.Float('Previous Wage', readonly=True)
    is_transfer = fields.Boolean('Is Transfer Decree')
    

    @api.depends('decree_template')
    def _compute_is_salary_change(self):
            for record in self:
                record.is_salary_change = False



    @api.onchange('employee_id', 'is_salary_change')
    def _onchange_employee_salary(self):
        if self.employee_id and self.is_salary_change:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', 'in', ['open', 'draft'])
            ], limit=1)
            
            if contract:
                self.previous_wage = contract.wage
                self.wage = contract.wage
                
                if hasattr(contract, 'phone_add'):
                    self.phone_add = contract.phone_add
                if hasattr(contract, 'administration_add'):
                    self.administration_add = contract.administration_add
                if hasattr(contract, 'food_and_vehicle_add'):
                    self.food_and_vehicle_add = contract.food_and_vehicle_add
                if hasattr(contract, 'long_year_add'):
                    self.long_year_add = contract.long_year_add
                if hasattr(contract, 'health_insurance'):
                    self.health_insurance = contract.health_insurance
                if hasattr(contract, 'accident_insurance'):
                    self.accident_insurance = contract.accident_insurance
                if hasattr(contract, 'voucher'):
                    self.voucher = contract.voucher
                if hasattr(contract, 'abnormal_add'):
                    self.abnormal_add = contract.abnormal_add
    

    def apply_salary_changes(self):
        self.ensure_one()
        
        if not self.is_salary_change or not self.employee_id:
            return True
            
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['open', 'draft'])
        ], limit=1)
        
        if not contract:
            raise ValidationError(_("No active contract found for employee %s") % self.employee_id.name)
        
        contract.write({
            'wage': self.wage,
            'phone_add': self.phone_add,
            'administration_add': self.administration_add,
            'food_and_vehicle_add': self.food_and_vehicle_add,
            'long_year_add': self.long_year_add,
            'health_insurance': self.health_insurance, 
            'accident_insurance': self.accident_insurance,
            'voucher': self.voucher,
            'abnormal_add': self.abnormal_add,
        })
        
        msg = _("Salary updated through decree %s (%s):\n") % (self.name, self.decree_number or '')
        msg += _("- Base wage: %.2f → %.2f\n") % (self.previous_wage, self.wage)
        
        self.employee_id.message_post(
            body=msg,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        if not contract.decree_id:
            contract.decree_id = self.id
            
        return True

    

    def _get_report_base_filename(self):
        return self.name or 'Decree Report'
    
    
    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = self.env['hr.contract'].search_count([('decree_id', '=', rec.id)])


    def action_to_draft(self):
        self.write({'state': 'draft'})
        return True

    def action_to_cancel(self):
        self.write({'state': 'cancelled'})
        return True
    
    def action_to_approve(self):
        number = self.env['ir.sequence'].next_by_code('hr.decree')
        self.write({'state': 'approved',
                    'decree_number': number
                })
        return True

    def action_to_contract(self, contracts=False):
        if not contracts:
            contracts = self.mapped('contract_id')
        action = self.env['ir.actions.actions']._for_xml_id('hr_contract.action_hr_contract')
        if len(contracts) > 1:
            action['domain'] = [('id', 'in', contracts.ids)]

        elif len(contracts) == 1:
            form_view = [(self.env.ref('hr_contract.hr_contract_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = contracts.id
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
    
    @api.onchange('decree_type')
    def onchange_decree_type(self):
        res = {}
        if self.decree_type == 'public':
            res['employee_id'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['position_id'] = False
        return {'value':res}
    
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
                res['department_id'] = emp_id.department_id.id
                res['position_id'] = emp_id.job_id.id
        else:
            res['last_name'] = False
            res['company_id'] = False
            res['department_id'] = False
            res['position_id'] = False
            
        return {'value':res}
    
    def write(self, vals):
        
        if self.decree_type == 'staff':
            if 'is_read_decree' in vals:
                if self.employee_id.user_id.id != self.env.user.id:
                    raise ValidationError(_("Тухайн ажилтан зөвхөн өөрөө тушаалтай танилцсанаа тэмдэглэнэ !"))
                
        ifuser_hrmanager = self.env.user.has_group('hr.group_hr_manager')
        if ifuser_hrmanager == False:
            if 'name' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'decree_number' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'decree_type' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'date' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'user_ids' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'note' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'employee_id' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'company_id' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'department_id' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'position_id' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            if 'state' in vals:
                raise ValidationError(_("Зөвхөн хүний нөөцийн менежер эрхтэй хүн засах эрхтэй ! Та зөвхөн өөрийнхөө << Тушаалтай танилцсан эсэх >> - ийг л засч болно. Та хэрэгсэхгй дарж байгаад Засах дарж ороод << Тушаалтай танилцсан эсэх >> талбарыг засна уу !!!"))
            
            
        res = super(hr_decree, self).write(vals)
        return res
