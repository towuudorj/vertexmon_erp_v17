
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
    transfering_position_id = fields.Many2one('hr.job', string='Transfering Position')
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

    decr_emp_contract = fields.Char('Contract Number')
    decr_trial_period = fields.Integer('Trial Period')
    decr_startdate = fields.Date('Start Date') #Огноо
    decr_guide_dep_id = fields.Many2one('hr.department', 'Guide Department')#Хэлтэс
    decr_guide_pos_id = fields.Many2one('hr.job', 'Guide Position')#Албан тушаал
    decr_guide_emp_id = fields.Many2one('hr.employee', 'Guide Employee')
    decr_day_off_wage = fields.Float(string='Day off wage')
    decr_day_off = fields.Integer(string='Day off')
    decr_reason = fields.Char('Reason')
    decr_is_wage = fields.Boolean('Is Wage')
    decr_amount = fields.Float(string='Amount')
    decr_enddate = fields.Date('End Date') #Огноо
    decr_taks_details = fields.Char('Task Details')
    decr_to_location = fields.Char('To Location')
    decr_department_id = fields.Many2one('hr.department', 'Department')#Хэлтэс
    decr_position_id = fields.Many2one('hr.job', 'Position')#Албан тушаал
    decr_employee_id = fields.Many2one('hr.employee', 'Employee')
    decr_partner_id = fields.Many2one('res.partner', 'Partner')#Харилцагч
    decr_date = fields.Date('Decree Date') #Огноо
    decr_quarter = fields.Char('Quarter')
    decr_location = fields.Char('Location')
    decr_is_wage_hour = fields.Boolean('Is Wage by Hour')
    decr_wage_hour = fields.Monetary('Wage by Hour', digits=(16, 2), tracking=True, 
                          help="Employee's hourly wage")
    decr_adv_month = fields.Date("Advance Month")
    decr_pay_month = fields.Date("Pay Month")
    decr_percentage = fields.Float(string="Хувь/%/",digits=(16, 2))
    decr_juram_zuil_number = fields.Char('Журам/Зүйлийн дугаар')
    decr_juram_zaalt_number = fields.Char('Журам/Заалтын дугаар')
    decr_geree_zuil_number = fields.Char('Гэрээ/Зүйлийн дугаар')
    decr_geree_zaalt_number = fields.Char('Гэрээ/Заалтын дугаар')
    decr_lastdate = fields.Date('Хүлээлцэх огноо') #Огноо

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

def verbose_format(amount,currency):
    u'''Мөнгөн дүнг үсгээр илэрхийлэх функц
    '''
    amount = str(amount)
    result = u''
    BUTARHAI = True
    i = 0
    stramount = amount.replace(',','.')
    
    if '-' in stramount:
        stramount= stramount.replace('-','')        
    if '.' in amount:
        amount = stramount[:stramount.find('.')]
        subamount = stramount[stramount.find('.')+1:]
    else :
        amount = stramount
        subamount = u''
    length = len(amount)
    if length == 0 or float(amount) == 0:
        return ''
    place = 0
    try :
        while i < length :
            c = length - i
            if c % 3 == 0 :
                c -= 3
            else :
                while c % 3 != 0 :
                    c -= 1
            place = c / 3
            i1 = length - c
            tmp = amount[i:i1]
            j = 0
            if tmp == '000' :
                i = i1
                continue
            while j < len(tmp) :
                char = int(tmp[j])
                p = len(tmp) - j
                if char == 1 :
                    if p == 3 :
                        result += u'нэг зуун '
                    elif p == 2 :
                        result += u'арван '
                    elif p == 1 :
                        if len(result)==0:
                            result += u'нэг '
                        else:
                            result += u'нэгэн '
                elif char == 2 :
                    if p == 3 :
                        result += u'хоёр зуун '
                    elif p == 2 :
                        result += u'хорин '
                    elif p == 1 :
                        result += u'хоёр '
                elif char == 3 :
                    if p == 3 :
                        result += u'гурван зуун '
                    elif p == 2 :
                        result += u'гучин '
                    elif p == 1 :
                        result += u'гурван '
                elif char == 4 :
                    if p == 3 :
                        result += u'дөрвөн зуун '
                    elif p == 2 :
                        result += u'дөчин '
                    elif p == 1 :
                        result += u'дөрвөн '
                elif char == 5 :
                    if p == 3 :
                        result += u'таван зуун '
                    elif p == 2 :
                        result += u'тавин '
                    elif p == 1 :
                        result += u'таван '
                elif char == 6 :
                    if p == 3 :
                        result += u'зургаан зуун ' 
                    elif p == 2 :
                        result += u'жаран '
                    elif p == 1 :
                        result += u'зургаан '
                elif char == 7 :
                    if p == 3 :
                        result += u'долоон зуун '
                    elif p == 2 :
                        result += u'далан '
                    elif p == 1 :
                        result += u'долоон '
                elif char == 8 :
                    if p == 3 :
                        result += u'найман зуун '
                    elif p == 2 :
                        result += u'наян '
                    elif p == 1 :
                        result += u'найман '
                elif char == 9 :
                    if p == 3 :
                        result += u'есөн зуун '
                    elif p == 2 :
                        result += u'ерэн '
                    elif p == 1 :
                        result += u'есөн '
                
                j += 1
            # -------- end while j < len(tmp)
            if place == 3 :
                result += u'тэрбум '
            elif place == 2 :
                result += u'сая '
            elif place == 1 :
                result += u'мянга '
            i = i1
        # ---------- end while i < len(amount)
    except Exception :
        return False
               
    return result

