"""
Exam Evaluator Service
Automated evaluation of student answer sheets using OpenAI GPT models
"""

import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from openai import OpenAI
import re

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

class ExamEvaluator:
    """Main evaluator class for automated exam assessment"""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize the evaluator with OpenAI client
        
        Args:
            openai_api_key: OpenAI API key
            model: GPT model to use for evaluation
        """
        self.client = OpenAI(api_key=openai_api_key)
        self.model = model
        self.evaluation_prompt = self._load_evaluation_prompt()
    
    def _load_evaluation_prompt(self) -> str:
        """Load the evaluation prompt from ref.txt"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), "..", "ref.txt")
            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            # Fallback prompt if ref.txt not found
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Fallback evaluation prompt"""
        return """
        You are an expert English Language examiner. Evaluate student answers according to the provided marking scheme.
        Be fair, consistent, and provide detailed feedback for each question.
        """
    
    def load_structured_question_paper(self, json_path: str) -> Dict:
        """
        Load structured question paper with marking scheme
        
        Args:
            json_path: Path to the structured JSON file
            
        Returns:
            Dictionary containing question paper structure and marking scheme
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Question paper JSON not found: {json_path}")
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON format in file: {json_path}")
    
    def extract_student_answers(self, answer_text: str) -> Dict[str, str]:
        """
        Extract individual question answers from student's answer sheet
        
        Args:
            answer_text: Raw text of student's answer sheet
            
        Returns:
            Dictionary mapping question IDs to student answers
        """
        answers = {}
        
        # Split by common question patterns
        question_patterns = [
            r'(?:Question|Q\.?)\s*(\d+(?:\.\d+)?)[:\.\)\s]',
            r'(\d+(?:\.\d+)?)[:\.\)\s]',
            r'Section\s*[A-C]\s*Question\s*(\d+)',
        ]
        
        # Try each pattern to split the text
        for pattern in question_patterns:
            matches = list(re.finditer(pattern, answer_text, re.IGNORECASE))
            if matches:
                for i, match in enumerate(matches):
                    question_id = match.group(1)
                    start_pos = match.end()
                    
                    # Find end position (next question or end of text)
                    if i + 1 < len(matches):
                        end_pos = matches[i + 1].start()
                    else:
                        end_pos = len(answer_text)
                    
                    answer = answer_text[start_pos:end_pos].strip()
                    answers[f"Q{question_id}"] = answer
                break
        
        # If no pattern worked, treat entire text as one answer
        if not answers:
            answers["Q1"] = answer_text.strip()
        
        return answers
    
    def evaluate_single_question(self, 
                                question_data: Dict, 
                                student_answer: str, 
                                question_id: str) -> EvaluationResult:
        """
        Evaluate a single question using OpenAI
        
        Args:
            question_data: Question data from structured JSON
            student_answer: Student's answer for this question
            question_id: Question identifier
            
        Returns:
            EvaluationResult object with detailed assessment
        """
        # Prepare evaluation prompt
        evaluation_prompt = f"""
{self.evaluation_prompt}

## QUESTION TO EVALUATE

**Question ID**: {question_id}
**Question Text**: {question_data.get('question_text', 'N/A')}
**Total Marks**: {question_data.get('marks', 0)}

**Marking Scheme**:
{json.dumps(question_data.get('marking_scheme', {}), indent=2)}

**Acceptable Answers**:
{json.dumps(question_data.get('acceptable_answers', []), indent=2)}

## STUDENT ANSWER

{student_answer}

## EVALUATION REQUIRED

Please provide a detailed evaluation in the following JSON format:
{{
    "marks_awarded": <float>,
    "total_marks": <float>,
    "feedback": "<detailed feedback>",
    "justification": "<why these marks were awarded>",
    "missing_elements": ["<list of missing elements that would earn more marks>"],
    "correct_elements": ["<list of correct elements identified>"],
    "areas_for_improvement": ["<specific suggestions for improvement>"]
}}

Ensure your evaluation is fair, consistent, and follows the marking scheme exactly.
"""
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert exam evaluator. Provide detailed, fair assessments."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=1000
            )
            
            # Parse response
            response_text = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                evaluation_data = json.loads(json_match.group())
            else:
                # Fallback parsing if JSON not found
                evaluation_data = self._parse_fallback_response(response_text, question_data.get('marks', 0))
            
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=float(evaluation_data.get('marks_awarded', 0)),
                total_marks=float(evaluation_data.get('total_marks', question_data.get('marks', 0))),
                feedback=evaluation_data.get('feedback', ''),
                missing_elements=evaluation_data.get('missing_elements', []),
                justification=evaluation_data.get('justification', '')
            )
            
        except Exception as e:
            # Error handling - return zero marks with error message
            return EvaluationResult(
                question_id=question_id,
                student_answer=student_answer,
                marks_awarded=0.0,
                total_marks=float(question_data.get('marks', 0)),
                feedback=f"Evaluation error: {str(e)}",
                missing_elements=[],
                justification="Unable to evaluate due to technical error"
            )
    
    def _parse_fallback_response(self, response_text: str, total_marks: float) -> Dict:
        """Parse response when JSON extraction fails"""
        return {
            'marks_awarded': 0.0,
            'total_marks': total_marks,
            'feedback': response_text,
            'justification': 'Parsed from non-JSON response',
            'missing_elements': []
        }
    
    def evaluate_complete_exam(self, 
                              question_paper_path: str, 
                              student_answer_text: str) -> OverallEvaluation:
        """
        Evaluate complete exam paper
        
        Args:
            question_paper_path: Path to structured JSON question paper
            student_answer_text: Complete student answer text
            
        Returns:
            OverallEvaluation object with comprehensive assessment
        """
        # Load question paper
        question_paper = self.load_structured_question_paper(question_paper_path)
        
        # Extract student answers
        student_answers = self.extract_student_answers(student_answer_text)
        
        # Initialize evaluation tracking
        question_evaluations = []
        section_wise_marks = {}
        total_marks_awarded = 0.0
        total_possible_marks = 0.0
        
        # Process each section
        for section_name, section_data in question_paper.get('sections', {}).items():
            section_marks_awarded = 0.0
            section_total_marks = 0.0
            
            # Process each question in section
            for question_id, question_data in section_data.get('questions', {}).items():
                # Get student answer for this question
                student_answer = student_answers.get(question_id, "No answer provided")
                
                # Evaluate question
                evaluation = self.evaluate_single_question(
                    question_data, 
                    student_answer, 
                    question_id
                )
                
                question_evaluations.append(evaluation)
                section_marks_awarded += evaluation.marks_awarded
                section_total_marks += evaluation.total_marks
            
            # Store section-wise marks
            section_wise_marks[section_name] = {
                'marks_awarded': section_marks_awarded,
                'total_marks': section_total_marks,
                'percentage': (section_marks_awarded / section_total_marks * 100) if section_total_marks > 0 else 0
            }
            
            total_marks_awarded += section_marks_awarded
            total_possible_marks += section_total_marks
        
        # Calculate overall percentage
        percentage = (total_marks_awarded / total_possible_marks * 100) if total_possible_marks > 0 else 0
        
        # Generate overall feedback
        overall_feedback = self._generate_overall_feedback(question_evaluations, percentage)
        strengths = self._identify_strengths(question_evaluations)
        areas_for_improvement = self._identify_improvement_areas(question_evaluations)
        
        return OverallEvaluation(
            total_marks_awarded=total_marks_awarded,
            total_possible_marks=total_possible_marks,
            percentage=percentage,
            section_wise_marks=section_wise_marks,
            question_evaluations=question_evaluations,
            overall_feedback=overall_feedback,
            strengths=strengths,
            areas_for_improvement=areas_for_improvement
        )
    
    def _generate_overall_feedback(self, evaluations: List[EvaluationResult], percentage: float) -> str:
        """Generate comprehensive overall feedback"""
        if percentage >= 90:
            performance_level = "Excellent"
        elif percentage >= 75:
            performance_level = "Good"
        elif percentage >= 60:
            performance_level = "Satisfactory"
        elif percentage >= 40:
            performance_level = "Needs Improvement"
        else:
            performance_level = "Poor"
        
        return f"""
Overall Performance: {performance_level} ({percentage:.1f}%)

The student has demonstrated {performance_level.lower()} understanding of the English language concepts tested in this examination. 
Key areas of strength and improvement have been identified in the detailed question-wise feedback.
"""
    
    def _identify_strengths(self, evaluations: List[EvaluationResult]) -> List[str]:
        """Identify student's strengths from evaluations"""
        strengths = []
        
        for eval_result in evaluations:
            if eval_result.marks_awarded / eval_result.total_marks >= 0.8:
                strengths.append(f"Strong performance in {eval_result.question_id}")
        
        if not strengths:
            strengths.append("Shows effort in attempting all questions")
        
        return strengths
    
    def _identify_improvement_areas(self, evaluations: List[EvaluationResult]) -> List[str]:
        """Identify areas needing improvement"""
        improvements = []
        
        for eval_result in evaluations:
            if eval_result.marks_awarded / eval_result.total_marks < 0.5:
                improvements.extend(eval_result.missing_elements[:2])  # Top 2 missing elements
        
        return list(set(improvements))  # Remove duplicates
    
    def generate_evaluation_report(self, evaluation: OverallEvaluation) -> str:
        """
        Generate a comprehensive evaluation report
        
        Args:
            evaluation: OverallEvaluation object
            
        Returns:
            Formatted evaluation report string
        """
        report = f"""
=== AUTOMATED EXAM EVALUATION REPORT ===

OVERALL PERFORMANCE
-------------------
Total Marks: {evaluation.total_marks_awarded:.1f} / {evaluation.total_possible_marks:.1f}
Percentage: {evaluation.percentage:.1f}%

SECTION-WISE BREAKDOWN
----------------------
"""
        
        for section, marks in evaluation.section_wise_marks.items():
            report += f"{section}: {marks['marks_awarded']:.1f}/{marks['total_marks']:.1f} ({marks['percentage']:.1f}%)\n"
        
        report += f"""
QUESTION-WISE EVALUATION
------------------------
"""
        
        for i, eval_result in enumerate(evaluation.question_evaluations, 1):
            report += f"""
{eval_result.question_id}: {eval_result.marks_awarded:.1f}/{eval_result.total_marks:.1f}
Feedback: {eval_result.feedback}
Justification: {eval_result.justification}
"""
            if eval_result.missing_elements:
                report += f"Missing Elements: {'; '.join(eval_result.missing_elements)}\n"
            report += "\n"
        
        report += f"""
OVERALL FEEDBACK
----------------
{evaluation.overall_feedback}

STRENGTHS
---------
{chr(10).join(f"• {strength}" for strength in evaluation.strengths)}

AREAS FOR IMPROVEMENT
---------------------
{chr(10).join(f"• {area}" for area in evaluation.areas_for_improvement)}

=== END OF REPORT ===
"""
        
        return report

