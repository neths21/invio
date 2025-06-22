from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_login import login_required, current_user
from app.models.models import (
    Product, Category, Supplier, InventoryTransaction, 
    Notification, PurchaseOrder, PurchaseOrderItem
)
from app.controllers.forms import (
    ProductForm, CategoryForm, SupplierForm, 
    InventoryTransactionForm, PurchaseOrderForm
)
from app.services.ai_service import AIService
from app.services.chatbot_service import ChatbotService
from app import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, desc
import pandas as pd
import json
from collections import defaultdict
from PIL import Image
from io import BytesIO
from pyzbar.pyzbar import decode
import base64
from app.services.barcode_service import decode_dataurl_to_barcode_text
from app.services.analysis_service import AnalysisService
from app.services.email_service import EmailService
from flask import current_app

inventory_bp = Blueprint('inventory', __name__)
ai_service = AIService()
chatbot_service = ChatbotService()

# Product routes
@inventory_bp.route('/products')
@login_required
def products():
    # Get filter parameter if provided
    category_id = request.args.get('category_id', type=int)
    
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of items per page
    
    # Base query
    query = Product.query
    
    # Filter products by category if category_id is provided
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Get paginated products
    paginated_products = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Get all categories for the filter dropdown
    categories = Category.query.all()
    
    return render_template('inventory/products.html', 
                          products=paginated_products.items, 
                          pagination=paginated_products,
                          categories=categories, 
                          category_id=category_id)

@inventory_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    
    # Populate choices for category and supplier
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    
    if form.validate_on_submit():
        # 1) Try to decode camera‐captured image via our service
        raw_b64 = request.form.get("barcode_image_data", None)
        if raw_b64:
            try:
                decoded_text = decode_dataurl_to_barcode_text(raw_b64)
                if decoded_text:
                    form.sku.data = decoded_text
                else:
                    flash("No barcode detected in the captured image.", "warning")
            except ValueError as e:
                flash(f"Barcode decoding error: {e}", "danger")
        

        # 2) Now proceed as before, using form.sku.data (either user‐typed or decoded)
        try:
            product = Product(
                name=form.name.data,
                description=form.description.data,
                sku=form.sku.data,
                unit_price=form.unit_price.data,
                quantity_in_stock=form.quantity_in_stock.data,
                reorder_level=form.reorder_level.data,
                reorder_quantity=form.reorder_quantity.data,
                category_id=form.category_id.data,
                supplier_id=form.supplier_id.data
            )

            db.session.add(product)
            db.session.commit()

            # Create initial inventory transaction if needed (unchanged)…
            if form.quantity_in_stock.data > 0:
                transaction = InventoryTransaction(
                    product_id=product.id,
                    transaction_type="purchase",
                    quantity=form.quantity_in_stock.data,
                    unit_price=form.unit_price.data,
                    total_price=form.unit_price.data * form.quantity_in_stock.data,
                    notes=f"Initial inventory for {form.name.data}",
                    created_by=current_user.id
                )
                db.session.add(transaction)
                db.session.commit()

            flash("Product added successfully", "success")
            return redirect(url_for("inventory.products"))

        except IntegrityError:
            db.session.rollback()
            flash("A product with this SKU already exists. Please enter a unique SKU.", "danger")
            return render_template("inventory/product_form.html", form=form, title="Add Product")

    return render_template("inventory/product_form.html", form=form, title="Add Product")

@inventory_bp.route('/products/<int:product_id>')
@login_required
def view_product(product_id):
    product = Product.query.get_or_404(product_id)
    transactions = InventoryTransaction.query.filter_by(product_id=product_id).order_by(InventoryTransaction.transaction_date.desc()).all()
    
    # Get product analysis from AI
    product_analysis = ai_service.analyze_inventory_trends(product, transactions)
    
    return render_template(
        'inventory/product_details.html', 
        product=product, 
        transactions=transactions, 
        analysis=product_analysis
    )

