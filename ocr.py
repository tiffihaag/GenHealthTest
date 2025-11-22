# ocr.py

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
import PyPDF2
import httpx
from datetime import datetime
from typing import Optional

# Import your Pydantic models from main.py or a shared `models.py` file
# Assuming they are defined in main.py, you'd import them like this:
# from main import OrderCreate, OrderResponse # This might cause circular import with some setups
# For simplicity, let's redefine them here FOR NOW, but better practice is shared models.py
from pydantic import BaseModel
class OrderCreate(BaseModel):
    customer_name: str
    product: str
    quantity: int
    total_price: float
    status: Optional[str] = 'pending'

class OrderResponse(BaseModel):
    id: str
    customer_name: str
    product: str
    quantity: int
    total_price: float
    status: str
    created_at: str

# --- REMOVE all previous firebase_admin.initialize_app() and firebase_admin.get_app() from here ---
# Instead, we will define dependencies that get the *already initialized* Firebase client.
import firebase_admin
from firebase_admin import firestore
from firebase_admin.firestore import CollectionReference # For type hinting

# Dependency to get the Firestore client
def get_firestore_db():
    try:
        # This assumes the default app is initialized by main.py
        firebase_admin.get_app()
        return firestore.client()
    except ValueError:
        raise HTTPException(status_code=500, detail="Firebase Admin SDK not initialized. Check main.py setup.")

# Dependency to get the 'orders' collection reference
def get_orders_collection(db_client: firestore.Client = Depends(get_firestore_db)) -> CollectionReference:
    return db_client.collection('orders')
# --- END of Firebase dependency setup ---


ocr_router = APIRouter()

# Assume your GenKit Cloud Function endpoint URL
GENKIT_EXTRACT_ORDER_URL = "YOUR_DEPLOYED_GENKIT_CLOUD_FUNCTION_URL" # <--- IMPORTANT: Update this URL

@ocr_router.post("/orders/from-pdf", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_from_pdf(
    pdf_file: UploadFile = File(...),
    orders_collection: CollectionReference = Depends(get_orders_collection) # Inject orders_ref
):
    if not pdf_file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed."
        )
    
    # 1. Extract text from the PDF
    extracted_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file.file)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() or ""
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text from PDF: {e}"
        )

    if not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the provided PDF."
        )

    # TEMPORARY MOCK FOR LOCAL TESTING:
    print(f"Extracted text for AI processing:\n{extracted_text[:500]}...") # Print first 500 chars
    
    # We'll mock the response from GenKit for now.
    ai_extracted_data = {
        "customer_name": "Test Customer from PDF",
        "product": "Test Product from PDF",
        "quantity": 1,
        "total_price": 99.99,
        "status": "processed-by-ai"
    }
    
    order_data_for_firestore = OrderCreate(**ai_extracted_data)

    # Re-enable the actual httpx call once your GenKit function is deployed:
    # try:
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(
    #             GENKIT_EXTRACT_ORDER_URL,
    #             json={"pdf_text": extracted_text}
    #         )
    #         response.raise_for_status()
    #         ai_extracted_data = response.json()
    #         order_data_for_firestore = OrderCreate(**ai_extracted_data)
    # except httpx.HTTPStatusError as e:
    #     raise HTTPException(
    #         status_code=e.response.status_code,
    #         detail=f"Error from AI Logic: {e.response.text}"
    #     )
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail=f"Error communicating with AI Logic or processing its response: {e}"
    # )
        
    # 3. Use your existing Firestore logic to save the extracted order
    order_data = {
        'customer_name': order_data_for_firestore.customer_name,
        'product': order_data_for_firestore.product,
        'quantity': order_data_for_firestore.quantity,
        'total_price': order_data_for_firestore.total_price,
        'status': order_data_for_firestore.status,
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Use the injected orders_collection here
    doc_ref = orders_collection.add(order_data)
    order_id = doc_ref[1].id
    
    order_data['id'] = order_id
    return OrderResponse(**order_data)
