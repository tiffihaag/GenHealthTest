from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
import httpx
from datetime import datetime
from typing import Optional
import os # To read environment variables

# --- Google Cloud Document AI Imports ---
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

# --- Pydantic Models (Temporarily defined here for demonstration) ---
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

# --- Document AI Configuration (UPDATE THESE VALUES CAREFULLY) ---
# It's best practice to use environment variables for these sensitive values
# For local testing, you can temporarily hardcode them, but remember to remove before production
# You can set these as environment variables like:
# export GCP_PROJECT="genh-f43c3"
# export DOCUMENT_AI_LOCATION="us"
# export DOCUMENT_AI_OCR_PROCESSOR_ID="bd4c4089295a0377"
# export DOCUMENT_AI_PROCESSOR_VERSION="rc" # or a specific version like 'pretrained-ocr-v1.2-2023-01-26'

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT", "genh-f43c3") # Your Firebase Project ID
DOCUMENT_AI_LOCATION = os.environ.get("DOCUMENT_AI_LOCATION", "us") # Your processor's location
# !!! REPLACE "YOUR_OCR_PROCESSOR_ID_HERE" with the actual ID you got from Document AI Console !!!
DOCUMENT_AI_OCR_PROCESSOR_ID = os.environ.get("DOCUMENT_AI_OCR_PROCESSOR_ID", "bd4c4089295a0377")
# 'rc' usually refers to the latest stable version. Use a specific version if you prefer.
DOCUMENT_AI_PROCESSOR_VERSION = os.environ.get("DOCUMENT_AI_PROCESSOR_VERSION", "rc")
# --- END Document AI Configuration ---

ocr_router = APIRouter()

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
    
    # --- START Document AI OCR Integration ---
    extracted_text = ""
    try:
        # Read the content of the uploaded PDF file asynchronously
        pdf_content = await pdf_file.read()

        # Initialize Document AI client
        # You must set the `api_endpoint` if you use a location other than "us".
        client_options = ClientOptions(api_endpoint=f"{DOCUMENT_AI_LOCATION}-documentai.googleapis.com")
        docai_client = documentai.DocumentProcessorServiceClient(client_options=client_options)

        # The full resource name of the processor version
        resource_name = docai_client.processor_version_path(
            GCP_PROJECT_ID, DOCUMENT_AI_LOCATION, DOCUMENT_AI_OCR_PROCESSOR_ID, DOCUMENT_AI_PROCESSOR_VERSION
        )

        # Create the raw document object
        raw_document = documentai.RawDocument(content=pdf_content, mime_type="application/pdf")

        # Configure the process request
        request = documentai.ProcessRequest(name=resource_name, raw_document=raw_document)

        # Process the document
        print(f"Sending PDF to Document AI OCR processor: {DOCUMENT_AI_OCR_PROCESSOR_ID} in {DOCUMENT_AI_LOCATION}...")
        result = docai_client.process_document(request=request)
        print("Document AI processing complete.")

        # Extract the full text from the processed document
        extracted_text = result.document.text

        print(f"Successfully extracted {len(extracted_text)} characters from PDF using Document AI.")
        if len(extracted_text) < 500: # print full text if short, otherwise just first 500 chars
            print(f"Extracted Text (full): {extracted_text.strip()}")
        else:
            print(f"Extracted Text (first 500 chars): {extracted_text.strip()[:500]}...")

    except Exception as e:
        print(f"Error during Document AI OCR processing: {e}")
        # Provide more specific guidance in the HTTP response detail
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting text from PDF using Document AI: {e}. "
                   "Please ensure the Document AI API is enabled, an OCR processor is created, "
                   "and the 'GOOGLE_APPLICATION_CREDENTIALS' environment variable is set correctly "
                   "for your service account with appropriate permissions."
        )
    # --- END Document AI OCR Integration ---

    # This check is still valid, even with Document AI
    if not extracted_text.strip():
        print("Error: Extracted text is empty or only whitespace after Document AI processing.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the provided PDF using Document AI (returned empty text)."
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
    #         # Now 'extracted_text' comes from Document AI's OCR
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

