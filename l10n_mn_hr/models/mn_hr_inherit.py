# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError
import json, requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

DATE_FORMAT = "%Y-%m-%d"


class HrJob(models.Model):
    _inherit = 'hr.job'
    
    code = fields.Char(string='Code')
    

class Employee(models.Model):
    _inherit = "hr.employee"
    
    last_name = fields.Char(string='Last name')
    surname = fields.Char(string='Surname')
    khoroo_id = fields.Many2one('vat.district', string='Khoroo')
    bank_name = fields.Char(string='Bank Name', default='XAC')
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        groups="hr.group_hr_user",
        help='Employee bank salary account',required=False)
    tdd_number = fields.Char(string=u'Татвар төлөгчийн дугаар')
    register_number = fields.Char(string='Register number')
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user")
    education_id = fields.One2many('education','hr_employee_id',string='Education')
    training_course_id = fields.One2many('training.course','hr_employee_id',string='Training course')
    hr_language_id = fields.One2many('hr.language','hr_employee_id',string='Hr Language')
    computer_skill_id = fields.One2many('computer.skill','hr_employee_id',string='Computer skill')
    employment_id = fields.One2many('employment','hr_employee_id',string='Employment')
    employment_description = fields.Text('Employment description')
    other_program = fields.Text('Other program')
    live_people_id = fields.One2many('live.people','hr_employee_id',string='Live')
    hr_relationship_id = fields.One2many('hr.relationship','hr_employee_id',string='Hr relationship')
    other_use_skill = fields.Selection([('bad', 'Муу'),
                                        ('middle', 'Дунд'),
                                        ('good', 'Сайн'),
                                        ('best', 'Маш сайн')], string='Other use skill')
    driver_license = fields.Many2many('driver.type','hr_employee_id',string='Driver license')
    workplace_environment = fields.Selection([('normal', 'Normal'), 
                                        ('abnormal','Abnormal')] , string='Workplace environment', default='normal')
    abnormal_id = fields.Many2one('abnormal.register',string='Abnormal')
    disabled_employee = fields.Boolean(string='Employee with disability')
    disability_percentage = fields.Integer(string='Disability Percentage') #2025.01.31-нд нэмсэн шинэ талбар
    two_jobs = fields.Boolean(string='Currently employed by another company')
    company_name = fields.Char(string='Company') #2025.01.31-нд нэмсэн шинэ талбар
    accession_date = fields.Date('Accession date', required=True)#Ажилд орсон огноо
    employee_age = fields.Integer('Age')

    interestedly_job_id = fields.Many2many('hr.job',string='Interestedly job')
    workplace_id = fields.Many2one('workplace.register', string="Workplace")
    which_section = fields.Char(string='Which section') #Хэн, аль хэлтэст
    additional_information = fields.Text(string='Additional information') #Та өөрийнхөө талаар нэмэлт мэдээлэл байвал өгнө үү!
    is_judgemnet = fields.Selection([('yes', 'Yes'), 
                                        ('no', 'No')], string='Is judgement')
    judgemnet_desc = fields.Char(string='Judgement description') #Тайлбар
    
    notify_people_id = fields.One2many('notify.people','hr_employee_id',string='Notify people')
    hr_visit_id = fields.One2many('hr.visit','hr_employee_id',string='hr visit')
    hobby = fields.Text(string='Hobby')
    advantage_weaknesses_id = fields.One2many('advantage.weaknesses','hr_employee_id',string='Advantage weaknesses')
    art_sport_id = fields.One2many('art.sport','hr_employee_id',string='Art sport')
    hr_award_id = fields.One2many('hr.award','hr_employee_id',string='Hr award')
    residential_address = fields.Char(string='Residential address') #Оршин суугаа хаяг

    working_year = fields.Integer('Working year')#Байгууллагад ажиллаж буй жил
    working_year_month = fields.Integer('Working year month')#Байгууллагад ажиллаж буй сар
    working_year_other1 = fields.Integer('Working year other')#Бусад байгууллагад ажиллаж буй жил
    working_year_other1_month = fields.Integer('Working year other1 month')#Бусад байгууллагад ажиллаж буй сар
    working_year_other3 = fields.Integer('Working year other')#Бусад байгууллагад ажиллаж буй жил
    working_year_other3_month = fields.Integer('Working year other1 month')#Бусад байгууллагад ажиллаж буй сар
    
    working_year_company1 = fields.Integer('Working year company')
    working_year_company1_month = fields.Integer('Working year company month')#Компанид ажиллаж буй сар
    working_year_company4 = fields.Integer('Working year company')
    
    seniority = fields.Integer(string='Seniority')#Улсад ажилласан жил
    seniority_month = fields.Integer(string='Seniority month')#Улсад ажилласан сар

    maternity_leave_informatioin = fields.Boolean(string='Maternity leave informatioin')# Жирэмсний амралтын мэдээлэл
    maternity_leave_date = fields.Date(string='Maternity leave date')#Жирэмсний амралт
    
    maternity_year = fields.Integer('Maternity year')#Жирэмсний амралттай байсан жил
    maternity_year_month = fields.Integer('Maternity year month')#Жирэмсний амралттай байсан сар
    maternity_id = fields.One2many('maternity.leave.line','hr_employee_id',string='Maternity leave')
    show_maternity_info = fields.Boolean(string='Show Maternity Info')
    decree_id = fields.Many2one('hr.decree',string='Decree')#Тушаал
    emergency_contact_relation = fields.Selection([
        ('father','Father'),
        ('mother','Mother'),
        ('other','Other'),
    ], string='Emergency contact relation')
    emergency_relation_other = fields.Char(string='Specify relation')
    show_other_relation = fields.Boolean(string='Show Other Relation')

    decree_count = fields.Integer(compute='_compute_decree_count')
    contract_count = fields.Integer(compute='_compute_contract_count')

    attendance_id = fields.Integer('Attendance ID')

    def _compute_decree_count(self):
        for employee in self:
            employee.decree_count = self.env['hr.decree'].search_count([('employee_id', '=', employee.id)])

    def _compute_contract_count(self):
        for employee in self:
            employee.contract_count = self.env['hr.contract'].search_count([('employee_id', '=', employee.id)])

    def action_create_decree(self):
        return {
            'name': _('New Decree'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.decree',
            'view_mode': 'form',
            'context': {
                'default_employee_id': self.id,
                'default_job_id': self.job_id.id,
                'default_department_id': self.department_id.id,
            },
            'target': 'current',
        }

    def action_create_contract(self):
        action = self.env["ir.actions.actions"]._for_xml_id('hr_contract.action_hr_contract')
        action.update({'domain': [('employee_id', '=', self.id)],
                      'views':  [[False, 'list'], [False, 'kanban'], [False, 'activity'], [False, 'form']],
                       'context': {'default_employee_id': self.id,
                                   'default_job_id': self.job_id.id,
                                   'default_department_id': self.department_id.id,}})
        return action



    @api.onchange('emergency_contact_relation')
    def _onchange_emergency_contact_relation(self):
        for record in self:
            if record.emergency_contact_relation== 'other':
                record.show_other_relation = True
            else:
                record.show_other_relation = False


    def get_vat_code_check(self):
        register_number_check_url = 'https://api.ebarimt.mn/api/info/check/getTinInfo'
        if self.register_number:
            url = register_number_check_url + "?regNo="+self.register_number
            header = {
                    "Content-Type":"Application/json",                
                    }
            return_data = requests.request("get", url, headers = header)
            if return_data.status_code == 200:
                json_data = return_data.json()
                self.tdd_number = json_data['data']
            else:
                raise UserError(_(u'Регистрийн дугаар зөв оруулсан эсэхээ  шалгана уу.'))
        else:
            raise UserError(_(u'Регистрийн дугаар зөв оруулсан эсэхээ  шалгана уу.'))


    def compute_all_maternity(self):
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        for pr_emps in emp_ids:
            pr_emps.maternity_year2()
        return True
    
    def maternity_year2(self):
        res = {}
        line_month = 0.0
        line_year = 0.0
        maternity_year = 0.0
        wyo = 0
        wyo_other = 0
        for record in self:
            if record.maternity_id:
                for emp in record.maternity_id:
                    if emp.maternity_date_start != None:
                        a = int(str(emp.maternity_date_end)[0:4])
                        b = int(str(emp.maternity_date_start)[0:4])
                        c = int(str(emp.maternity_date_end)[5:7])
                        d = int(str(emp.maternity_date_start)[5:7])
                        if a == b and c > d:
                            line_month = c - d + 1
                        elif a > b and c > d:
                            line_year = (a - b) * 12
                            line_month = line_year + (c - d) + 1
                        elif a > b and c < d:
                            line_year = (a - b - 1) * 12
                            line_month = line_year + (c + 12 - d) + 1
                        elif a == b and c == d:
                            line_month = 1
                        elif a > b and c == d:
                            line_month = (a - b) * 12 + 1
                        else:
                            line_month = 0
                    else:
                        line_month = 0.0
                    
                    maternity_year += line_month
        if int(maternity_year / 12) > 0:
            wyo = int(maternity_year / 12)
            wyo_other = maternity_year - int(maternity_year / 12) * 12
        elif int(maternity_year / 12) == 0:
            wyo = 0
            wyo_other = maternity_year
        self.write({'maternity_year': wyo,
                    'maternity_year_month': wyo_other})
        return True
    
    @api.onchange('gender')
    def _onchange_gender(self):
        if self.gender == 'female':
            self.show_maternity_info = True
        else:
            self.show_maternity_info = False
    
    


    
    def compute_all_company(self):
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        for pr_emps in emp_ids:
            pr_emps.work_year_company2()
        return True
    
    def work_year_company2(self):
        res = {}
        line_month = 0.0
        line_year = 0.0
        work_year_company = 0.0
        wyo = 0
        wyo_other = 0
        our_month = 0
        working_year_company_all = 0.0
        for record in self:
            if record.employment_id:
                for emp in record.employment_id:
                    if emp.is_company == True:
                        a = int(str(emp.org_finish)[0:4])
                        b = int(str(emp.org_start)[0:4])
                        c = int(str(emp.org_finish)[5:7])
                        d = int(str(emp.org_start)[5:7])
                        if a == b and c > d:
                            line_month = c - d + 1
                        elif a > b and c > d:
                            line_year = (a - b) * 12
                            line_month = line_year + (c - d) + 1
                        elif a > b and c < d:
                            line_year = (a - b - 1) * 12
                            line_month = line_year + (c + 12 - d) + 1
                        elif a == b and c == d:
                            line_month = 1
                        elif a > b and c == d:
                            line_month = (a - b) * 12 + 1
                        else:
                            line_month = 0
                    else:
                        line_month = 0.0
                    
                    work_year_company += line_month
                    
                    our_month = self.working_year * 12 + self.working_year_month
                    working_year_company_all = work_year_company + our_month
                    
        if int(working_year_company_all / 12) > 0:
            wyo = int(working_year_company_all / 12)
            wyo_other = working_year_company_all - int(working_year_company_all / 12) * 12
        elif int(working_year_company_all / 12) == 0:
            wyo = 0
            wyo_other = working_year_company_all
            
        self.write({'working_year_company4': work_year_company,
                    'working_year_company1': wyo,
                    'working_year_company1_month': wyo_other})
        return True
    
    def compute_all_wyo(self):
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        for pr_emps in emp_ids:
            pr_emps.working_year_other2()
        return True
    
    def working_year_other2(self):
        res = {}
        line_month = 0.0
        line_year = 0.0
        working_year_others = 0.0
        working_year_others_company = 0.0
        wyo = 0
        wyo_other = 0
        wyo_company = 0
        wyo_other_compnay = 0
        for record in self:
            if record.employment_id:
                for emp in record.employment_id:
                    if emp.is_ndd == True:
                        a = int(str(emp.org_finish)[0:4])
                        b = int(str(emp.org_start)[0:4])
                        c = int(str(emp.org_finish)[5:7])
                        d = int(str(emp.org_start)[5:7])
                        if a == b and c > d:
                            line_month = c - d + 1
                        elif a > b and c > d:
                            line_year = (a - b) * 12
                            line_month = line_year + (c - d) + 1
                        elif a > b and c < d:
                            line_year = (a - b - 1) * 12
                            line_month = line_year + (c + 12 - d) + 1
                        elif a == b and c == d:
                            line_month = 1
                        elif a > b and c == d:
                            line_month = (a - b) * 12 + 1
                        else:
                            line_month = 0
                    else:
                        line_month = 0.0
                    
                    working_year_others += line_month
                    working_year_others_company = working_year_others - self.working_year_company4
        if int(working_year_others / 12) > 0:
            wyo = int(working_year_others / 12)
            wyo_other = working_year_others - int(working_year_others / 12) * 12
        elif int(working_year_others / 12) == 0:
            wyo = 0
            wyo_other = working_year_others
            
        if int(working_year_others_company / 12) > 0:
            wyo_compnay = int(working_year_others_company / 12)
            wyo_other_compnay = working_year_others_company - int(working_year_others_company / 12) * 12
        elif int(working_year_others_company / 12) == 0:
            wyo_compnay = 0
            wyo_other_compnay = working_year_others_company
        
            
        
        self.write({'working_year_other3': wyo,
                    'working_year_other3_month': wyo_other,
                    'working_year_other1': wyo_compnay,
                    'working_year_other1_month': wyo_other_compnay})
        return True
    
            
    def compute_all_wy_from_accession_date(self):
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        for pr_emps in emp_ids:
            pr_emps.sudo().compute_working_year_from_accession_date()
        return True
    
    def compute_working_year_from_accession_date(self):
        if self.accession_date:
            date_from = datetime.strptime(str(self.accession_date), DATE_FORMAT)
            date_to = datetime.today()
            diff = relativedelta(date_to, date_from)
            self.working_year = diff.years
            self.working_year_month = diff.months
        return True
    
    
            
    def compute_all_gs(self):
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        for pr_emps in emp_ids:
            pr_emps.get_seniority2()
        return True
    
    def get_seniority2(self):
        obj = self.browse()
        line_month = 0.0
        line_year = 0.0
        employment_month = 0
        our_month = 0
        ndd_month = 0.0
        
        sy = 0
        sy_other = 0
        
        employment_month = self.working_year_other3 * 12 + self.working_year_other3_month 
        our_month = self.working_year * 12 + self.working_year_month
        ndd_month = employment_month + our_month
            
        if int(ndd_month / 12) > 0:
            sy = int(ndd_month / 12)
            sy_other = ndd_month - int(ndd_month / 12) * 12
        elif int(ndd_month / 12) == 0:
            sy = 0
            sy_other = ndd_month
        self.write({'seniority': sy,
                    'seniority_month': sy_other})
        return True

    def compute_all_aa(self):
        emp_obj = self.env['hr.employee']
        emp_ids = emp_obj.search([('active', '=', True)])
        for pr_emps in emp_ids:
            pr_emps.autochange_age()
        return True
    
    def autochange_age(self):
        res = {}
        now_age = 0
        year = 0
        month = 0
        day = 0
        year1 = 0
        month1 = 0
        day1 = 0
        diff_year = 0
        diff_month = 0
        diff_day = 0
        if  self.birthday:
            date_from = datetime.strptime(str(self.birthday), DATE_FORMAT)
            date_to = datetime.today()
            diff = relativedelta(date_to, date_from)
            now_age = diff.years
        else:
            pass
        self.write({'employee_age': now_age})
        return True
    
class EmployeePublic(models.Model):
    _inherit = "hr.employee.public"
    
    last_name = fields.Char(string='Last name')
    surname = fields.Char(string='Surname')
    khoroo_id = fields.Many2one('vat.district', string='Khoroo')
    bank_name = fields.Char(string='Bank Name', default='XAC')
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        groups="hr.group_hr_user",
        help='Employee bank salary account',required=False)
    tdd_number = fields.Char(string=u'Татвар төлөгчийн дугаар')
    register_number = fields.Char(string='Register number')
    education_id = fields.One2many('education','hr_employee_id',string='Education')
    training_course_id = fields.One2many('training.course','hr_employee_id',string='Training course')
    hr_language_id = fields.One2many('hr.language','hr_employee_id',string='Hr Language')
    computer_skill_id = fields.One2many('computer.skill','hr_employee_id',string='Computer skill')
    employment_id = fields.One2many('employment','hr_employee_id',string='Employment')
    employment_description = fields.Text('Employment description')
    other_program = fields.Text('Other program')
    live_people_id = fields.One2many('live.people','hr_employee_id',string='Live')
    hr_relationship_id = fields.One2many('hr.relationship','hr_employee_id',string='Hr relationship')
    other_use_skill = fields.Selection([('bad', 'Муу'),
                                        ('middle', 'Дунд'),
                                        ('good', 'Сайн'),
                                        ('best', 'Маш сайн')], string='Other use skill')
    
    driver_license = fields.Many2many('driver.type','hr_employee_id',string='Driver license') # Жолооны үнэмлэхний ангилал
    workplace_environment = fields.Selection([('normal', 'Normal'), 
                                        ('abnormal', 'Abnormal')] , string='Workplace environment') #ажлын байрны нөхцөл
    abnormal_id = fields.Many2one('abnormal.register',string='Abnormal') 
    disabled_employee = fields.Boolean(string='Employee with disability') #Хөгжлийн бэрхшээлтэй эсэх
    disability_percentage = fields.Integer(string='Disability Percentage', related='employee_id.disability_percentage', compute_sudo=True)  # 2025.01.31-нд нэмсэн шинэ талбар
    two_jobs = fields.Boolean(string='Currently employed by another company') #Өөр компанид ажиллаж байгаа эсэх
    company_name = fields.Char(string='Company', related='employee_id.company_name', compute_sudo=True)  # 2025.01.31-нд нэмсэн шинэ талбар
    interestedly_job_id = fields.Many2many('hr.job',string='Interestedly job') #Сонирхож буй албан тушаал
    workplace_id = fields.Many2one('workplace.register', string="Workplace")
    which_section = fields.Char(string='Which section') #Хэн, аль хэлтэст
    additional_information = fields.Text(string='Additional information') #Та өөрийнхөө талаар нэмэлт мэдээлэл байвал өгнө үү!
    is_judgemnet = fields.Selection([('yes', 'Yes'), 
                                        ('no', 'No')])
    judgemnet_desc = fields.Char(string='Judgement description') #Тайлбар

    notify_people_id = fields.One2many('notify.people','hr_employee_id',string='Notify people')
    hr_visit_id = fields.One2many('hr.visit','hr_employee_id',string='hr visit')
    hobby = fields.Text(string='Hobby')
    advantage_weaknesses_id = fields.One2many('advantage.weaknesses','hr_employee_id',string='Advantage weaknesses')
    art_sport_id = fields.One2many('art.sport','hr_employee_id',string='Art sport')
    hr_award_id = fields.One2many('hr.award','hr_employee_id',string='Hr award')
    residential_address = fields.Char(string='Residential address') #Орчин суугаа хаяг
    accession_date = fields.Date('Accession date')#Ажилд орсон огноо
    employee_age = fields.Integer('Age')

    working_year = fields.Integer('Working year')#Байгууллагад ажиллаж буй жил
    working_year_month = fields.Integer('Working year month')#Байгууллагад ажиллаж буй сар
    working_year_other1 = fields.Integer('Working year other')#Бусад байгууллагад ажиллаж буй жил
    working_year_other1_month = fields.Integer('Working year other1 month')#Бусад байгууллагад ажиллаж буй сар
    working_year_other3 = fields.Integer('Working year other')#Бусад байгууллагад ажиллаж буй жил
    working_year_other3_month = fields.Integer('Working year other1 month')#Бусад байгууллагад ажиллаж буй сар
    
    working_year_company1 = fields.Integer('Working year company')
    working_year_company1_month = fields.Integer('Working year company month')#Компанид ажиллаж буй сар
    working_year_company4 = fields.Integer('Working year company')
    
    seniority = fields.Integer(string='Seniority')#Улсад ажилласан жил
    seniority_month = fields.Integer(string='Seniority month')#Улсад ажилласан сар

    maternity_leave_informatioin = fields.Boolean(string='Maternity leave informatioin')# Жирэмсний амралтын мэдээлэл
    maternity_leave_date = fields.Date(string='Maternity leave date')#Жирэмсний амралт
    
    maternity_year = fields.Integer('Maternity year')#Жирэмсний амралттай байсан жил
    maternity_year_month = fields.Integer('Maternity year month')#Жирэмсний амралттай байсан сар
    maternity_id = fields.One2many('maternity.leave.line','hr_employee_id',string='Maternity leave')
    show_maternity_info = fields.Boolean(string='Show Maternity Info')
    decree_id = fields.Many2one('hr.decree',string='Decree')#Тушаал
    emergency_contact_relation = fields.Selection([
        ('father','Father'),
        ('mother','Mother'),
        ('other','Other'),
    ], string='Emergency contact relation')
    emergency_relation_other = fields.Char(string='Specify relation')
    show_other_relation = fields.Boolean(string='Show Other Relation')

    decree_count = fields.Integer(compute='_compute_decree_count')
    contract_count = fields.Integer(compute='_compute_contract_count')
    attendance_id = fields.Integer('Attendance ID', related='employee_id.attendance_id', compute_sudo=True)



