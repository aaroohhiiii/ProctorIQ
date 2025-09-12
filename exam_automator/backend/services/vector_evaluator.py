"""
Enhanced Exam Evaluator Service with Vector Database Integration
Automated evaluation of student answer sheets using OpenAI GPT models with context retrieval
"""

import json
import os
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
import re
from pathlib import Path

# Add the db directory to the path to import vector_store
sys.path.append(str(Path(__file__).parent.parent / "db"))

try:
    from vector_store import VectorStoreManager
    VECTOR_STORE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Vector store not available: {e}")
    VectorStoreManager = None
    VECTOR_STORE_AVAILABLE = False

@dataclass
class EvaluationResult:
    """Data class for storing evaluation results"""
    question_id: str
    student_answer: str
    marks_awarded: float
    total_marks: float
    feedback: str
    missing_elements: List[str]
    justification: str
    context_used: List[str]  # New field to track vector DB context

@dataclass
class OverallEvaluation:
    """Data class for overall evaluation summary"""
    total_marks_awarded: float
    total_possible_marks: float
    percentage: float
    section_wise_marks: Dict[str, Dict[str, float]]
    question_evaluations: List[EvaluationResult]
    overall_feedback: str
    strengths: List[str]
    areas_for_improvement: List[str]
    vector_context_summary: Dict[str, int]  # Summary of vector DB usage

