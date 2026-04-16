# -*- coding: utf-8 -*-

import requests
from odoo.exceptions import ValidationError


def get_token(microsoft_value_obj):
    microsoft_value_obj = microsoft_value_obj.sudo()

    CLIENT_ID = microsoft_value_obj.client_id
    CLIENT_SECRET = microsoft_value_obj.client_secret
    TENANT_ID = microsoft_value_obj.tenant_id

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    try:
        res = requests.post(url, data=data)
        return res.json()
    except:
        raise ValidationError(u'Шаарлагатай параметрүүд бөглөгдөөгүй, буруу байна')


def get_site_id(microsoft_value_obj, token):
    microsoft_value_obj = microsoft_value_obj.sudo()
    if microsoft_value_obj.site_id:
        return microsoft_value_obj.site_id
    else:
        if microsoft_value_obj.site_name and microsoft_value_obj.sharepoint_url:
            url = f"https://graph.microsoft.com/v1.0/sites/{microsoft_value_obj.sharepoint_url}:/sites/{microsoft_value_obj.site_name}"
            headers = {
                'Authorization': token,
            }
            try:
                res = requests.get(url, headers=headers)
                res = res.json()
                microsoft_value_obj.site_id = res.get('id')
                return res.get('id')
            except:
                raise ValidationError('Шаарлагатай параметрүүд буруу байна')
        else:
            raise ValidationError('Шаарлагатай параметрүүд бөглөгдөөгүй байна')

def get_list_id(microsoft_value_obj, site_id, token, list_name, list_id):
    microsoft_value_obj = microsoft_value_obj.sudo()
    if microsoft_value_obj[list_id]:
        return microsoft_value_obj[list_id]
    else:
        if microsoft_value_obj[list_name] and site_id:
            url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists"
            headers = {
                'Authorization': token,
            }
            try:
                res = requests.get(url, headers=headers)
                res = res.json()
                if res.get('value', False):
                    for val in res.get('value'):
                        if val.get('name', False) and val.get('name') == microsoft_value_obj[list_name]:
                            microsoft_value_obj[list_id] = val.get('id')
                            return val.get('id')
                raise ValidationError('Шаарлагатай параметрүүд буруу байна')
            except:
                raise ValidationError('Шаарлагатай параметрүүд буруу байна')
        else:
            raise ValidationError('Шаарлагатай параметрүүд бөглөгдөөгүй байна')