@inventory_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    # Set product_id for the custom validator
    form.product_id = product_id
    
    # Populate choices for category and supplier
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    
    if form.validate_on_submit():
        try:
            # Check if quantity has changed
            old_quantity = product.quantity_in_stock
            new_quantity = form.quantity_in_stock.data
            
            # Update product
            product.name = form.name.data
            product.description = form.description.data
            product.sku = form.sku.data
            product.unit_price = form.unit_price.data
            product.quantity_in_stock = new_quantity
            product.reorder_level = form.reorder_level.data
            product.reorder_quantity = form.reorder_quantity.data
            product.category_id = form.category_id.data
            product.supplier_id = form.supplier_id.data
            
            # Create adjustment transaction if quantity changed
            if old_quantity != new_quantity:
                adjustment = new_quantity - old_quantity
                
                transaction = InventoryTransaction(
                    product_id=product.id,
                    transaction_type='adjustment',
                    quantity=abs(adjustment),
                    unit_price=form.unit_price.data,
                    total_price=form.unit_price.data * abs(adjustment),
                    notes=f"Manual adjustment: {'increased' if adjustment > 0 else 'decreased'} by {abs(adjustment)}",
                    created_by=current_user.id
                )
                db.session.add(transaction)
            
            db.session.commit()
            flash('Product updated successfully', 'success')
            return redirect(url_for('inventory.products'))
        except IntegrityError:
            db.session.rollback()
            flash('A product with this SKU already exists. Please enter a unique SKU.', 'danger')
            return render_template('inventory/product_form.html', form=form, product=product, title='Edit Product')
    
    return render_template('inventory/product_form.html', form=form, product=product, title='Edit Product')

@inventory_bp.route('/products/<int:product_id>/delete', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Delete associated transactions and notifications
    InventoryTransaction.query.filter_by(product_id=product_id).delete()
    Notification.query.filter_by(product_id=product_id).delete()
    
    db.session.delete(product)
    db.session.commit()
    
    flash('Product deleted successfully', 'success')
    return redirect(url_for('inventory.products'))

@inventory_bp.route('/api/products/<int:product_id>')
@login_required
def get_product_info(product_id):
    product = Product.query.get_or_404(product_id)
    
    product_data = {
        'id': product.id,
        'name': product.name,
        'sku': product.sku,
        'unit_price': product.unit_price,
        'quantity_in_stock': product.quantity_in_stock,
        'reorder_level': product.reorder_level,
        'reorder_quantity': product.reorder_quantity
    }
    
    return jsonify({'product': product_data})

# Category routes
@inventory_bp.route('/categories')
@login_required
def categories():
    categories = Category.query.all()
    form = CategoryForm()  # Create a form instance for the quick add form
    return render_template('inventory/categories.html', categories=categories, form=form)

@inventory_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category added successfully', 'success')
        return redirect(url_for('inventory.categories'))
    
    return render_template('inventory/category_form.html', form=form, title='Add Category')

@inventory_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        flash('Category updated successfully', 'success')
        return redirect(url_for('inventory.categories'))
    
    return render_template('inventory/category_form.html', form=form, category=category, title='Edit Category')

@inventory_bp.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Check if category is in use
    if Product.query.filter_by(category_id=category_id).first():
        flash('Cannot delete category because it is in use by one or more products', 'danger')
        return redirect(url_for('inventory.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted successfully', 'success')
    return redirect(url_for('inventory.categories'))

# Supplier routes
@inventory_bp.route('/suppliers')
@login_required
def suppliers():
    suppliers = Supplier.query.all()
    
    # Get active orders count from suppliers
    active_orders_count = PurchaseOrder.query.filter(
        PurchaseOrder.status.in_(['pending', 'approved'])
    ).count()
      # Calculate total products supplied by all suppliers
    total_products = db.session.query(func.count(Product.id.distinct())).filter(
        Product.supplier_id.in_([s.id for s in suppliers])
    ).scalar() or 0
    
    # Count the number of received purchase orders
    total_purchased = PurchaseOrder.query.filter(
        PurchaseOrder.status == 'received'
    ).count() or 0
    
    # Get top suppliers by product count
    top_suppliers = db.session.query(
        Supplier.id, Supplier.name, func.count(Product.id).label('product_count')
    ).join(Product, Product.supplier_id == Supplier.id).group_by(
        Supplier.id
    ).order_by(db.desc('product_count')).limit(5).all()
    
    return render_template('inventory/suppliers.html', 
                          suppliers=suppliers,
                          active_orders=active_orders_count,
                          total_products=total_products,
                          total_purchased=total_purchased,
                          top_suppliers=top_suppliers)

@inventory_bp.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    form = SupplierForm()
    
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data,
            contact_person=form.contact_person.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data
        )
        
        db.session.add(supplier)
        db.session.commit()
        
        flash('Supplier added successfully', 'success')
        return redirect(url_for('inventory.suppliers'))
    
    return render_template('inventory/supplier_form.html', form=form, title='Add Supplier')

@inventory_bp.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    form = SupplierForm(obj=supplier)
    
    if form.validate_on_submit():
        supplier.name = form.name.data
        supplier.contact_person = form.contact_person.data
        supplier.email = form.email.data
        supplier.phone = form.phone.data
        supplier.address = form.address.data
        
        db.session.commit()
        flash('Supplier updated successfully', 'success')
        return redirect(url_for('inventory.suppliers'))
    
    return render_template('inventory/supplier_form.html', form=form, supplier=supplier, title='Edit Supplier')

@inventory_bp.route('/suppliers/<int:supplier_id>/delete', methods=['POST'])
@login_required
def delete_supplier(supplier_id):
    supplier = Supplier.query.get_or_404(supplier_id)
    
    # Check if supplier is in use
    if Product.query.filter_by(supplier_id=supplier_id).first():
        flash('Cannot delete supplier because it is in use by one or more products', 'danger')
        return redirect(url_for('inventory.suppliers'))
    
    db.session.delete(supplier)
    db.session.commit()
    
    flash('Supplier deleted successfully', 'success')
    return redirect(url_for('inventory.suppliers'))

@inventory_bp.route('/suppliers/export/csv')
@login_required
def export_suppliers_csv():
    suppliers = Supplier.query.all()
    
    # Create a DataFrame from the suppliers data
    data = []
    for supplier in suppliers:
        data.append({
            'ID': supplier.id,
            'Name': supplier.name,
            'Contact Person': supplier.contact_person,
            'Email': supplier.email,
            'Phone': supplier.phone,
            'Address': supplier.address,
            'Products Count': len(supplier.products)
        })
    
    df = pd.DataFrame(data)
    
    # Create a string IO object to store the CSV
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)
    
    # Return the CSV file as a response
    return send_file(
        output,
        as_attachment=True,
        download_name=f'suppliers_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
        mimetype='text/csv'
    )

