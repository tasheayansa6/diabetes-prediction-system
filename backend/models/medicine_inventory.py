from backend.extensions import db
from datetime import datetime

class MedicineInventory(db.Model):
    __tablename__ = 'medicine_inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.String(50), unique=True, nullable=False)
    
    # Medicine Information
    name = db.Column(db.String(200), nullable=False)
    generic_name = db.Column(db.String(200))
    category = db.Column(db.String(100))
    manufacturer = db.Column(db.String(200))
    supplier = db.Column(db.String(200))
    
    # Stock Information
    quantity = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20), default='tablets')
    minimum_stock = db.Column(db.Integer, default=10)
    maximum_stock = db.Column(db.Integer, default=100)
    reorder_level = db.Column(db.Integer, default=20)
    
    # Pricing
    cost_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    tax_percentage = db.Column(db.Float, default=0.0)
    
    # Expiry and Batch
    batch_number = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)
    manufactured_date = db.Column(db.Date)
    
    # Storage
    location = db.Column(db.String(100))
    storage_conditions = db.Column(db.String(200))
    
    # Prescription Requirements
    requires_prescription = db.Column(db.Boolean, default=True)
    is_controlled_substance = db.Column(db.Boolean, default=False)
    
    # Dosage Information
    strength = db.Column(db.String(50))
    dosage_form = db.Column(db.String(50))
    
    # Description
    description = db.Column(db.Text)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_restocked_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        if 'medicine_id' not in kwargs or not kwargs['medicine_id']:
            import uuid
            kwargs['medicine_id'] = f"MED{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        super(MedicineInventory, self).__init__(**kwargs)
    
    @property
    def stock_status(self):
        if self.quantity <= 0:
            return "Out of Stock"
        elif self.quantity <= self.minimum_stock:
            return "Low Stock"
        else:
            return "In Stock"
    
    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < datetime.utcnow().date()
        return False
    
    @property
    def needs_reorder(self):
        return self.quantity <= self.reorder_level
    
    def add_stock(self, quantity, notes=""):
        self.quantity += quantity
        self.last_restocked_at = datetime.utcnow()
        return True
    
    def remove_stock(self, quantity, notes=""):
        if self.quantity >= quantity:
            self.quantity -= quantity
            return True
        return False
    
    def to_dict(self):
        return {
            "id": self.id,
            "medicine_id": self.medicine_id,
            "name": self.name,
            "generic_name": self.generic_name,
            "category": self.category,
            "manufacturer": self.manufacturer,
            "supplier": self.supplier,
            "quantity": self.quantity,
            "unit": self.unit,
            "minimum_stock": self.minimum_stock,
            "maximum_stock": self.maximum_stock,
            "reorder_level": self.reorder_level,
            "cost_price": self.cost_price,
            "selling_price": self.selling_price,
            "batch_number": self.batch_number,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "location": self.location,
            "storage_conditions": self.storage_conditions,
            "requires_prescription": self.requires_prescription,
            "is_controlled_substance": self.is_controlled_substance,
            "strength": self.strength,
            "dosage_form": self.dosage_form,
            "description": self.description,
            "is_active": self.is_active,
            "stock_status": self.stock_status,
            "is_expired": self.is_expired,
            "needs_reorder": self.needs_reorder,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_restocked_at": self.last_restocked_at.isoformat() if self.last_restocked_at else None
        }
    
    def __repr__(self):
        return f"<MedicineInventory {self.name} (Qty: {self.quantity})>"
