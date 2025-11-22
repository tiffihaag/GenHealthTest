# ocr.py

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
import PyPDF2
import httpx
from datetime import datetime
from typing import Optional

# --- Pydantic Models (Temporarily defined here for demonstration) ---
# In a larger project, these would typically be in a separate 'models.py'
# file and imported into both main.py and ocr.py to avoid duplication.
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
# --- End Pydantic Models ---

import firebase_admin
from firebase_admin import firestore
from firebase_admin.firestore import CollectionReference # For type hinting

# Dependency to get the Firestore client (assuming Firebase is initialized in main.py)
def get_firestore_db():
    try:
        firebase_admin.get_app()
        return firestore.client()
    except ValueError:
        raise HTTPException(status_code=500, detail="Firebase Admin SDK not initialized. Check main.py setup.")

# Dependency to get the 'orders' collection reference
def get_orders_collection(db_client: firestore.Client = Depends(get_firestore_db)) -> CollectionReference:
    return db_client.collection('orders')


# --- FIX START ---
# Define ocr_router BEFORE any @ocr_router.post decorators
ocr_router = APIRouter()
# --- FIX END ---


# Assume your GenKit Cloud Function endpoint URL
GENKIT_EXTRACT_ORDER_URL = "YOUR_DEPLOYED_GENKIT_CLOUD_FUNCTION_URL" # <--- IMPORTANT: Update this URL when you deploy GenKit

@ocr_router.post("/orders/from-pdf", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_from_pdf(
    pdf_file: UploadFile = File(...),
    orders_collection: CollectionReference = Depends(get_orders_collection) # Injected Firestore collection
):
    print(f"Received file: {pdf_file.filename}, Content-Type: {pdf_file.content_type}")

    if not pdf_file.filename.lower().endswith('.pdf'):
        print(f"Error: File '{pdf_file.filename}' is not a PDF.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed."
        )
    
    extracted_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file.file)
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() or ""
        print(f"Successfully extracted {len(extracted_text)} characters from PDF.")
        if len(extracted_text) < 500: # print full text if short, otherwise just first 500 chars
            print(f"Extracted Text (full): {extracted_text.strip()}")
        else:
            print(f"Extracted Text (first 500 chars): {extracted_text.strip()[:500]}...")

    except Exception as e:
        print(f"Error during PDF text extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text from PDF: {e}"
        )

    if not extracted_text.strip():
        print("Error: Extracted text is empty or only whitespace.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the provided PDF."
        )

    # --- TEMPORARY MOCK FOR LOCAL TESTING ---
    # This section simulates the response from your GenKit Cloud Function.
    # REMOVE/UNCOMMENT the httpx call below once your GenKit function is deployed!
    print("MOCKING GenKit AI response for local testing...")
    ai_extracted_data = {
        "customer_name": "Test Customer from PDF",
        "product": "Test Product from PDF",
        "quantity": 1,
        "total_price": 99.99,
        "status": "processed-by-ai"
    }
    
    order_data_for_firestore = OrderCreate(**ai_extracted_data)

    # --- Re-enable the actual httpx call once your GenKit function is deployed: ---
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
    # --- End httpx call section ---
        
    # 3. Use your existing Firestore logic to save the extracted order
    order_data = {
        'customer_name': order_data_for_firestore.customer_name,
        'product': order_data_for_firestore.product,
        'quantity': order_data_for_firestore.quantity,
        'total_price': order_data_for_firestore.total_price,
        'status': order_data_for_firestore.status,
        'created_at': datetime.utcnow().isoformat()
    }
    
    doc_ref = orders_collection.add(order_data)
    order_id = doc_ref[1].id
    
    order_data['id'] = order_id
    return OrderResponse(**order_data)

