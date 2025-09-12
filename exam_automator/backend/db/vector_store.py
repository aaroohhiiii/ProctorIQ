import os
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings
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
        self.index_name = "proctoriq"  # Lowercase for Pinecone compliance
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
        """Load exam question papers and marking schemes only (NO student answers)"""
        all_docs = []

        try:
            # Only load official exam documents - NO student answers
            document_patterns = {
                "SQP*.txt": {"type": "question_paper", "priority": "high"},
                "MS*.txt": {"type": "marking_scheme", "priority": "high"},
                # Removed student answer patterns - they should NOT be in vector DB
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
                            
                            all_docs.extend(docs)
                            logger.info(f"✅ Loaded {file_path.name} ({len(docs)} docs)")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to load {file_path.name}: {e}")

            # Load structured JSON papers (most important for evaluation)
            structured_docs = self.load_structured_papers()
            all_docs.extend(structured_docs)

            # Log summary
            if all_docs:
                doc_types = {}
                for doc in all_docs:
                    doc_type = doc.metadata.get("type", "unknown")
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                logger.info(f"📚 Total documents loaded: {len(all_docs)}")
                for doc_type, count in doc_types.items():
                    logger.info(f"  - {doc_type}: {count} documents")
                logger.info("🚫 Student answers excluded from vector DB (processed dynamically)")
            else:
                logger.warning("⚠️ No documents found in the docs directory")
                
        except Exception as e:
            logger.error(f"❌ Failed to load documents: {e}")
            return []

        return all_docs

    def load_structured_papers(self) -> List[Document]:
        """Load structured JSON papers and convert to documents"""
        documents = []
        
        try:
            # Look for Paper*_Structured.json files
            json_files = list(self.data_dir.glob("Paper*_Structured.json"))
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        paper_data = json.load(f)
                    
                    # Extract paper number from filename
                    paper_number = paper_data['paper_info']['paper_id']
                    
                    # Create document for paper info
                    paper_info_text = f"Paper {paper_number}: {paper_data['paper_info']['title']}\n"
                    paper_info_text += f"Subject: {paper_data['paper_info']['subject']}\n"
                    paper_info_text += f"Max Marks: {paper_data['paper_info']['max_marks']}\n"
                    paper_info_text += f"Time: {paper_data['paper_info']['time_allowed']}\n"
                    paper_info_text += "Instructions: " + " ".join(paper_data['instructions']['general'])
                    
                    doc = Document(
                        page_content=paper_info_text,
                        metadata={
                            'type': 'structured_paper_info',
                            'paper_number': paper_number,
                            'filename': file_path.name,
                            'priority': 'high'
                        }
                    )
                    documents.append(doc)
                    
                    # Process each section
                    for section_key, section_data in paper_data['sections'].items():
                        section_text = f"Section: {section_data['title']} (Marks: {section_data['marks']})\n"
                        
                        # Process questions in each section
                        for question_key, question_data in section_data['questions'].items():
                            question_text = f"Question {question_data['id']} ({question_data['marks']} marks)\n"
                            question_text += f"Type: {question_data['type']}\n"
                            
                            # Add passage content if exists
                            if 'passage' in question_data:
                                passage = question_data['passage']
                                question_text += f"Passage: {passage['title']}\n"
                                if 'content' in passage:
                                    question_text += f"Content: {passage['content']}\n"
                            
                            # Add sub-questions and answers
                            if 'sub_questions' in question_data:
                                for sub_q_key, sub_q_data in question_data['sub_questions'].items():
                                    question_text += f"Sub-question {sub_q_key}: {sub_q_data['question']}\n"
                                    if 'answer' in sub_q_data:
                                        question_text += f"Answer: {sub_q_data['answer']}\n"
                                    if 'explanation' in sub_q_data:
                                        question_text += f"Explanation: {sub_q_data['explanation']}\n"
                            
                            doc = Document(
                                page_content=question_text,
                                metadata={
                                    'type': 'structured_question',
                                    'paper_number': paper_number,
                                    'section': section_key,
                                    'question_id': question_data['id'],
                                    'marks': question_data['marks'],
                                    'question_type': question_data['type'],
                                    'filename': file_path.name,
                                    'priority': 'high'
                                }
                            )
                            documents.append(doc)
                    
                    logger.info(f"✅ Loaded structured paper {file_path.name} ({len(documents)} docs so far)")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to load structured paper {file_path.name}: {e}")
            
            logger.info(f"📚 Total structured documents: {len(documents)}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to load structured papers: {e}")
            
        return documents

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

    # NOTE: Student answers should NOT be stored in vector DB
    # They are processed dynamically during evaluation
    # def get_student_answers(self, paper_number: str, variation: Optional[str] = None) -> List[Document]:
    #     """This method is disabled - student answers should be processed dynamically, not stored in vector DB"""
    #     logger.warning("🚫 Student answers should not be stored in vector database")
    #     return []

    def search_relevant_context(self, question: str, paper_number: Optional[str] = None) -> List[Document]:
        """Search for relevant context for question evaluation (official documents only)"""
        # Start with base filter to exclude student answers
        filters = {}
        
        # Note: We've already excluded student answers from vector store loading
        # This ensures only official documents (QP, MS, structured JSONs) are searched
        
        if paper_number:
            filters["paper_number"] = paper_number
        
        return self.query_vector_store(
            query=question,
            k=3,  # Reduced from 5 to 3 for faster retrieval
            filters=filters if filters else None
        )

    def search_batch_context(self, questions: List[str], paper_number: Optional[str] = None) -> Dict[str, List[Document]]:
        """
        Optimized batch search for multiple questions to reduce evaluation time
        
        Args:
            questions: List of question texts
            paper_number: Optional paper number to filter results
            
        Returns:
            Dictionary mapping question text to relevant documents
        """
        # Create a combined query from all questions for initial broad search
        combined_query = " ".join(questions[:3])  # Use first 3 questions to avoid overly long query
        
        filters = {}
        if paper_number:
            filters["paper_number"] = paper_number
        
        # Get a broader set of potentially relevant documents
        all_docs = self.query_vector_store(
            query=combined_query,
            k=8,  # Get more docs to distribute among questions
            filters=filters if filters else None
        )
        
        # Distribute documents to questions based on relevance
        result = {}
        for question in questions:
            # Simple keyword matching for quick distribution
            question_docs = []
            for doc in all_docs:
                doc_text = doc.page_content.lower()
                question_lower = question.lower()
                
                # Check for keyword overlap (more lenient)
                question_words = set(question_lower.split())
                doc_words = set(doc_text.split())
                overlap = len(question_words.intersection(doc_words))
                
                if overlap > 1:  # Reduced from 2 to 1 for more matches
                    question_docs.append(doc)
                    if len(question_docs) >= 2:  # Limit to 2 docs per question
                        break
            
            # Fallback: if no specific matches, give each question some general docs
            if not question_docs and all_docs:
                question_docs = all_docs[:2]  # Give first 2 docs as fallback
            
            result[question] = question_docs
        
        return result


if __name__ == "__main__":
    # Initialize the vector store manager
    manager = VectorStoreManager()
    
    # Setup vector store with exam documents
    logger.info("🚀 Setting up ProctorIQ Vector Store...")
    success = manager.setup_vector_store()
    
    if success:
        print("✅ Vector store setup completed successfully.")
        
        # Wait for index to sync
        import time
        print("⏳ Waiting for index synchronization...")
        time.sleep(3)
        
        # Test queries
        print("\n🔍 Testing vector store queries...")
        
        # Test getting question paper
        qp_docs = manager.get_question_paper("1")
        print(f"📄 Found {len(qp_docs)} question paper documents for Paper 1")
        if qp_docs:
            print(f"   Sample: {qp_docs[0].metadata.get('filename', 'unknown')}")
        
        # Test getting marking scheme
        ms_docs = manager.get_marking_scheme("1")
        print(f"📋 Found {len(ms_docs)} marking scheme documents for Paper 1")
        if ms_docs:
            print(f"   Sample: {ms_docs[0].metadata.get('filename', 'unknown')}")
        
        # NOTE: Student answers are NOT stored in vector DB - processed dynamically
        print("🚫 Student answers excluded from vector store (processed during evaluation)")
        
        # Test context search
        context_docs = manager.search_relevant_context(
            "What textual evidence tells us that Pip was trembling?",
            paper_number="1"
        )
        print(f"🔎 Found {len(context_docs)} relevant context documents")
        if context_docs:
            print(f"   Sample: {context_docs[0].metadata.get('filename', 'unknown')} ({context_docs[0].metadata.get('type', 'unknown')})")
        
    else:
        print("❌ Vector store setup failed.")
        print("💡 Make sure:")
        print("  - PINECONE_API_KEY is set in your .env file")
        print("  - Internet connection is available")
        print("  - Documents exist in the docs directory")