class VectorEnhancedEvaluator:
    """Enhanced evaluator class with vector database integration"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4o-mini", use_vector_db: bool = True):
        """
        Initialize the evaluator with OpenAI client and vector store
        
        Args:
            openai_api_key: OpenAI API key
            model: GPT model to use for evaluation
            use_vector_db: Whether to use vector database for context retrieval
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.use_vector_db = use_vector_db
        self.evaluation_prompt = self._load_evaluation_prompt()
        
        # Initialize vector store manager if enabled
        if self.use_vector_db and VECTOR_STORE_AVAILABLE and VectorStoreManager:
            try:
                self.vector_manager = VectorStoreManager()
                print("✅ Vector database integration enabled")
            except Exception as e:
                print(f"⚠️ Vector database unavailable: {e}")
                self.use_vector_db = False
                self.vector_manager = None
        else:
            if self.use_vector_db:
                print("⚠️ Vector database requested but not available")
            self.use_vector_db = False
            self.vector_manager = None
    
    def _load_evaluation_prompt(self) -> str:
        """Load the evaluation prompt from ref.txt"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), "..", "ref.txt")
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Fallback evaluation prompt"""
        return """
        You are an expert English Language examiner following CBSE standards. 
        Evaluate student answers according to the provided marking scheme.
        Be fair, consistent, and provide detailed feedback for each question.
        Award partial marks appropriately and justify your assessment.
        """
    
    def get_vector_context(self, question_text: str, paper_number: Optional[str] = None) -> List[str]:
        """
        Retrieve relevant context from vector database
        
        Args:
            question_text: The question text to search for
            paper_number: Optional paper number to filter results
            
        Returns:
            List of relevant context strings
        """
        if not self.use_vector_db or not self.vector_manager:
            return []
        
        try:
            # Search for relevant context
            docs = self.vector_manager.search_relevant_context(question_text, paper_number)
            
            context_items = []
            for doc in docs[:2]:  # Reduced from 3 to 2 for faster processing
                doc_type = doc.metadata.get('type', 'unknown')
                filename = doc.metadata.get('filename', 'unknown')
                content = doc.page_content[:300]  # Reduced from 500 to 300 for faster processing
                
                context_items.append(f"[{doc_type.upper()} - {filename}]\n{content}")
            
            return context_items
            
        except Exception as e:
            print(f"⚠️ Vector context retrieval failed: {e}")
            return []

    def get_batch_vector_context(self, questions: List[str], paper_number: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Optimized batch retrieval of vector context for multiple questions
        
        Args:
            questions: List of question texts
            paper_number: Optional paper number to filter results
            
        Returns:
            Dictionary mapping question text to context strings
        """
        if not self.use_vector_db or not self.vector_manager:
            return {q: [] for q in questions}
        
        try:
            # Use batch search for better performance
            docs_by_question = self.vector_manager.search_batch_context(questions, paper_number)
            print(f"📊 Batch context mapping: {len(docs_by_question)} questions mapped")
            
            result = {}
            for question in questions:
                context_items = []
                docs = docs_by_question.get(question, [])
                print(f"📝 Question: '{question[:50]}...' → {len(docs)} docs")
                
                for doc in docs[:2]:  # Limit to 2 docs per question
                    doc_type = doc.metadata.get('type', 'unknown')
                    filename = doc.metadata.get('filename', 'unknown')
                    content = doc.page_content[:250]  # Shorter content for batch processing
                    
                    context_items.append(f"[{doc_type.upper()} - {filename}]\n{content}")
                
                result[question] = context_items
            
            return result
            
        except Exception as e:
            print(f"⚠️ Batch vector context retrieval failed: {e}")
            return {q: [] for q in questions}
    
    def load_structured_question_paper(self, json_path: str) -> Dict:
        """Load structured question paper with marking scheme"""
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Question paper JSON not found: {json_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in file: {json_path}")
    
    def extract_student_answers(self, answer_text: str) -> Dict[str, str]:
        """Extract individual question answers from student's answer sheet"""
        answers = {}
        
        # Split by common question patterns
        question_patterns = [
            r'(?:Question|Q\.?)\s*(\d+(?:\.\d+)?)[:\.\)\s]',
            r'(\d+(?:\.\d+)?)\s*[\.\)\-]',
            r'(?:Answer|Ans\.?)\s*(\d+(?:\.\d+)?)[:\.\)\s]'
        ]
        
        lines = answer_text.split('\n')
        current_question = None
        current_answer = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line starts a new question
            question_found = False
            for pattern in question_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous question if exists
                    if current_question and current_answer:
                        answers[current_question] = '\n'.join(current_answer).strip()
                    
                    # Start new question
                    current_question = match.group(1)
                    # Remove question number from line
                    remaining_text = re.sub(pattern, '', line, flags=re.IGNORECASE).strip()
                    if remaining_text:
                        current_answer = [remaining_text]
                    else:
                        current_answer = []
                    question_found = True
                    break
            
            if not question_found and current_question:
                current_answer.append(line)
        
        # Save the last question
        if current_question and current_answer:
            answers[current_question] = '\n'.join(current_answer).strip()
        
        return answers
    
    def evaluate_single_question_with_context(self, 
                                question_data: Dict, 
                                student_answer: str, 
                                question_id: str,
                                vector_context: List[str]) -> EvaluationResult:
        """
        Evaluate a single question with pre-retrieved vector context (optimized version)
        
        Args:
            question_data: Question information from structured JSON
            student_answer: Student's answer text
            question_id: Question identifier
            vector_context: Pre-retrieved vector context
            
        Returns:
            EvaluationResult object
        """
        try:
            question_text = question_data.get('question', '')
            
            # Build enhanced evaluation prompt with pre-retrieved context
            evaluation_request = f"""
{self.evaluation_prompt}

QUESTION DETAILS:
ID: {question_id}
Question: {question_text}
Total Marks: {question_data.get('marks', 0)}
Type: {question_data.get('type', 'unknown')}

MARKING SCHEME:
{json.dumps(question_data.get('marking_scheme', {}), indent=2)}

VECTOR DATABASE CONTEXT:
{chr(10).join(vector_context) if vector_context else "No relevant context found"}

STUDENT ANSWER:
{student_answer}

EVALUATION REQUIREMENTS:
1. Assess the answer against the marking scheme
2. Consider the vector database context for additional reference
3. Award marks fairly with proper justification
4. Identify missing elements
5. Provide constructive feedback

Please provide your evaluation in the following JSON format:
{{
    "marks_awarded": <number>,
    "feedback": "<detailed feedback string>",
    "missing_elements": ["<element1>", "<element2>"],
    "justification": "<explanation for marks awarded>"
}}
"""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert examiner. Respond only with valid JSON."
                    },
                    {"role": "user", "content": evaluation_request}
                ],
                max_tokens=800,  # Reduced from default for faster response
                temperature=0.1
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            try:
                # Look for JSON pattern
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    eval_result = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")
            except (json.JSONDecodeError, ValueError):
                # Fallback: Basic parsing from response text
                eval_result = {
                    'marks_awarded': 0,
                    'feedback': response_text,
                    'missing_elements': [],
                    'justification': 'Parsed from unstructured response'
                }
            
            # Create result object
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=float(eval_result.get('marks_awarded', 0)),
                total_marks=float(question_data.get('marks', 0)),
                feedback=eval_result.get('feedback', 'No feedback provided'),
                missing_elements=eval_result.get('missing_elements', []),
                justification=eval_result.get('justification', 'No justification provided'),
                context_used=vector_context
            )
            
        except Exception as e:
            print(f"❌ Error evaluating question {question_id}: {e}")
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=0.0,
                total_marks=float(question_data.get('marks', 0)),
                feedback=f"Evaluation failed: {str(e)}",
                missing_elements=[],
                justification="Technical error during evaluation",
                context_used=vector_context
            )
    
    def evaluate_single_question_fallback(self, question_id: str, question_data: dict, 
                               student_answer: str, marking_scheme: str) -> EvaluationResult:
        """
        Fallback method for backward compatibility - uses individual vector context retrieval
        """
        try:
            # Get vector context for this specific question
            if self.use_vector_db and self.vector_manager:
                vector_context = self.vector_manager.search_context(
                    question_data.get('question', ''), 
                    k=3
                )
            else:
                vector_context = []
            
            # Use the optimized method with the retrieved context
            return self.evaluate_single_question_with_context(
                question_data, student_answer, question_id, vector_context
            )
            
        except Exception as e:
            print(f"❌ Fallback evaluation failed for question {question_id}: {e}")
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=0.0,
                total_marks=float(question_data.get('marks', 0)),
                feedback=f"Evaluation failed: {str(e)}",
                missing_elements=[],
                justification="Technical error during evaluation",
                context_used=[]
            )

    def evaluate_single_question(self, 
                                question_data: Dict, 
                                student_answer: str, 
                                question_id: str,
                                paper_number: Optional[str] = None) -> EvaluationResult:
        """
        Evaluate a single question with vector database context
        
        Args:
            question_data: Question information from structured JSON
            student_answer: Student's answer text
            question_id: Question identifier
            paper_number: Paper number for context retrieval
            
        Returns:
            EvaluationResult object
        """
        try:
            # Get vector context for this question
            question_text = question_data.get('question', '')
            vector_context = self.get_vector_context(question_text, paper_number)
            
            # Build enhanced evaluation prompt
            evaluation_request = f"""
{self.evaluation_prompt}

QUESTION DETAILS:
ID: {question_id}
Question: {question_text}
Total Marks: {question_data.get('marks', 0)}
Type: {question_data.get('type', 'unknown')}

MARKING SCHEME:
{json.dumps(question_data.get('marking_scheme', {}), indent=2)}

VECTOR DATABASE CONTEXT:
{chr(10).join(vector_context) if vector_context else "No relevant context found"}

STUDENT ANSWER:
{student_answer}

EVALUATION REQUIREMENTS:
1. Assess the answer against the marking scheme
2. Consider the vector database context for additional reference
3. Award marks fairly with proper justification
4. Identify missing elements
5. Provide constructive feedback

Please provide your evaluation in the following JSON format:
{{
    "marks_awarded": <number>,
    "total_marks": <number>,
    "feedback": "<detailed feedback>",
    "missing_elements": ["<element1>", "<element2>"],
    "justification": "<explanation for marks awarded>",
    "context_sources": ["<source1>", "<source2>"]
}}
"""
            
            # Get evaluation from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert examiner with access to comprehensive marking resources."},
                    {"role": "user", "content": evaluation_request}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            response_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                # Clean the response text to extract JSON
                response_text = response_text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]  # Remove ```json
                if response_text.endswith('```'):
                    response_text = response_text[:-3]  # Remove ```
                
                # Find JSON object boundaries
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    eval_data = json.loads(json_text)
                else:
                    raise json.JSONDecodeError("No JSON object found", response_text, 0)
                    
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed for question {question_id}: {e}")
                eval_data = self._parse_fallback_response(response_text, question_data.get('marks', 0))
            
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=float(eval_data.get('marks_awarded', 0)),
                total_marks=float(question_data.get('marks', 0)),
                feedback=eval_data.get('feedback', 'No feedback provided'),
                missing_elements=eval_data.get('missing_elements', []),
                justification=eval_data.get('justification', 'No justification provided'),
                context_used=[ctx[:100] + "..." for ctx in vector_context]  # Store context summary
            )
            
        except Exception as e:
            print(f"⚠️ Error evaluating question {question_id}: {e}")
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=0.0,
                total_marks=float(question_data.get('marks', 0)),
                feedback=f"Evaluation error: {str(e)}",
                missing_elements=["Unable to evaluate"],
                justification="System error during evaluation",
                context_used=[]
            )
    
    def _parse_fallback_response(self, response_text: str, total_marks: float) -> Dict:
        """Parse response when JSON extraction fails"""
        marks_match = re.search(r'marks?[:\s]*(\d+(?:\.\d+)?)', response_text, re.IGNORECASE)
        marks_awarded = float(marks_match.group(1)) if marks_match else 0.0
        
        return {
            'marks_awarded': min(marks_awarded, total_marks),
            'total_marks': total_marks,
            'feedback': response_text[:300] + "..." if len(response_text) > 300 else response_text,
            'missing_elements': [],
            'justification': 'Parsed from natural language response',
            'context_sources': []
        }
    
    def evaluate_complete_exam(self, 
                              question_paper_path: str, 
                              student_answer_text: str) -> OverallEvaluation:
        """
        Evaluate complete exam with vector database enhancement
        
        Args:
            question_paper_path: Path to structured JSON question paper
            student_answer_text: Complete student answer text
            
        Returns:
            OverallEvaluation object
        """
        try:
            # Load question paper
            question_paper = self.load_structured_question_paper(question_paper_path)
            paper_number = question_paper['paper_info']['paper_id']
            
            # Extract student answers
            student_answers = self.extract_student_answers(student_answer_text)
            
            print(f"🔍 Evaluating Paper {paper_number} with {len(student_answers)} student answers")
            print(f"📊 Vector DB enabled: {self.use_vector_db}")
            
            all_evaluations = []
            section_wise_marks = {}
            vector_context_usage = {}
            
            # Process each section
            for section_key, section_data in question_paper['sections'].items():
                section_marks = {'awarded': 0.0, 'total': 0.0}
                
                for question_key, question_data in section_data['questions'].items():
                    question_id = question_data['id']
                    
                    # Get student answer for this question
                    student_answer = student_answers.get(question_id, "No answer provided")
                    
                    # Evaluate with vector context
                    evaluation = self.evaluate_single_question(
                        question_data, 
                        student_answer, 
                        question_id,
                        paper_number
                    )
                    
                    all_evaluations.append(evaluation)
                    section_marks['awarded'] += evaluation.marks_awarded
                    section_marks['total'] += evaluation.total_marks
                    
                    # Track vector context usage
                    if evaluation.context_used:
                        vector_context_usage[question_id] = len(evaluation.context_used)
                
                section_wise_marks[section_key] = section_marks
            
            # Calculate totals
            total_awarded = sum(eval.marks_awarded for eval in all_evaluations)
            total_possible = sum(eval.total_marks for eval in all_evaluations)
            percentage = (total_awarded / total_possible * 100) if total_possible > 0 else 0
            
            # Generate overall feedback
            overall_feedback = self._generate_overall_feedback(all_evaluations, percentage)
            strengths = self._identify_strengths(all_evaluations)
            improvements = self._identify_improvement_areas(all_evaluations)
            
            print(f"✅ Evaluation complete: {total_awarded:.1f}/{total_possible} ({percentage:.1f}%)")
            print(f"📊 Vector context used in {len(vector_context_usage)} questions")
            
            return OverallEvaluation(
                total_marks_awarded=total_awarded,
                total_possible_marks=total_possible,
                percentage=percentage,
                section_wise_marks=section_wise_marks,
                question_evaluations=all_evaluations,
                overall_feedback=overall_feedback,
                strengths=strengths,
                areas_for_improvement=improvements,
                vector_context_summary=vector_context_usage
            )
            
        except Exception as e:
            print(f"❌ Error during complete exam evaluation: {e}")
            raise
    
    def evaluate_answer_sheet(self, question_paper: dict, student_answer_text: str) -> OverallEvaluation:
        """
        Evaluate answer sheet using provided question paper dict and student answer text
        
        Args:
            question_paper: Question paper data as dictionary
            student_answer_text: Complete student answer text
            
        Returns:
            OverallEvaluation object
        """
        try:
            paper_number = question_paper.get('paper_info', {}).get('paper_id', '1')
            
            # Extract student answers
            student_answers = self.extract_student_answers(student_answer_text)
            
            print(f"🔍 Evaluating Paper {paper_number} with {len(student_answers)} student answers")
            print(f"📊 Vector DB enabled: {self.use_vector_db}")
            
            # OPTIMIZATION: Collect all questions for batch context retrieval
            all_questions = []
            question_map = {}
            
            for section_key, section_data in question_paper.get('sections', {}).items():
                for question_key, question_data in section_data.get('questions', {}).items():
                    question_text = question_data.get('question', '')
                    question_id = question_data['id']
                    all_questions.append(question_text)
                    question_map[question_text] = question_id
            
            # Batch retrieve vector context for all questions at once
            print(f"🚀 Batch retrieving context for {len(all_questions)} questions...")
            batch_context = self.get_batch_vector_context(all_questions, paper_number)
            print(f"✅ Context retrieved successfully")
            
            all_evaluations = []
            section_wise_marks = {}
            vector_context_usage = {}
            
            # Process each section
            for section_key, section_data in question_paper.get('sections', {}).items():
                section_marks = {'awarded': 0.0, 'total': 0.0}
                
                for question_key, question_data in section_data.get('questions', {}).items():
                    question_id = question_data['id']
                    question_text = question_data.get('question', '')
                    
                    # Find student answer for this question
                    student_answer = student_answers.get(question_id, "")
                    if not student_answer:
                        student_answer = student_answers.get(f"Q{question_id}", "")
                    if not student_answer:
                        student_answer = student_answers.get(f"q{question_id}", "")
                    
                    # Get pre-retrieved context for this question
                    vector_context = batch_context.get(question_text, [])
                    print(f"🔍 Question {question_id}: Found {len(vector_context)} context items")
                    
                    # Evaluate this question with pre-retrieved context
                    evaluation = self.evaluate_single_question_with_context(
                        question_data, 
                        student_answer, 
                        question_id,
                        vector_context
                    )
                    
                    all_evaluations.append(evaluation)
                    section_marks['awarded'] += evaluation.marks_awarded
                    section_marks['total'] += evaluation.total_marks
                    
                    # Track vector context usage
                    if evaluation.context_used:
                        vector_context_usage[question_id] = len(evaluation.context_used)
                        print(f"✅ Question {question_id}: Using {len(evaluation.context_used)} context items")
                    else:
                        print(f"⚠️ Question {question_id}: No context recorded in evaluation result")
                
                section_wise_marks[section_key] = section_marks
            
            # Calculate totals
            total_awarded = sum(eval.marks_awarded for eval in all_evaluations)
            total_possible = sum(eval.total_marks for eval in all_evaluations)
            percentage = (total_awarded / total_possible * 100) if total_possible > 0 else 0
            
            # Generate overall feedback
            overall_feedback = self._generate_overall_feedback(all_evaluations, percentage)
            
            # Identify strengths and improvements
            strengths = self._identify_strengths(all_evaluations)
            improvements = self._identify_improvement_areas(all_evaluations)
            
            print(f"✅ Evaluation complete: {total_awarded:.1f}/{total_possible} ({percentage:.1f}%)")
            print(f"📊 Vector context used in {len(vector_context_usage)} questions")
            
            return OverallEvaluation(
                total_marks_awarded=total_awarded,
                total_possible_marks=total_possible,
                percentage=percentage,
                section_wise_marks=section_wise_marks,
                question_evaluations=all_evaluations,
                overall_feedback=overall_feedback,
                strengths=strengths,
                areas_for_improvement=improvements,
                vector_context_summary=vector_context_usage
            )
            
        except Exception as e:
            print(f"❌ Error during answer sheet evaluation: {e}")
            raise
    
    def _generate_overall_feedback(self, evaluations: List[EvaluationResult], percentage: float) -> str:
        """Generate overall feedback based on evaluation results"""
        if percentage >= 80:
            performance = "excellent"
        elif percentage >= 65:
            performance = "good"
        elif percentage >= 50:
            performance = "satisfactory"
        else:
            performance = "needs improvement"
        
        return f"""
Overall Performance: {performance.title()} ({percentage:.1f}%)

The student has demonstrated {performance} understanding of the subject matter. 
{"Continue the excellent work and maintain this standard." if percentage >= 80 else 
 "Good effort with room for further improvement." if percentage >= 50 else
 "Significant improvement needed. Focus on understanding key concepts."}
"""
    
    def _identify_strengths(self, evaluations: List[EvaluationResult]) -> List[str]:
        """Identify student's strengths from evaluations"""
        strengths = []
        
        for eval_result in evaluations:
            if eval_result.marks_awarded / eval_result.total_marks >= 0.8:
                strengths.append(f"Strong performance in Question {eval_result.question_id}")
        
        if not strengths:
            strengths.append("Shows effort in attempting all questions")
        
        return strengths
    
    def _identify_improvement_areas(self, evaluations: List[EvaluationResult]) -> List[str]:
        """Identify areas needing improvement"""
        improvements = []
        
        for eval_result in evaluations:
            if eval_result.marks_awarded / eval_result.total_marks < 0.5:
                improvements.extend(eval_result.missing_elements[:2])
        
        return list(set(improvements))
    
    def generate_evaluation_report(self, evaluation: OverallEvaluation) -> str:
        """Generate detailed evaluation report with vector context information"""
        report = f"""
# ProctorIQ Evaluation Report (Vector-Enhanced)

## Overall Performance
- **Total Score**: {evaluation.total_marks_awarded:.1f}/{evaluation.total_possible_marks} 
- **Percentage**: {evaluation.percentage:.1f}%
- **Vector Context Used**: {len(evaluation.vector_context_summary)} questions enhanced

## Section-wise Performance
"""
        
        for section, marks in evaluation.section_wise_marks.items():
            percentage = (marks['awarded'] / marks['total'] * 100) if marks['total'] > 0 else 0
            report += f"- **{section.title()}**: {marks['awarded']:.1f}/{marks['total']} ({percentage:.1f}%)\n"
        
        report += f"""
## Question-wise Analysis

"""
        
        for eval_result in evaluation.question_evaluations:
            vector_indicator = "🔍" if eval_result.context_used else "📝"
            report += f"""
### {vector_indicator} Question {eval_result.question_id}
- **Marks**: {eval_result.marks_awarded:.1f}/{eval_result.total_marks}
- **Feedback**: {eval_result.feedback}
- **Justification**: {eval_result.justification}
"""
            if eval_result.context_used:
                report += f"- **Vector Context**: {len(eval_result.context_used)} sources consulted\n"
            
            if eval_result.missing_elements:
                report += f"- **Missing Elements**: {', '.join(eval_result.missing_elements)}\n"
        
        report += f"""
## Overall Feedback
{evaluation.overall_feedback}

## Strengths
{chr(10).join(f"- {strength}" for strength in evaluation.strengths)}

## Areas for Improvement
{chr(10).join(f"- {area}" for area in evaluation.areas_for_improvement)}

---
*Generated by ProctorIQ Vector-Enhanced Evaluator*
"""
        
        return report
    
    def save_evaluation_report(self, evaluation: OverallEvaluation, output_path: str):
        """Save evaluation report to file"""
        report = self.generate_evaluation_report(evaluation)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(report)
        
        print(f"📄 Evaluation report saved to: {output_path}")