# Inventory Transaction routes
@inventory_bp.route('/transactions')
@login_required
def transactions():
    # Get filter type parameter if provided
    transaction_type = request.args.get('type')
    
    # Base query
    query = InventoryTransaction.query
    
    # Apply filter if type is provided
    IN_TYPES = {'purchase', 'in'}
    OUT_TYPES = {'sale', 'out'}
    
    if transaction_type:
        if transaction_type.lower() == 'purchase':
            # Filter for stock in transactions
            query = query.filter(InventoryTransaction.transaction_type.in_(['purchase', 'IN']))
        elif transaction_type.lower() == 'sale':
            # Filter for stock out transactions
            query = query.filter(InventoryTransaction.transaction_type.in_(['sale', 'OUT']))
    
    # Get all transactions with applied filters
    transactions = query.order_by(InventoryTransaction.transaction_date.desc()).all()
    
    # Calculate stats for all transactions (unfiltered)
    all_transactions = InventoryTransaction.query.all()
    stock_in_count = 0
    stock_out_count = 0
    total_value = 0.0
    
    for t in all_transactions:
        ttype = (t.transaction_type or '').strip().lower()
        if ttype in IN_TYPES:
            stock_in_count += t.quantity
        elif ttype in OUT_TYPES:
            stock_out_count += t.quantity
        total_value += float(t.total_price or 0.0)
    
    return render_template('inventory/transactions.html', 
                          transactions=transactions,
                          stock_in_count=stock_in_count, 
                          stock_out_count=stock_out_count, 
                          total_value=total_value,
                          active_filter=transaction_type)