class maternity_leave_line(models.Model):
    _name = 'maternity.leave.line'
    _description = 'Maternity leave line'
    
    maternity_date_start = fields.Date(string='Date start')
    maternity_date_end = fields.Date(string='Date end')
    hr_employee_id = fields.Many2one('hr.employee', string='Employee')

class notify_people(models.Model):
    _name = 'notify.people'
    _description = 'notifies people'

    last_name = fields.Char(string='Last name')
    first_name = fields.Char(string='First  name')
    now_profession = fields.Char(string='Now profession')
    phone = fields.Char(string='Phone')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
    
class hr_visit(models.Model):
    _name = 'hr.visit'
    _description = 'hr visit'
    
    name = fields.Char(string='Name')
    went_time = fields.Char(string='Went time')
    went_vision = fields.Char(string='Went vision')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
    
class advantage_weaknesses(models.Model):
    _name = 'advantage.weaknesses'
    _description = 'advantage and weaknesses'
    
    advantage = fields.Char(string='Advantage')
    weaknesses = fields.Char(string='Weaknesses')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
    
class art_sport(models.Model):
    _name = 'art.sport'
    _description = 'art sport'
       
    sk_sport = fields.Char(string='Sk sport')
    sp_time = fields.Char(string='Sp time')
    is_award = fields.Char(string='Is award')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
    code = fields.Char(string='Code')
    
    
