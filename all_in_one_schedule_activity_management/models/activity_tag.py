
from odoo import fields, models
from random import randint


class ActivityTag(models.Model):
    """This class is used to create tags for activity"""
    _name = "activity.tag"
    _description = "Activity Tag"

    def _get_default_color(self):
        """to get colors for the tag"""
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True, translate=True,
                       help="Tag name")
    color = fields.Integer('Color', default=_get_default_color,
                           help="Tag color")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