@inventory_bp.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = InventoryTransactionForm()
    all_products = Product.query.all()
    # Populate choices for products
    form.product_id.choices = [(p.id, f"{p.name} ({p.sku})") for p in Product.query.all()]
    
    if form.validate_on_submit():
        product = Product.query.get(form.product_id.data)
        
        # Calculate total price
        total_price = form.unit_price.data * form.quantity.data
        
        transaction = InventoryTransaction(
            product_id=form.product_id.data,
            transaction_type=form.transaction_type.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data,
            total_price=total_price,
            transaction_date=form.transaction_date.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(transaction)
        
        # Update product stock quantity
        if form.transaction_type.data == 'purchase':
            product.quantity_in_stock += form.quantity.data
        elif form.transaction_type.data == 'sale':
            if product.quantity_in_stock >= form.quantity.data:
                product.quantity_in_stock -= form.quantity.data
            else:
                flash('Insufficient stock for this sale', 'danger')
                return render_template('inventory/transaction_form.html', form=form, title='Add Transaction')
        
        db.session.commit()
        flash('Transaction added successfully', 'success')
        return redirect(url_for('inventory.transactions'))
    
    return render_template('inventory/transaction_form.html', form=form, title='Add Transaction',products=all_products)

# Purchase Order routes
@inventory_bp.route('/purchase-orders')
@login_required
def purchase_orders():
    orders = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).all()
    return render_template('inventory/purchase_orders.html', orders=orders)

@inventory_bp.route('/purchase-orders/add', methods=['GET', 'POST'])
@login_required
def add_purchase_order():
    form = PurchaseOrderForm()
    
    # Populate choices for supplier
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    
    if form.validate_on_submit():
        # Create new purchase order
        purchase_order = PurchaseOrder(
            supplier_id=form.supplier_id.data,
            order_date=form.order_date.data,
            expected_delivery_date=form.expected_delivery_date.data,
            status=form.status.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        db.session.add(purchase_order)
        db.session.flush()  # Get the purchase order ID
        
        # Process items from form data
        # Handle the items array format from the form
        items = []
        i = 0
        while True:
            product_key = f'items[{i}][product_id]'
            quantity_key = f'items[{i}][quantity]'
            price_key = f'items[{i}][unit_price]'
            
            if product_key not in request.form:
                break
                
            product_id = int(request.form[product_key])
            quantity = int(request.form[quantity_key])
            unit_price = float(request.form[price_key])
            total_price = quantity * unit_price
            
            items.append({
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': total_price
            })
            i += 1
        
        total_amount = 0
        
        for item in items:
            product_id = item['product_id']
            quantity = item['quantity']
            unit_price = item['unit_price']
            total_price = item['total_price']
            
            # Create purchase order item
            item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            
            db.session.add(item)
            total_amount += total_price
        
        # Update total amount
        purchase_order.total_amount = total_amount
        
        db.session.commit()
        flash('Purchase order created successfully', 'success')
        return redirect(url_for('inventory.purchase_orders'))
    
    # Get all products for dynamic form
    products = Product.query.all()
    
    return render_template(
        'inventory/purchase_order_form.html', 
        form=form, 
        products=products,
        title='Create Purchase Order'
    )

@inventory_bp.route('/purchase-orders/<int:order_id>')
@login_required
def view_purchase_order(order_id):
    # Get the purchase order with supplier relationship loaded
    order = PurchaseOrder.query.options(db.joinedload(PurchaseOrder.supplier)).get_or_404(order_id)
    # Get items with their products eagerly loaded
    items = PurchaseOrderItem.query.options(
        db.joinedload(PurchaseOrderItem.product)
    ).filter_by(purchase_order_id=order_id).all()
    # Get AI summary
    supplier = order.supplier  # Already loaded through the relationship
    ai_summary = ai_service.generate_purchase_order_summary(order, supplier, items)
    return render_template(
        'inventory/view_purchase_order.html',
        order=order,
        items=items,
        supplier=supplier,
        ai_summary=ai_summary
    )

@inventory_bp.route('/api/products/<int:product_id>', methods=['GET'])
@login_required
def get_product_api_info(product_id):
    product = Product.query.get_or_404(product_id)
    
    return jsonify({
        'status': 'success',
        'product': {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'quantity_in_stock': product.quantity_in_stock,
            'unit_price': product.unit_price,
            'reorder_level': product.reorder_level,
            'reorder_quantity': product.reorder_quantity
        }
    })

@inventory_bp.route('/purchase-orders/<int:order_id>/update-status', methods=['POST'])
@login_required
def update_purchase_order_status(order_id):
    order = PurchaseOrder.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'approved', 'received', 'canceled']:
        order.status = new_status
        
        # If status is received, update inventory
        if new_status == 'received':
            items = PurchaseOrderItem.query.filter_by(purchase_order_id=order_id).all()
            
            for item in items:
                product = Product.query.get(item.product_id)
                
                # Create inventory transaction
                transaction = InventoryTransaction(
                    product_id=item.product_id,
                    transaction_type='purchase',
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    notes=f"Received from PO #{order.id}",
                    created_by=current_user.id
                )
                
                db.session.add(transaction)
                
                # Update product stock
                product.quantity_in_stock += item.quantity
        
        db.session.commit()
        flash(f'Purchase order status updated to {new_status}', 'success')
    
    return redirect(url_for('inventory.view_purchase_order', order_id=order_id))