class hr_award(models.Model):
    _name = 'hr.award'
    _description = 'HR award'
    
    
    award_name = fields.Char(string='Award name')
    award_year = fields.Char(string='Award year')
    award_where = fields.Char(string='Where do awarded during')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    code = fields.Char(string='Code')

               
    


        
class driver_type(models.Model):
    _name = 'driver.type'
    _description = 'Driver type'
    
    company_id = fields.Many2one('res.company',string=u'Компани')
    name = fields.Char(string='Driver type')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
    code = fields.Char(string='Code')



class EducationDegree(models.Model):
    _name = 'hr.education.degree'
    _description = 'Education Degree'
    
    company_id = fields.Many2one('res.company',string=u'Компани')
    name = fields.Char('Education degree')
    code = fields.Char(string='Code')
           
    
    
class Education(models.Model):
    _name = 'education'
    _description = 'Education'
    
    graduate_school = fields.Char(string='Graduate school courses')
    where = fields.Char(string='Where')
    starting_year = fields.Date(string='Starting year')
    ending_year = fields.Date(string='Ending year')
    qualifications = fields.Char(string='Qualifications')
    occupation = fields.Char(string='Occupation')
    edu_rate = fields.Float(string='Edu rate')
    edu_percent = fields.Float(string='Percent')
    edu_payment_type = fields.Selection([('exhibition', 'Exhibition'),('credit', 'Credit'),('self', 'Self')], string='Payment type')
    type_id = fields.Many2one('hr.education.degree', string='Education degree')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')

    
    
    
