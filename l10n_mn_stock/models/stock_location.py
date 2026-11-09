from odoo import models, fields


class Location(models.Model):
    _inherit = 'stock.location'

    supply_location = fields.Boolean('Is supply', default=False)
    supply_writeoff_location = fields.Boolean(
        'Хангамж актлах байрлал', default=False,
        help='Ажилтанд олгосон хангамжийг (буцаалтгүйгээр) хаах/актлах байрлал. '
             'Энэ байрлал руу орсон хөдөлгөөн хангамжийн тайланд ажилтны үлдэгдлээс хасагдана, '
             'агуулахын үлдэгдэлд нөлөөлөхгүй.')
    supply_transfer_location = fields.Boolean(
        'Хангамж шилжүүлэх байрлал', default=False,
        help='Ажилтнаас ажилтанд хангамж шилжүүлэх виртуал байрлал. Энэ байрлал руу орсон хөдөлгөөн '
             'хангамжийн тайланд "Өгөх ажилтан"-аас хасагдаж, хүлээн авах ажилтанд нэмэгдэнэ.')
