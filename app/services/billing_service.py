"""Billing service for invoice generation and PDF creation."""
import json
import os
from io import BytesIO
from datetime import datetime, timezone
from app.extensions import db
from app.models.bill import Bill
from app.models.restaurant import Restaurant


class BillingService:
    """Service for generating bills and PDF invoices."""
    
    @staticmethod
    def generate_bill(session):
        """Generate a combined bill for all orders in a session."""
        restaurant = Restaurant.query.first()
        orders = session.orders.all()
        
        # Calculate combined totals
        subtotal = sum(o.subtotal for o in orders)
        tax_amount = sum(o.tax_amount for o in orders)
        service_charge = sum(o.service_charge for o in orders)
        discount_amount = sum(o.discount_amount for o in orders)
        total_amount = sum(o.total_amount for o in orders)
        
        # Build bill data (snapshot of all order details)
        bill_data = {
            'orders': []
        }
        for order in orders:
            order_data = {
                'order_id': order.order_id,
                'items': [{
                    'name': item.item_name,
                    'quantity': item.quantity,
                    'unit_price': item.unit_price,
                    'line_total': item.line_total,
                    'is_veg': item.is_veg,
                } for item in order.items],
                'subtotal': order.subtotal,
                'total': order.total_amount,
            }
            bill_data['orders'].append(order_data)
        
        # Check if bill exists
        bill = session.bill
        if not bill:
            bill = Bill(session_id=session.id)
            db.session.add(bill)
        
        # Populate bill
        bill.restaurant_name = restaurant.name if restaurant else 'Restaurant'
        bill.restaurant_address = restaurant.address if restaurant else ''
        bill.restaurant_phone = restaurant.phone if restaurant else ''
        bill.restaurant_email = restaurant.email if restaurant else ''
        bill.restaurant_gst = restaurant.gst_number if restaurant else ''
        bill.token_number = session.token.token_number if session.token else 0
        bill.subtotal = subtotal
        bill.tax_percent = restaurant.tax_percent if restaurant else 10
        bill.tax_amount = tax_amount
        bill.service_charge_percent = restaurant.service_charge_percent if restaurant else 5
        bill.service_charge = service_charge
        bill.discount_amount = discount_amount
        bill.total_amount = total_amount
        bill.payment_status = 'paid'
        bill.bill_data = json.dumps(bill_data)
        
        db.session.commit()
        return bill
    
    @staticmethod
    def generate_pdf(bill):
        """Generate a professional PDF invoice for a bill."""
        from reportlab.lib.pagesizes import A4, mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
        from reportlab.lib.units import mm
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                               rightMargin=20*mm, leftMargin=20*mm,
                               topMargin=20*mm, bottomMargin=20*mm)
        
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'BillTitle', parent=styles['Heading1'],
            fontSize=18, alignment=1, spaceAfter=4*mm,
            textColor=colors.HexColor('#1a1a2e')
        )
        subtitle_style = ParagraphStyle(
            'BillSubtitle', parent=styles['Normal'],
            fontSize=10, alignment=1, textColor=colors.grey,
            spaceAfter=2*mm
        )
        normal_style = ParagraphStyle(
            'BillNormal', parent=styles['Normal'],
            fontSize=10, spaceAfter=1*mm
        )
        right_style = ParagraphStyle(
            'BillRight', parent=styles['Normal'],
            fontSize=10, alignment=2
        )
        bold_style = ParagraphStyle(
            'BillBold', parent=styles['Normal'],
            fontSize=11, spaceAfter=1*mm,
            textColor=colors.HexColor('#1a1a2e')
        )
        
        elements = []
        
        # Restaurant Header
        elements.append(Paragraph(bill.restaurant_name or 'Restaurant', title_style))
        if bill.restaurant_address:
            elements.append(Paragraph(bill.restaurant_address, subtitle_style))
        
        contact_parts = []
        if bill.restaurant_phone:
            contact_parts.append(f'Phone: {bill.restaurant_phone}')
        if bill.restaurant_email:
            contact_parts.append(f'Email: {bill.restaurant_email}')
        if contact_parts:
            elements.append(Paragraph(' | '.join(contact_parts), subtitle_style))
        
        if bill.restaurant_gst:
            elements.append(Paragraph(f'GST: {bill.restaurant_gst}', subtitle_style))
        
        elements.append(Spacer(1, 4*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        elements.append(Spacer(1, 4*mm))
        
        # Bill info
        elements.append(Paragraph(f'<b>Bill No:</b> {bill.bill_number}', normal_style))
        elements.append(Paragraph(f'<b>Token:</b> #{bill.token_number:02d}', normal_style))
        elements.append(Paragraph(f'<b>Date:</b> {bill.created_at.strftime("%d %b %Y, %I:%M %p")}', normal_style))
        elements.append(Spacer(1, 4*mm))
        
        # Items table
        bill_data = json.loads(bill.bill_data) if bill.bill_data else {'orders': []}
        
        table_data = [['Item', 'Qty', 'Price', 'Total']]
        
        for order_info in bill_data.get('orders', []):
            for item in order_info.get('items', []):
                table_data.append([
                    item['name'],
                    str(item['quantity']),
                    f"₹{item['unit_price']:.2f}",
                    f"₹{item['line_total']:.2f}",
                ])
        
        if len(table_data) > 1:
            table = Table(table_data, colWidths=[90*mm, 20*mm, 30*mm, 30*mm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            elements.append(table)
        
        elements.append(Spacer(1, 4*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        elements.append(Spacer(1, 3*mm))
        
        # Totals
        totals_data = [
            ['Subtotal', f'₹{bill.subtotal:.2f}'],
            [f'Tax ({bill.tax_percent}%)', f'₹{bill.tax_amount:.2f}'],
            [f'Service Charge ({bill.service_charge_percent}%)', f'₹{bill.service_charge:.2f}'],
        ]
        if bill.discount_amount > 0:
            totals_data.append(['Discount', f'-₹{bill.discount_amount:.2f}'])
        totals_data.append(['GRAND TOTAL', f'₹{bill.total_amount:.2f}'])
        
        totals_table = Table(totals_data, colWidths=[130*mm, 40*mm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#1a1a2e')),
        ]))
        elements.append(totals_table)
        
        elements.append(Spacer(1, 8*mm))
        elements.append(Paragraph('Thank you for dining with us!', subtitle_style))
        elements.append(Paragraph('We hope to see you again soon.', subtitle_style))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def get_bill_by_session(session_id):
        """Get bill for a session."""
        return Bill.query.filter_by(session_id=session_id).first()
