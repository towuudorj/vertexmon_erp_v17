# -*- coding: utf-8 -*-


def migrate(cr, version):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'account_asset_move' AND column_name = 'asset_id'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        INSERT INTO account_asset_move_asset_rel (move_id, asset_id)
        SELECT id, asset_id FROM account_asset_move WHERE asset_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)
    # Хуучин бүртгэлийн дугаар "/" байсан
    cr.execute("UPDATE account_asset_move SET name = 'ХШ/OLD/' || id WHERE name = '/'")
