# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    # Override the field to extend the allowable types to 'service'
    product_id = fields.Many2one(
        'product.product', 
        string='Product to Repair',
        domain="[('type', 'in', ['product', 'consu', 'service']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True
    )

    @api.depends('product_id')
    def _compute_tracking(self):
        """ Ensure service products cleanly fallback to no tracking 
            to prevent constraints or lot requirements from blocking validation """
        super(RepairOrder, self)._compute_tracking()
        for repair in self:
            if repair.product_id and repair.product_id.type == 'service':
                repair.tracking = 'none'