class training_course(models.Model):
    _name = 'training.course'
    _description = 'Training course'

    where = fields.Char(string='Where')
    when = fields.Date(string='When')
    time = fields.Char(string='Time')
    training_profession = fields.Char(string='Training profession')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    code = fields.Char(string='Code')

    
    
class LanguageType(models.Model):
    _name = 'language.type'
    _description = 'Language type'
    
    company_id = fields.Many2one('res.company',string=u'Компани')
    name = fields.Char('Language type')
    code = fields.Char(string='Code')

    
class hr_language(models.Model):
    _name = 'hr.language'
    _description = 'HR language'
    
    name = fields.Many2one('language.type',string='Hr Language')
    lang_speak = fields.Selection([('bad', 'Муу'),('middle', 'Дунд'),('good', 'Сайн')], string='Speak')
    lang_listen = fields.Selection([('bad', 'Муу'), ('middle', 'Дунд'),('good', 'Сайн')], string='Listen')
    lang_translation = fields.Selection([('bad', 'Муу'), ('middle', 'Дунд'), ('good', 'Сайн')], string='Translation')
    lang_write = fields.Selection([('bad', 'Муу'), ('middle', 'Дунд'),('good', 'Сайн')], string='Write')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id =fields.Many2one('hr.applicant',string='Hr applicant')
    code = fields.Char(string='Code')

    
    
    
    
