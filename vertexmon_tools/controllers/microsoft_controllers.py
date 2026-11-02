# -*- coding: utf-8 -*-

import requests
from odoo.exceptions import UserError, ValidationError

TOKEN_TIMEOUT = 30  # секунд
REQUEST_TIMEOUT = 60  # секунд


class MicrosoftUnreachable(UserError):
    """Microsoft-той холбогдож чадсангүй (сүлжээ, DNS, хугацаа хэтэрсэн). Тохиргооны алдаа биш:
    дараа дахин оролдоход ихэвчлэн арилна."""


def get_token(microsoft_value_obj):
    microsoft_value_obj = microsoft_value_obj.sudo()

    CLIENT_ID = microsoft_value_obj.client_id
    CLIENT_SECRET = microsoft_value_obj.client_secret
    TENANT_ID = microsoft_value_obj.tenant_id
    if not (CLIENT_ID and CLIENT_SECRET and TENANT_ID):
        raise ValidationError(u'Microsoft API тохиргооны Tenant ID, Client ID, Client Secret бөглөгдөөгүй байна')

    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    try:
        res = requests.post(url, data=data, timeout=TOKEN_TIMEOUT)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise MicrosoftUnreachable(u'Microsoft-той холбогдож чадсангүй (сүлжээ / DNS / хугацаа хэтэрсэн). '
                                   u'Дараа дахин оролдоно уу.\n%s' % e) from e
    except requests.exceptions.RequestException as e:
        raise MicrosoftUnreachable(u'Microsoft руу хүсэлт илгээж чадсангүй.\n%s' % e) from e
    try:
        return res.json()
    except ValueError:
        raise ValidationError(u'Microsoft-оос буруу хариу ирлээ (HTTP %s):\n%s' % (res.status_code, res.text[:500]))


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
                res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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
                res = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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