import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pathlib import Path
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import JSONLoader, PyPDFLoader, DirectoryLoader
from langchain_community.docstore.document import Document
from langchain_pinecone import PineconeVectorStore
from loguru import logger

load_dotenv()

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("⚠️ PINECONE_API_KEY not found in .env")
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

class VectorStoreManager:
    def __init__(self):
        self.index_name = "ProctorIQ"
        self.embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
        self.dimension = 384
        self.chunk_size = 500
        self.chunk_overlap = 50
        self.data_dir= "exam_automator\backend\docs"
        # self.data_dir = Path(__file__).parent.parent / "data/raw/cloudnine_scraped"

        self.embeddings = self.load_embeddings()
        self.pinecone = Pinecone(api_key=PINECONE_API_KEY)
        self.vector_store = self._get_or_create_vector_store()
        
    def load_embeddings(self):
        return HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

    def _get_or_create_vector_store(self) -> Optional[PineconeVectorStore]:
        try:
            if self.index_name not in [index.name for index in self.pinecone.list_indexes()]:
                self.pinecone.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
                logger.info(f"✅ Created new Pinecone index: {self.index_name}")
            return PineconeVectorStore.from_existing_index(
                index_name=self.index_name,
                embedding=self.embeddings
            )
        except Exception as e:
            logger.error(f"❌ Error creating vector store: {e}")
            return None

    def load_all_documents(self) -> List[Document]:
        all_docs = []

        document_types = {
            # "departments.json": {"type": "department", "priority": "high"},
            # "doctors.json": {"type": "doctor", "priority": "high"},
            # "faqs.json": {"type": "faq", "priority": "medium"},
            # "services.json": {"type": "service", "priority": "high"},
            # "dummy_dialogs.json": {"type": "dialog", "priority": "medium"}
        }

        try:
            for file, metadata in document_types.items():
                file_path = self.data_dir / file
                if file_path.exists():
                    loader = JSONLoader(
                        file_path=str(file_path),
                        jq_schema=".",
                        text_content=False  # Important fix!
                    )
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata.update(metadata)
                    all_docs.extend(docs)
                    logger.info(f"✅ Loaded {file} ({len(docs)} docs)")
                    

            # Load PDFs from guidelines folder
            guideline_dir = self.data_dir / "guidelines"
            if guideline_dir.exists():
                loader = DirectoryLoader(
                    str(guideline_dir),
                    glob="*.pdf",
                    loader_cls=PyPDFLoader
                )
                docs = loader.load()
                for doc in docs:
                    doc.metadata.update({"type": "medical_guideline", "priority": "medium"})
                all_docs.extend(docs)
                logger.info(f"📘 Loaded {len(docs)} pages from guidelines")
        except Exception as e:
            logger.error(f"❌ Failed to load documents: {e}")
            return []

        return all_docs

    def split_documents(self, docs: List[Document]) -> List[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        chunks = splitter.split_documents(docs)
        logger.info(f"📚 Split into {len(chunks)} chunks")
        return chunks

    def setup_vector_store(self) -> bool:
        try:
            docs = self.load_all_documents()
            if not docs:
                logger.warning("⚠️ No documents found to process.")
                return False

            chunks = self.split_documents(docs)

            PineconeVectorStore.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                index_name=self.index_name
            )
            logger.info(f"✅ Successfully added {len(chunks)} chunks to vector store.")
            return True
        except Exception as e:
            logger.error(f"❌ Error setting up vector store: {e}")
            return False

    def query_vector_store(self, query: str, k: int = 3, filters: Optional[Dict] = None) -> List[Document]:
        """Query the vector store for relevant documents"""
        try:
            if not self.vector_store:
                logger.error("❌ Vector store not initialized")
                return []

            search_kwargs = {"k": k}
            if filters:
                search_kwargs["filter"] = filters

            docs = self.vector_store.similarity_search(
                query=query,
                **search_kwargs
            )
            logger.info(f"✅ Found {len(docs)} relevant documents")
            return docs
        except Exception as e:
            logger.error(f"❌ Error querying vector store: {e}")
            return []


if __name__ == "__main__":
    manager = VectorStoreManager()
    success = manager.setup_vector_store()
    if success:
        print("✅ Vector store setup completed successfully.")
    else:
        print("❌ Vector store setup failed.")