class employment(models.Model):
    _name = 'employment'
    _description = 'Employment'

    name = fields.Char(string='Organization')
    org_start = fields.Date(string='Start date')
    org_finish = fields.Date(string='End date')
    salary_size = fields.Float(string='Salary size')
    org_position = fields.Char(string='Position')
    work_schedule = fields.Char(string='Work schedule')
    org_reason = fields.Char('Reason')
    supervisor_name = fields.Char('Supervisor name')
    supervisor_phone = fields.Char('Supervisor phone')
    hr_employee_id = fields.Many2one('hr.employee','Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant','Hr applicant')
    
class ComputerType(models.Model):
    _name = 'hr.programm'
    _description = 'HR program'
    
    company_id = fields.Many2one('res.company',string=u'Компани')
    name = fields.Char('Programm name')
    code = fields.Char(string='Code')


class computer_skill(models.Model):
    _name = 'computer.skill'
    _description = 'Computer skill'

    name = fields.Many2one('hr.programm',string='Programm name')
    use_skill = fields.Selection([('bad', 'Муу'),('middle', 'Дунд'),('good', 'Сайн'),('best', 'Маш сайн')], string='Use skill')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
    code = fields.Char(string='Code')




class hr_relationship(models.Model):
    _name = 'hr.relationship'
    _description = 'HR relationship'
    
    who = fields.Char(string='Who')
    last_name = fields.Char(string='Last name')
    first_name = fields.Char(string='First name')
    age = fields.Integer(string='Age')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    work_organization = fields.Char(string='Work organization')
    position = fields.Char(string='Position')
    phone = fields.Char(string='Phone')
    salar = fields.Float(string='Salary')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')



class live_people(models.Model):
    _name = 'live.people'
    _description = 'Live people'
    
    who = fields.Char(string='Who')
    last_name = fields.Char(string='Last name')
    first_name = fields.Char(string='First name')
    age = fields.Integer(string='Age')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    work_organization = fields.Char(string='Work organization')
    position = fields.Char(string='Position')
    where = fields.Char(string=u'Where')
    phone = fields.Char(string='Phone')
    salary = fields.Float(string='Salary')
    hr_employee_id = fields.Many2one('hr.employee',string='Hr employee')
    hr_applicant_id = fields.Many2one('hr.applicant',string='Hr applicant')