# Utility functions for easy usage
def load_evaluator_from_env() -> ExamEvaluator:
    """Load evaluator using OpenAI key from environment variables"""
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    openai_key = os.getenv('OPEN_AI_KEY')
    if not openai_key:
        raise ValueError("OPEN_AI_KEY not found in environment variables")
    
    return ExamEvaluator(openai_key)

def quick_evaluate(question_paper_path: str, student_answer_path: str) -> str:
    """
    Quick evaluation function for easy testing
    
    Args:
        question_paper_path: Path to structured JSON question paper
        student_answer_path: Path to student answer text file
        
    Returns:
        Formatted evaluation report
    """
    evaluator = load_evaluator_from_env()
    
    # Read student answer
    with open(student_answer_path, 'r', encoding='utf-8') as file:
        student_answer_text = file.read()
    
    # Evaluate
    evaluation = evaluator.evaluate_complete_exam(question_paper_path, student_answer_text)
    
    # Generate report
    return evaluator.generate_evaluation_report(evaluation)

if __name__ == "__main__":
    # Example usage
    try:
        # Test with sample data
        evaluator = load_evaluator_from_env()
        print("Evaluator initialized successfully!")
        
        # You can test with:
        # evaluation = evaluator.evaluate_complete_exam(
        #     "path/to/Paper1_Structured.json",
        #     "path/to/student_answer.txt"
        # )
        # print(evaluator.generate_evaluation_report(evaluation))
        
    except Exception as e:
        print(f"Error initializing evaluator: {e}")
