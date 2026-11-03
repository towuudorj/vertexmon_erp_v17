# -*- coding: utf-8 -*-
"""Хөрөнгө шилжүүлгийг олон хөрөнгө, ажилтан эзэмшигчтэй болгосон.

Хасагдсан asset_id/owner_id/quantity баганын NOT NULL-ийг авч, хуучин asset_id-г
шинэ Many2many руу post-migrate дээр хуулахаар хадгална.
"""


def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
         WHERE table_name = 'account_asset_move'
           AND column_name IN ('asset_id', 'owner_id', 'quantity')
    """)
    for (column,) in cr.fetchall():
        cr.execute('ALTER TABLE account_asset_move ALTER COLUMN "%s" DROP NOT NULL' % column)
