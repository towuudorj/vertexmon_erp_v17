{
    "name": "Tools",
    "summary": "Tools",
    "description": """Tools""",
    "version": "17.0.1.0.0",
    "category": "Tool",
    "website": "https://vertexmon.com",
    "author": "Vertexmon",
    "application": False,
    "installable": True,
    "depends": ["base", "hr"],
    "data": [
        'security/ir.model.access.csv',
        'data/microsoft_api_value_data.xml',
        'views/res_users_view.xml',
        'views/report_base_view.xml',
        'views/microsoft_api_value_view.xml',
        'views/user_role_view.xml',
        'views/user_setting_view.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vertexmon_tools/static/src/css/*.css'
        ]
    }
}