class HrTemplateCode(models.Model):
    _inherit = 'hr.decree'

    decree_template_code = fields.Char(
        related="decree_template.code",
        store=False
    )



class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def get_dep_name_mn(self):
        self.ensure_one()
        return self.with_context(lang='mn_MN').name

class HrPosition(models.Model):
    _inherit = 'hr.job'

    def get_job_name_mn(self):
        self.ensure_one()
        return self.with_context(lang='mn_MN').name
    
class HrDecree(models.Model):
    _inherit = 'hr.decree'

    decr_image = fields.Binary(
        string="Тушаалын зураг",
        attachment=True
    )

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_partner_name_mn(self):
        self.ensure_one()
        return self.with_context(lang='mn_MN').name

class HrDecree(models.Model):
    _name = "hr.decree"
    _inherit = "hr.decree"  # хэрэв оролцуулах бол

    decr_notes = fields.Text(string="Decree Notes")  # олон мөрт текст талбар

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def get_department_mn(self):
        self.ensure_one()
        return self.with_context(lang='mn_MN').department_id.name or ''

    def get_job_mn(self):
        self.ensure_one()
        return self.with_context(lang='mn_MN').job_id.name or ''

class HrDecreeReport(models.Model):
    _inherit = 'hr.decree'

    # Санхүү эрхэлсэн захирал
    chief_accountant_id = fields.Many2one(
        'hr.employee',
        string='Chief Accountant',
        compute='_compute_chief_accountant',
        store=False
    )

    @api.depends()
    def _compute_chief_accountant(self):
        chiefacc = self.env['hr.employee'].search([
            ('job_id.name', '=', 'Санхүү эрхэлсэн захирал')
        ], limit=1)
        for rec in self:
            rec.chief_accountant_id = chiefacc or False

    # Үйл ажиллагаа хариуцсан захирал
    chief_hresources_id = fields.Many2one(
        'hr.employee',
        string='Chief Human Resources',
        compute='_compute_chief_hresources',
        store=False
    )

    @api.depends()
    def _compute_chief_hresources(self):
        chiefhr = self.env['hr.employee'].search([
            ('job_id.name', '=', 'Үйл ажиллагаа хариуцсан захирал')
        ], limit=1)
        for rec in self:
            rec.chief_hresources_id = chiefhr or False

    # Гүйцэтгэх захирал
    executive_director_id = fields.Many2one(
        'hr.employee',
        string='Executive Director',
        compute='_compute_executive_director',
        store=False
    )

    @api.depends()
    def _compute_executive_director(self):
        for rec in self:
            exedirector = self.env['hr.employee'].search([
                ('job_id.name', '=', 'Гүйцэтгэх захирал')
            ], limit=1)
            rec.executive_director_id = exedirector or False

    # Accountant short name
    chief_acc_short_name = fields.Char(compute="_compute_chief_acc_short_name")

    def _compute_chief_acc_short_name(self):
        for rec in self:
            emp = rec.chief_accountant_id
            if emp:
                ln = emp.last_name or ''
                initial = ln[:1] + '. ' if ln else ''
                full = emp.name or ''
                first = full.split('.')[0]
                rec.chief_acc_short_name = initial + first
            else:
                rec.chief_acc_short_name = ''

    # HR short name
    chief_hr_short_name = fields.Char(compute="_compute_chief_hr_short_name")

    def _compute_chief_hr_short_name(self):
        for rec in self:
            emp = rec.chief_hresources_id
            if emp:
                ln = emp.last_name or ''
                initial = ln[:1] + '. ' if ln else ''
                full = emp.name or ''
                first = full.split('.')[0]
                rec.chief_hr_short_name = initial + first
            else:
                rec.chief_hr_short_name = ''

    # Director short name
    exe_director_short_name = fields.Char(compute="_compute_executive_director_short_name")

    def _compute_executive_director_short_name(self):
        for rec in self:
            emp = rec.executive_director_id
            if emp:
                ln = emp.last_name or ''
                initial = (ln[:1] + '. ').upper() if ln else ''
                full = emp.name or ''
                first = full.split('.')[0].upper()
                rec.exe_director_short_name = initial + first
            else:
                rec.exe_director_short_name = ''

    # Guide Emp short name
    guide_emp_short_name = fields.Char(compute="_compute_guide_emp_short_name")

    def _compute_guide_emp_short_name(self):
        for rec in self:
            emp = rec.decr_guide_emp_id
            if emp:
                ln = emp.last_name or ''
                initial = ln[:1] + '. ' if ln else ''
                full = emp.name or ''
                first = full.split('.')[0]
                rec.guide_emp_short_name = initial + first
            else:
                rec.guide_emp_short_name = ''

    # Цалингийн дүнг текстээр харуулах
    wage_amount_to_text = fields.Char(
        string='Wage Amount in Text',
        compute='_compute_wage_amount_to_text'
    )

    def _compute_wage_amount_to_text(self):
        for rec in self:
            if rec.wage:  # wage утга байгаа бол
                rec.wage_amount_to_text = verbose_format(rec.wage, rec.currency_id)
            else:  # wage хоосон бол хоосон string
                rec.wage_amount_to_text = ''

    # Цалингийн дүнг текстээр харуулах /Цагийн/
    wage_hour_amount_to_text = fields.Char(
        string='Wage Hour Amount in Text',
        compute='_compute_wage_hour_amount_to_text'
    )

    def _compute_wage_hour_amount_to_text(self):
        for rec in self:
            if rec.decr_wage_hour:  # wage_hour утга байгаа бол
                rec.wage_hour_amount_to_text = verbose_format(rec.decr_wage_hour, rec.currency_id)
            else:  # wage_hour хоосон бол хоосон string
                rec.wage_hour_amount_to_text = ''

    # Цалингийн дүнг текстээр харуулах
    food_and_vehicle_add_amount_to_text = fields.Char(
        string='Food and Vehicle add Amount in Text',
        compute='_compute_food_and_vehicle_add_amount_to_text'
    )

    def _compute_food_and_vehicle_add_amount_to_text(self):
        for rec in self:
            if rec.food_and_vehicle_add:  # food_and_vehicle_add утга байгаа бол
                rec.food_and_vehicle_add_amount_to_text = verbose_format(rec.food_and_vehicle_add, rec.currency_id)
            else:  # food_and_vehicle_add хоосон бол хоосон string
                rec.food_and_vehicle_add_amount_to_text = ''

    # Нэрийг Б.Цогтбаяр форматаар авах
    emp_short_name = fields.Char(compute="_compute_emp_short_name")

    def _compute_emp_short_name(self):
        for rec in self:
            emp = rec.employee_id
            if emp:
                ln = emp.last_name or ''
                initial = ln[:1] + '. ' if ln else ''
                full = emp.name or ''
                first = full.split('.')[0]
                rec.emp_short_name = initial + first
            else:
                rec.emp_short_name = ''

    # Ээлжийн амралтын хоног текстээр харуулах
    day_off_wage_to_text = fields.Char(
        string='Day off wage in Text',
        compute='_compute_day_off_wage_to_text'
    )

    def _compute_day_off_wage_to_text(self):
        for rec in self:
            if rec.decr_day_off_wage:  # decr_day_off_wage утга байгаа бол
                rec.day_off_wage_to_text = verbose_format(rec.decr_day_off_wage, rec.currency_id)
            else:  # decr_day_off_wage хоосон бол хоосон string
                rec.day_off_wage_to_text = ''

    # Мөнгөн дүнг текстээр харуулах
    decr_amount_to_text = fields.Char(
        string='Amount in Text',
        compute='_compute_decr_amount_to_text'
    )

    def _compute_decr_amount_to_text(self):
        for rec in self:
            if rec.decr_amount:  # decr_amount утга байгаа бол
                rec.decr_amount_to_text = verbose_format(rec.decr_amount, rec.currency_id)
            else:  # decr_amount хоосон бол хоосон string
                rec.decr_amount_to_text = ''

    # Нэрийг Б.Цогтбаяр форматаар авах
    decr_emp_short_name = fields.Char(compute="_compute_decr_emp_short_name", string="Товч нэр")

    def _compute_decr_emp_short_name(self):
        for rec in self:
            emp = rec.decr_employee_id  # сонгогдсон ажилтан
            if emp:
                ln = emp.last_name or ''
                initial = ln[:1] + '. ' if ln else ''
                full = emp.name or ''
                first = full.split('.')[0]  # нэрийн эхний хэсэг
                rec.decr_emp_short_name = initial + first
            else:
                rec.decr_emp_short_name = ''

    # Нэрийг Б.Цогтбаяр форматаар авах
    transfering_dep_emp_short_name = fields.Char(compute="_compute_transfering_dep_emp_short_name", string="Товч нэр")

    def _compute_transfering_dep_emp_short_name(self):
        for rec in self:
            emp = rec.transfering_department_id.manager_id  # сонгогдсон ажилтан
            if emp:
                ln = emp.last_name or ''
                initial = ln[:1] + '. ' if ln else ''
                full = emp.name or ''
                first = full.split('.')[0]  # нэрийн эхний хэсэг
                rec.transfering_dep_emp_short_name = initial + first
            else:
                rec.transfering_dep_emp_short_name = ''
