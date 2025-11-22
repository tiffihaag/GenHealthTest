from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
from typing import Optional

app = FastAPI(title="Order Management API")

# Initialize Firebase
cred = credentials.Certificate('path/to/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Collection reference
orders_ref = db.collection('orders')

# Pydantic models
class OrderCreate(BaseModel):
    customer_name: str
    product: str
    quantity: int
    total_price: float
    status: Optional[str] = 'pending'

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[int] = None
    total_price: Optional[float] = None
    status: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    customer_name: str
    product: str
    quantity: int
    total_price: float
    status: str
    created_at: str

# CREATE - Add new order
@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate):
    order_data = {
        'customer_name': order.customer_name,
        'product': order.product,
        'quantity': order.quantity,
        'total_price': order.total_price,
        'status': order.status,
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Add to Firestore
    doc_ref = orders_ref.add(order_data)
    order_id = doc_ref[1].id
    
    order_data['id'] = order_id
    return order_data

# READ - Get all orders
@app.get("/orders", response_model=list[OrderResponse])
async def get_orders():
    orders = []
    docs = orders_ref.stream()
    
    for doc in docs:
        order = doc.to_dict()
        order['id'] = doc.id
        orders.append(order)
    
    return orders

# READ - Get single order by ID
@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    doc = orders_ref.document(order_id).get()
    
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    order = doc.to_dict()
    order['id'] = doc.id
    
    return order

# UPDATE - Update existing order
@app.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(order_id: str, order: OrderUpdate):
    doc_ref = orders_ref.document(order_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update only provided fields
    update_data = order.dict(exclude_unset=True)
    
    if update_data:
        doc_ref.update(update_data)
    
    # Get updated document
    updated_doc = doc_ref.get()
    order_data = updated_doc.to_dict()
    order_data['id'] = updated_doc.id
    
    return order_data

# DELETE - Delete order
@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    doc_ref = orders_ref.document(order_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    doc_ref.delete()
    
    return {"message": "Order deleted successfully"}

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Order Management API - Visit /docs for API documentation"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)