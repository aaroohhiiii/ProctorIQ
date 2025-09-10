import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pathlib import Path
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import ServerlessSpec
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, DirectoryLoader
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
        self.chunk_size = 1000  # Increased for exam content
        self.chunk_overlap = 100  # Increased overlap for better context
        self.data_dir = Path(__file__).parent.parent / "docs"  # Points to exam_automator/backend/docs

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
        """Load all exam-related documents from the docs directory"""
        all_docs = []

        try:
            # Define document types for exam automation
            document_patterns = {
                "SQP*.txt": {"type": "question_paper", "priority": "high"},
                "MS*.txt": {"type": "marking_scheme", "priority": "high"},
                "Student_Answer_Paper*.txt": {"type": "student_answer", "priority": "medium"},
            }

            for pattern, metadata in document_patterns.items():
                # Use glob to find files matching the pattern
                files = list(self.data_dir.glob(pattern))
                
                for file_path in files:
                    if file_path.exists() and file_path.is_file():
                        try:
                            loader = TextLoader(str(file_path), encoding='utf-8')
                            docs = loader.load()
                            
                            # Add specific metadata based on filename
                            for doc in docs:
                                doc.metadata.update(metadata)
                                doc.metadata["filename"] = file_path.name
                                doc.metadata["file_path"] = str(file_path)
                                
                                # Extract paper number from filename
                                if "SQP" in file_path.name:
                                    paper_num = file_path.name.replace("SQP", "").replace(".txt", "")
                                    doc.metadata["paper_number"] = paper_num
                                elif "MS" in file_path.name:
                                    paper_num = file_path.name.replace("MS", "").replace(".txt", "")
                                    doc.metadata["paper_number"] = paper_num
                                elif "Student_Answer_Paper" in file_path.name:
                                    # Extract paper and variation info
                                    parts = file_path.name.replace("Student_Answer_Paper", "").replace(".txt", "").split("_")
                                    if len(parts) >= 2:
                                        doc.metadata["paper_number"] = parts[0]
                                        doc.metadata["variation"] = parts[1]
                            
                            all_docs.extend(docs)
                            logger.info(f"✅ Loaded {file_path.name} ({len(docs)} docs)")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to load {file_path.name}: {e}")

            # Log summary
            if all_docs:
                doc_types = {}
                for doc in all_docs:
                    doc_type = doc.metadata.get("type", "unknown")
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                logger.info(f"📚 Total documents loaded: {len(all_docs)}")
                for doc_type, count in doc_types.items():
                    logger.info(f"  - {doc_type}: {count} documents")
            else:
                logger.warning("⚠️ No documents found in the docs directory")
                
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

    def query_vector_store(self, query: str, k: int = 3, filters: Optional[Dict[str, str]] = None) -> List[Document]:
        """Query the vector store for relevant documents"""
        try:
            if not self.vector_store:
                logger.error("❌ Vector store not initialized")
                return []

            search_kwargs: Dict[str, Any] = {"k": k}
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

    def get_question_paper(self, paper_number: str) -> List[Document]:
        """Retrieve a specific question paper"""
        return self.query_vector_store(
            query="question paper",
            filters={"type": "question_paper", "paper_number": paper_number}
        )

    def get_marking_scheme(self, paper_number: str) -> List[Document]:
        """Retrieve marking scheme for a specific paper"""
        return self.query_vector_store(
            query="marking scheme",
            filters={"type": "marking_scheme", "paper_number": paper_number}
        )

    def get_student_answers(self, paper_number: str, variation: Optional[str] = None) -> List[Document]:
        """Retrieve student answer sheets"""
        filters = {"type": "student_answer", "paper_number": paper_number}
        if variation:
            filters["variation"] = variation
        
        return self.query_vector_store(
            query="student answer",
            filters=filters
        )

    def search_relevant_context(self, question: str, paper_number: Optional[str] = None) -> List[Document]:
        """Search for relevant context for question evaluation"""
        filters = {}
        if paper_number:
            filters["paper_number"] = paper_number
        
        return self.query_vector_store(
            query=question,
            k=5,
            filters=filters if filters else None
        )


if __name__ == "__main__":
    # Initialize the vector store manager
    manager = VectorStoreManager()
    
    # Setup vector store with exam documents
    logger.info("🚀 Setting up ProctorIQ Vector Store...")
    success = manager.setup_vector_store()
    
    if success:
        print("✅ Vector store setup completed successfully.")
        
        # Test queries
        print("\n🔍 Testing vector store queries...")
        
        # Test getting question paper
        qp_docs = manager.get_question_paper("1")
        print(f"📄 Found {len(qp_docs)} question paper documents for Paper 1")
        
        # Test getting marking scheme
        ms_docs = manager.get_marking_scheme("1")
        print(f"📋 Found {len(ms_docs)} marking scheme documents for Paper 1")
        
        # Test getting student answers
        sa_docs = manager.get_student_answers("1", "Variation1")
        print(f"✍️ Found {len(sa_docs)} student answer documents for Paper 1 Variation 1")
        
        # Test context search
        context_docs = manager.search_relevant_context(
            "What textual evidence tells us that Pip was trembling?",
            paper_number="1"
        )
        print(f"🔎 Found {len(context_docs)} relevant context documents")
        
    else:
        print("❌ Vector store setup failed.")
        print("💡 Make sure:")
        print("  - PINECONE_API_KEY is set in your .env file")
        print("  - Internet connection is available")
        print("  - Documents exist in the docs directory")