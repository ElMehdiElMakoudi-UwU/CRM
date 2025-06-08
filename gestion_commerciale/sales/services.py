from django.db.models import Sum, Q
from django.utils import timezone
from datetime import date
from calendar import monthrange
from decimal import Decimal

from .models import Sale
from pos.models import POSReceipt, POSLineItem
from mobile_pos.models import Order

class UnifiedSalesService:
    @staticmethod
    def get_monthly_sales(year, month):
        # Créer la date de début et de fin du mois
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        # Récupérer les ventes directes
        direct_sales = Sale.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date
        ).select_related('client')
        
        # Récupérer les ventes POS avec leurs lignes
        pos_sales = POSReceipt.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).select_related('client', 'cashier').prefetch_related('items', 'items__product')
        
        # Calculer le total des ventes POS et agréger les lignes par produit
        pos_totals = pos_sales.aggregate(
            total_amount=Sum('total'),
            total_paid=Sum('paid')
        )
        
        # Créer une seule entrée consolidée pour toutes les ventes POS du mois
        if pos_totals['total_amount']:
            # Agréger les lignes POS par produit
            pos_items_by_product = {}
            for receipt in pos_sales:
                for item in receipt.items.all():
                    product_name = item.product.name
                    if product_name not in pos_items_by_product:
                        pos_items_by_product[product_name] = {
                            'product': product_name,
                            'quantity': 0,
                            'total': Decimal('0'),
                            'unit_price': Decimal('0')
                        }
                    pos_items_by_product[product_name]['quantity'] += item.quantity
                    item_total = item.quantity * item.unit_price
                    pos_items_by_product[product_name]['total'] += item_total
            
            # Calculer le prix unitaire moyen pour chaque produit
            for item in pos_items_by_product.values():
                if item['quantity'] > 0:
                    item['unit_price'] = item['total'] / item['quantity']
            
            # Créer un datetime aware pour la fin du mois
            end_datetime = timezone.make_aware(
                timezone.datetime.combine(end_date, timezone.datetime.min.time())
            )
            
            unified_pos_sale = {
                'date': end_datetime,
                'client': "Ventes POS consolidées",
                'total_amount': pos_totals['total_amount'],
                'amount_paid': pos_totals['total_paid'],
                'is_credit': pos_totals['total_paid'] < pos_totals['total_amount'],
                'source': 'pos_consolidated',
                'id': f"{year}{month:02d}",  # ID unique basé sur l'année et le mois
                'detail_url': '#',
                'items': list(pos_items_by_product.values())  # Ajouter les lignes agrégées
            }
        else:
            unified_pos_sale = None
        
        # Récupérer les ventes Mobile POS
        mobile_sales = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).prefetch_related('items', 'items__product')
        
        # Calculer les totaux
        direct_totals = direct_sales.aggregate(
            total_amount=Sum('total_amount'),
            total_paid=Sum('amount_paid')
        )
        
        # Pour le Mobile POS, le total_amount est le seul champ nécessaire car il est toujours payé
        mobile_totals = mobile_sales.aggregate(
            total_amount=Sum('total_amount')
        )
        mobile_totals['total_paid'] = mobile_totals['total_amount']  # Toujours payé intégralement
        
        # Agréger les totaux
        total_amount = (
            (direct_totals['total_amount'] or 0) +
            (pos_totals['total_amount'] or 0) +
            (mobile_totals['total_amount'] or 0)
        )
        
        total_paid = (
            (direct_totals['total_paid'] or 0) +
            (pos_totals['total_paid'] or 0) +
            (mobile_totals['total_paid'] or 0)
        )
        
        # Préparer les données de vente unifiées
        unified_sales = []
        
        # Ajouter les ventes directes
        for sale in direct_sales:
            # S'assurer que la date est timezone-aware
            if timezone.is_naive(sale.date):
                sale_date = timezone.make_aware(sale.date)
            else:
                sale_date = sale.date
                
            unified_sales.append({
                'date': sale_date,
                'client': sale.client.name if sale.client else "Client anonyme",
                'total_amount': sale.total_amount,
                'amount_paid': sale.amount_paid,
                'is_credit': sale.is_credit,
                'source': 'direct',
                'id': sale.id,
                'detail_url': f'/sales/{sale.id}/',
                'items': [
                    {
                        'product': item.product.name,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'total': item.total_price
                    }
                    for item in sale.items.all()
                ]
            })
        
        # Ajouter la vente POS consolidée si elle existe
        if unified_pos_sale:
            unified_sales.append(unified_pos_sale)
        
        # Ajouter les ventes Mobile POS
        for sale in mobile_sales:
            # S'assurer que created_at est timezone-aware
            if timezone.is_naive(sale.created_at):
                sale_date = timezone.make_aware(sale.created_at)
            else:
                sale_date = sale.created_at
                
            unified_sales.append({
                'date': sale_date,
                'client': sale.client_name or "Client anonyme",
                'total_amount': sale.total_amount,
                'amount_paid': sale.total_amount,
                'is_credit': False,
                'source': 'mobile',
                'id': sale.id,
                'detail_url': f'/mobile-pos/orders/{sale.id}/',
                'items': [
                    {
                        'product': item.product.name,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'total': item.subtotal
                    }
                    for item in sale.items.all()
                ]
            })
        
        # Trier toutes les ventes par date
        unified_sales.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'sales': unified_sales,
            'totals': {
                'total_amount': total_amount,
                'total_paid': total_paid,
                'count': len(unified_sales)
            }
        }

    @staticmethod
    def prepare_sale_for_pdf(sale_data):
        """
        Prepare sale data for PDF generation.
        """
        if sale_data['source'] == 'direct':
            # Pour les ventes directes
            sale = Sale.objects.prefetch_related('items', 'items__product').get(id=sale_data['id'])
            items = [{
                'product': item.product.name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total': item.total_price
            } for item in sale.items.all()]
            
        elif sale_data['source'] == 'pos_consolidated':
            # Pour les ventes POS consolidées
            pos_sales = POSReceipt.objects.filter(
                created_at__date__year=sale_data['date'].year,
                created_at__date__month=sale_data['date'].month
            ).prefetch_related('items', 'items__product')
            
            # Agréger les lignes par produit
            items_by_product = {}
            for receipt in pos_sales:
                for item in receipt.items.all():
                    product_name = item.product.name
                    if product_name not in items_by_product:
                        items_by_product[product_name] = {
                            'product': product_name,
                            'quantity': 0,
                            'total': Decimal('0')
                        }
                    items_by_product[product_name]['quantity'] += item.quantity
                    items_by_product[product_name]['total'] += item.quantity * item.unit_price
            
            # Calculer le prix unitaire moyen
            items = []
            for item_data in items_by_product.values():
                if item_data['quantity'] > 0:
                    items.append({
                        'product': item_data['product'],
                        'quantity': item_data['quantity'],
                        'unit_price': item_data['total'] / item_data['quantity'],
                        'total': item_data['total']
                    })
            
        else:
            # Pour les ventes Mobile POS
            order = Order.objects.prefetch_related('items', 'items__product').get(id=sale_data['id'])
            items = [{
                'product': item.product.name,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'total': item.subtotal
            } for item in order.items.all()]
        
        # Create the sale context with items included
        sale_context = {
            'id': sale_data['id'],
            'date': sale_data['date'],
            'client': sale_data['client'],
            'total_amount': sale_data['total_amount'],
            'amount_paid': sale_data['amount_paid'],
            'source': sale_data['source'],
            'items': items,
            'cashier': sale_data.get('cashier', None)
        }
        
        return sale_context

    @staticmethod
    def generate_monthly_invoices_pdf(year, month, company=None):
        """Génère un PDF contenant toutes les factures du mois."""
        from django.template.loader import get_template
        from reportlab.platypus import SimpleDocTemplate, PageBreak
        from reportlab.lib.pagesizes import A4
        import io
        from xhtml2pdf import pisa
        from django.template import Context
        
        # Obtenir toutes les ventes du mois
        sales_data = UnifiedSalesService.get_monthly_sales(year, month)
        
        # Créer le PDF
        buffer = io.BytesIO()
        
        # Obtenir le template
        template = get_template('sales/unified_invoice_pdf.html')
        
        # Pour chaque vente, générer une page de facture
        all_pages = []
        for sale_data in sales_data['sales']:
            # Préparer les données pour le template
            sale_context = UnifiedSalesService.prepare_sale_for_pdf(sale_data)
            
            # Créer le contexte pour le template
            context = {
                'sale': sale_context,
                'company': company
            }
            
            # Générer le HTML pour cette facture
            html = template.render(context)
            
            # Ajouter au buffer
            if all_pages:  # Si ce n'est pas la première page, ajouter un saut de page
                all_pages.append('<div style="page-break-before: always;"></div>')
            all_pages.append(html)
        
        # Combiner toutes les pages
        final_html = ''.join(all_pages)
        
        # Convertir en PDF
        pisa.CreatePDF(final_html, dest=buffer)
        
        # Retourner le buffer
        buffer.seek(0)
        return buffer 