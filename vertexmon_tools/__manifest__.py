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
    "depends": ["base"],
    "data": [
        'views/report_base_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vertexmon_tools/static/src/css/*.css'
        ]
    }
}
