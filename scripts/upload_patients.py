#!/usr/bin/env python3
"""
Script to upload sample patient data to Pinecone vector database
"""

import os
import json
import sys
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from dotenv import load_dotenv
import time

def load_environment():
    """Load environment variables"""
    # Try to load from backend directory first
    backend_env = Path(__file__).parent.parent / "backend" / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)
    else:
        load_dotenv()
    
    required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file in the backend directory with the required variables.")
        sys.exit(1)

def initialize_pinecone():
    """Initialize Pinecone client and create index if needed"""
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
    
    index_name = os.getenv('PINECONE_INDEX_NAME', 'medical-assistant')
    
    # Check if index exists, create if it doesn't
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"Creating new Pinecone index: {index_name}")
        
        # Create serverless index (free tier compatible)
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI embedding dimension
            metric='cosine',
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'  # Free tier region
            )
        )
        
        # Wait for index to be ready
        print("Waiting for index to be ready...")
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
        
        print("Index created successfully!")
    else:
        print(f"Using existing Pinecone index: {index_name}")
    
    return pc, index_name

def load_patient_data():
    """Load patient data from JSON file"""
    data_file = Path(__file__).parent.parent / "backend" / "data" / "sample_patients.json"
    
    if not data_file.exists():
        print(f"Error: Patient data file not found at {data_file}")
        sys.exit(1)
    
    with open(data_file, 'r') as f:
        patients = json.load(f)
    
    print(f"Loaded {len(patients)} patient records")
    return patients

def create_documents(patients):
    """Convert patient data to LangChain Document objects"""
    documents = []
    
    for patient in patients:
        doc = Document(
            page_content=patient['content'],
            metadata={
                'patient_id': patient['id'],
                'source': 'medical_records'
            }
        )
        documents.append(doc)
    
    return documents

def upload_to_pinecone(documents, pc, index_name):
    """Upload documents to Pinecone vector store"""
    print("Initializing OpenAI embeddings...")
    embeddings = OpenAIEmbeddings()
    
    print("Creating vector store and uploading documents...")
    try:
        # Create vector store from documents with index name
        vectorstore = PineconeVectorStore.from_documents(
            documents=documents,
            embedding=embeddings,
            index_name=index_name,
            pinecone_api_key=os.getenv('PINECONE_API_KEY')
        )
        print(f"Successfully uploaded {len(documents)} documents to Pinecone!")
        return vectorstore
    except Exception as e:
        print(f"Error uploading to Pinecone: {e}")
        sys.exit(1)

def test_retrieval(vectorstore):
    """Test the retrieval functionality"""
    print("\nTesting retrieval...")
    
    test_queries = [
        "Tell me about John Doe",
        "Who has diabetes?",
        "Which patients are on blood pressure medication?",
        "Show me heart failure patients"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            docs = vectorstore.similarity_search(query, k=2)
            for i, doc in enumerate(docs, 1):
                patient_id = doc.metadata.get('patient_id', 'Unknown')
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"  Result {i} ({patient_id}): {content_preview}")
        except Exception as e:
            print(f"  Error during retrieval: {e}")

def main():
    """Main function"""
    print("Starting Pinecone upload process...")
    
    # Load environment variables
    load_environment()
    
    # Initialize Pinecone
    pc, index_name = initialize_pinecone()
    
    # Load patient data
    patients = load_patient_data()
    
    # Create documents
    documents = create_documents(patients)
    
    # Upload to Pinecone
    vectorstore = upload_to_pinecone(documents, pc, index_name)
    
    # Test retrieval
    test_retrieval(vectorstore)
    
    print("\n✅ Upload completed successfully!")
    print(f"Your medical assistant is now ready with {len(patients)} patient records.")
    print(f"You can now start the backend server and test the voice assistant.")

if __name__ == "__main__":
    main() 