@inventory_bp.route('/purchase-orders/<int:order_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_purchase_order(order_id):
    purchase_order = PurchaseOrder.query.get_or_404(order_id)
    form = PurchaseOrderForm(obj=purchase_order)
    
    # Populate choices for supplier
    form.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.all()]
    
    if form.validate_on_submit():
        # Update purchase order details
        form.populate_obj(purchase_order)
          # Remove existing items - we'll replace them with the updated ones
        for item in purchase_order.items:
            db.session.delete(item)
        
        # Process items from form data
        # Handle the items array format from the form
        items = []
        i = 0
        while True:
            product_key = f'items[{i}][product_id]'
            quantity_key = f'items[{i}][quantity]'
            price_key = f'items[{i}][unit_price]'
            
            if product_key not in request.form:
                break
                
            product_id = int(request.form[product_key])
            quantity = int(request.form[quantity_key])
            unit_price = float(request.form[price_key])
            total_price = quantity * unit_price
            
            items.append({
                'product_id': product_id,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': total_price
            })
            i += 1
        
        total_amount = 0
        
        for item in items:
            product_id = item['product_id']
            quantity = item['quantity']
            unit_price = item['unit_price']
            total_price = item['total_price']
            
            # Create purchase order item
            item = PurchaseOrderItem(
                purchase_order_id=purchase_order.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            
            db.session.add(item)
            total_amount += total_price
        
        # Update total amount
        purchase_order.total_amount = total_amount
        purchase_order.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Purchase order updated successfully', 'success')
        return redirect(url_for('inventory.purchase_orders'))
    
    # Get all products for dynamic form
    products = Product.query.all()
    
    return render_template(
        'inventory/purchase_order_form.html',
        form=form,
        products=products,
        order=purchase_order,
        title='Edit Purchase Order'
    )

@inventory_bp.route('/purchase-orders/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_purchase_order(order_id):
    purchase_order = PurchaseOrder.query.get_or_404(order_id)
    
    # Delete purchase order items first
    PurchaseOrderItem.query.filter_by(purchase_order_id=order_id).delete()
    
    # Delete the purchase order
    db.session.delete(purchase_order)
    db.session.commit()
    
    flash('Purchase order deleted successfully', 'success')
    return redirect(url_for('inventory.purchase_orders'))

# Chatbot Routes
@inventory_bp.route('/chatbot')
@login_required
def chatbot():
    """Render the chatbot interface"""
    now = datetime.now()
    return render_template('inventory/chatbot.html', now=now)

@inventory_bp.route('/chatbot/api', methods=['POST'])
@login_required
def chatbot_api():
    """API endpoint for chatbot interactions"""
    data = request.json
    user_message = data.get('message', '')
    
    # Check if this is a confirmation for a pending update
    confirmation_words = ["yes", "confirm", "approved", "ok", "okay", "sure", "go ahead", "do it", "y", "yep", "yeah"]
    is_confirmation = user_message.lower().strip() in confirmation_words or any(word in user_message.lower() for word in confirmation_words)
    
    # If we have a pending update in session and the message is a confirmation
    if is_confirmation and 'pending_stock_update' in session:
        try:
            # Get the pending update info
            update_info = session.pop('pending_stock_update')
            product_id = update_info['product_id']
            quantity = update_info['quantity']
            
            # For operations other than 'add', adjust the quantity accordingly
            if update_info['operation'] != 'add':
                quantity = -quantity
            
            # Process the stock update directly without going through chatbot service
            product = Product.query.get(product_id)
            
            if not product:
                return jsonify({
                    "success": False, 
                    "message": "Product not found. The update was not processed."
                })
            
            # Update stock
            original_quantity = product.quantity_in_stock
            product.quantity_in_stock += quantity
            
            # Create transaction record
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type="IN" if quantity > 0 else "OUT",
                quantity=abs(quantity),
                unit_price=product.unit_price,
                total_price=abs(quantity) * product.unit_price,
                notes=f"Stock update via chatbot",
                created_by=current_user.id
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": f"Successfully updated {product.name} stock from {original_quantity} to {product.quantity_in_stock}."
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "success": False, 
                "message": f"Error updating stock: {str(e)}"
            })
    
    # Otherwise, process message with chatbot service
    result = chatbot_service.process_message(user_message, current_user.id)
    
    # Store context in session if needed for confirmation flow
    if result.get('needsConfirmation'):
        session['pending_stock_update'] = {
            'product_id': result['product']['id'],
            'quantity': result['product']['quantity'],
            'operation': result['product']['operation']
        }
    
    return jsonify(result)

