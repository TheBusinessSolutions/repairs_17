from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    product_id = fields.Many2one(
        domain="[('detailed_type', 'in', ['product', 'consu', 'service'])]"
    )