# Utility functions for easy usage
def load_evaluator_from_env() -> VectorEnhancedEvaluator:
    """Load evaluator using OpenAI key from environment variables"""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    openai_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPEN_AI_KEY')
    if not openai_key:
        raise ValueError("OPENAI_API_KEY or OPEN_AI_KEY not found in environment variables")
    
    return VectorEnhancedEvaluator(openai_key)

def quick_evaluate(question_paper_path: str, student_answer_path: str) -> str:
    """Quick evaluation function with vector enhancement"""
    evaluator = load_evaluator_from_env()
    
    with open(student_answer_path, 'r', encoding='utf-8') as file:
        student_answer_text = file.read()
    
    evaluation = evaluator.evaluate_complete_exam(question_paper_path, student_answer_text)
    
    return evaluator.generate_evaluation_report(evaluation)

if __name__ == "__main__":
    # Example usage and testing
    try:
        print("🚀 Initializing Vector-Enhanced ProctorIQ Evaluator...")
        evaluator = load_evaluator_from_env()
        print("✅ Evaluator initialized successfully!")
        print(f"📊 Vector DB enabled: {evaluator.use_vector_db}")
        
        # You can test with:
        # evaluation = evaluator.evaluate_complete_exam(
        #     "path/to/Paper1_Structured.json",
        #     "path/to/student_answer.txt"
        # )
        # print(evaluator.generate_evaluation_report(evaluation))
        
    except Exception as e:
        print(f"❌ Error initializing evaluator: {e}")