@inventory_bp.route('/chatbot/confirm', methods=['POST'])
@login_required
def confirm_stock_update():
    """Legacy endpoint for confirming stock updates - now handled by chatbot/api"""
    data = request.json
    confirmation = data.get('confirmation', False)
    
    if not confirmation or 'pending_stock_update' not in session:
        return jsonify({
            "success": False,
            "message": "No pending stock update to confirm"
        })
    
    # Get the same update info that would be used by chatbot/api
    update_info = session.get('pending_stock_update')
    product_id = update_info['product_id']
    quantity = update_info['quantity']
    
    # For operations other than 'add', adjust the quantity accordingly
    if update_info['operation'] != 'add':
        quantity = -quantity
    
    # Process the stock update
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({"success": False, "message": "Product not found"})
    
    try:
        # Update stock
        original_quantity = product.quantity_in_stock
        product.quantity_in_stock += quantity
        
        # Create transaction record
        transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type="IN" if quantity > 0 else "OUT",
            quantity=abs(quantity),
            unit_price=product.unit_price,
            total_price=abs(quantity) * product.unit_price,
            notes=f"Stock update via chatbot",
            created_by=current_user.id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        # Remove from session after successful update
        session.pop('pending_stock_update', None)
        
        return jsonify({
            "success": True,
            "message": f"Successfully updated {product.name} stock from {original_quantity} to {product.quantity_in_stock}."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error updating stock: {str(e)}"})

@inventory_bp.route('/analytics')
def analytics_view():
    # 1) Load or generate ML results
    results = AnalysisService.get_latest_results()
    if not results:
        AnalysisService.run_ml_analysis()
        results = AnalysisService.get_latest_results()

    # 2) Create a list of dicts for JSON‐ready data
    js_results = [r.to_dict() for r in results]

    # 3) Render, passing both raw ORM rows (for table) & js_results
    return render_template(
        'inventory/analytics.html',
        ml_results=results,       # ORM objects for the table
        ml_results_json=js_results  # list of simple dicts for Chart.js
    )

@inventory_bp.route('/analytics/run', methods=['POST'])
def analytics_run():
    AnalysisService.run_ml_analysis()
    return jsonify(success=True)

@inventory_bp.route('/analytics/email', methods=['POST'])
def analytics_email():
    # generate or load results
    results = AnalysisService.get_latest_results()
    if not results:
        results = AnalysisService.run_ml_analysis()
    run_date = datetime.utcnow()

    # send email
    try:
        EmailService.send_analytics_report(results, run_date)
        return jsonify(success=True)
    except Exception as e:
        current_app.logger.exception("Failed to send analytics emails")
        return jsonify(success=False, error=str(e)), 500