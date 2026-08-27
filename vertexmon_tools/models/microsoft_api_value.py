from odoo import api, fields, models, _


class MicrosoftApiValue(models.Model):
    _name = 'microsoft.api.value'
    _description = 'Microsoft API value'

    name = fields.Char(default=u'Microsoft API Values')
    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret')
    tenant_id = fields.Char(string='Tenant ID')
    sharepoint_url = fields.Char(string='SharePoint URL')
    site_name = fields.Char(string='Site Name')
    site_id = fields.Char(string='Site ID')
    employee_list_name = fields.Char(string='Employee List Name')
    employee_list_id = fields.Char(string='Employee List ID')
    attendance_list_name = fields.Char(string='Attendance List Name')
    attendance_list_id = fields.Char(string='Attendance List ID')
    job_list_name= fields.Char(string='Job List Name')
    job_list_id = fields.Char(string='Job List ID')
    department_list_name= fields.Char(string='Department List Name')
    department_list_id = fields.Char(string='Department List ID')
    leave_list_name = fields.Char(string='Leave List Name')
    leave_list_id = fields.Char(string='Leave List ID')
    partner_list_name = fields.Char(string='Partner List Name')
    partner_list_id = fields.Char(string='Partner List ID')
    payment_list_name = fields.Char(string='Payment List Name')
    payment_list_id = fields.Char(string='Payment List ID')
    company_account_list_name = fields.Char(string='Company account List Name')
    company_account_list_id = fields.Char(string='Company account List Name')
    att_edit_req_list_name = fields.Char(string='Attendance edit Request')
    att_edit_req_list_id = fields.Char(string='Attendance edit Request')

    def write(self, vals):
        for key, value in list(vals.items()):
            if vals.get(key):
                if '_name' in key:
                    vals[key.replace('_name', '_id')] = False
        return super(MicrosoftApiValue, self).write(vals)
