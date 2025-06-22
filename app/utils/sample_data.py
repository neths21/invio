import json
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import db, create_app
from app.models.models import User, Supplier, Category, Product, InventoryTransaction

def load_sample_data():
    """Load sample data into the database"""
    # Create admin user
    admin_user = User(
        username="admin",
        email="admin@example.com",
        password_hash=generate_password_hash("admin123"),
        is_admin=True
    )
    db.session.add(admin_user)
    
    # Create regular user
    user = User(
        username="user",
        email="user@example.com",
        password_hash=generate_password_hash("user123"),
        is_admin=False
    )
    db.session.add(user)
    
    # Create suppliers
    suppliers = [
        Supplier(name="Tech Supplies Inc.", contact_person="John Smith", email="john@techsupplies.com", phone="555-123-4567", address="123 Tech St, San Francisco, CA 94107"),
        Supplier(name="Office Essentials", contact_person="Jane Doe", email="jane@officeessentials.com", phone="555-987-6543", address="456 Office Ave, New York, NY 10001"),
        Supplier(name="Hardware Depot", contact_person="Michael Johnson", email="michael@hardwaredepot.com", phone="555-789-0123", address="789 Hardware Blvd, Chicago, IL 60607")
    ]
    
    for supplier in suppliers:
        db.session.add(supplier)
    
    # Create categories
    categories = [
        Category(name="Electronics", description="Electronic devices and accessories"),
        Category(name="Office Supplies", description="Stationery and office essentials"),
        Category(name="Furniture", description="Office furniture and fixtures")
    ]
    
    for category in categories:
        db.session.add(category)
    
    # Commit to get IDs
    db.session.commit()
    
    # Create products
    products = [
        # Electronics
        Product(name="Laptop", description="15-inch business laptop", sku="EL-LAP-001", unit_price=999.99, quantity_in_stock=25, reorder_level=5, reorder_quantity=10, category_id=1, supplier_id=1),
        Product(name="Monitor", description="24-inch HD monitor", sku="EL-MON-001", unit_price=249.99, quantity_in_stock=15, reorder_level=3, reorder_quantity=5, category_id=1, supplier_id=1),
        Product(name="Keyboard", description="Wireless keyboard", sku="EL-KEY-001", unit_price=49.99, quantity_in_stock=30, reorder_level=10, reorder_quantity=20, category_id=1, supplier_id=1),
        Product(name="Mouse", description="Wireless mouse", sku="EL-MOU-001", unit_price=29.99, quantity_in_stock=20, reorder_level=8, reorder_quantity=15, category_id=1, supplier_id=1),
        Product(name="Headphones", description="Noise-canceling headphones", sku="EL-HEAD-001", unit_price=149.99, quantity_in_stock=12, reorder_level=4, reorder_quantity=8, category_id=1, supplier_id=1),
        
        # Office Supplies
        Product(name="Paper", description="A4 printer paper (500 sheets)", sku="OS-PAP-001", unit_price=9.99, quantity_in_stock=100, reorder_level=20, reorder_quantity=50, category_id=2, supplier_id=2),
        Product(name="Pens", description="Blue ballpoint pens (box of 12)", sku="OS-PEN-001", unit_price=5.99, quantity_in_stock=50, reorder_level=15, reorder_quantity=30, category_id=2, supplier_id=2),
        Product(name="Staplers", description="Desktop stapler", sku="OS-STA-001", unit_price=8.99, quantity_in_stock=25, reorder_level=10, reorder_quantity=20, category_id=2, supplier_id=2),
        Product(name="Notebooks", description="Spiral notebooks (pack of 3)", sku="OS-NOTE-001", unit_price=12.99, quantity_in_stock=35, reorder_level=12, reorder_quantity=24, category_id=2, supplier_id=2),
        Product(name="Folders", description="Manila folders (box of 50)", sku="OS-FOL-001", unit_price=15.99, quantity_in_stock=20, reorder_level=5, reorder_quantity=15, category_id=2, supplier_id=2),
        
        # Furniture
        Product(name="Desk", description="Executive desk", sku="FN-DSK-001", unit_price=349.99, quantity_in_stock=8, reorder_level=2, reorder_quantity=5, category_id=3, supplier_id=3),
        Product(name="Chair", description="Ergonomic office chair", sku="FN-CHR-001", unit_price=199.99, quantity_in_stock=12, reorder_level=3, reorder_quantity=6, category_id=3, supplier_id=3),
        Product(name="Bookshelf", description="5-shelf bookcase", sku="FN-BKS-001", unit_price=129.99, quantity_in_stock=5, reorder_level=2, reorder_quantity=3, category_id=3, supplier_id=3),
        Product(name="Filing Cabinet", description="3-drawer filing cabinet", sku="FN-CAB-001", unit_price=159.99, quantity_in_stock=6, reorder_level=2, reorder_quantity=4, category_id=3, supplier_id=3),
        Product(name="Conference Table", description="8-person conference table", sku="FN-TBL-001", unit_price=499.99, quantity_in_stock=3, reorder_level=1, reorder_quantity=2, category_id=3, supplier_id=3)
    ]
    
    for product in products:
        db.session.add(product)
    
    # Commit products to get IDs
    db.session.commit()
    
    # Create inventory transactions (purchases)
    for product in products:
        transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type='purchase',
            quantity=product.quantity_in_stock,
            unit_price=product.unit_price,
            total_price=product.unit_price * product.quantity_in_stock,
            transaction_date=datetime.utcnow() - timedelta(days=30),
            notes=f"Initial stock purchase of {product.name}",
            created_by=admin_user.id
        )
        db.session.add(transaction)
    
    # Create some sales transactions
    sales_data = [
        {"product_id": 1, "quantity": 3, "days_ago": 25},
        {"product_id": 1, "quantity": 2, "days_ago": 15},
        {"product_id": 2, "quantity": 1, "days_ago": 20},
        {"product_id": 6, "quantity": 15, "days_ago": 10},
        {"product_id": 7, "quantity": 5, "days_ago": 5},
        {"product_id": 11, "quantity": 1, "days_ago": 12},
        {"product_id": 12, "quantity": 2, "days_ago": 8}
    ]
    
    for sale in sales_data:
        product = Product.query.get(sale["product_id"])
        transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type='sale',
            quantity=sale["quantity"],
            unit_price=product.unit_price,
            total_price=product.unit_price * sale["quantity"],
            transaction_date=datetime.utcnow() - timedelta(days=sale["days_ago"]),
            notes=f"Sale of {product.name}",
            created_by=user.id
        )
        db.session.add(transaction)
        
        # Update stock quantity
        product.quantity_in_stock -= sale["quantity"]
    
    # Create a product with low stock
    low_stock_product = Product.query.get(5)  # Headphones
    low_stock_product.quantity_in_stock = 2  # Below reorder level
    
    # Commit all changes
    db.session.commit()
    
    print("Sample data loaded successfully!")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        load_sample_data()
