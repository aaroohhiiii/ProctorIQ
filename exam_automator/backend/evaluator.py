import os
import json
from typing import Dict, List, Any, Tuple
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExamEvaluator:
    """
    ProctorIQ Exam Evaluator using OpenAI GPT for automated answer sheet evaluation
    """
    
    def __init__(self):
        """Initialize the evaluator with OpenAI client and system prompt"""
        # Load environment variables from multiple possible locations
        load_dotenv()  # Load from current directory
        load_dotenv('/Users/karthiksarma/Desktop/proctoriq/.env')  # Load from project root
        
        # Try different possible key names
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('OPEN_AI_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY or OPEN_AI_KEY in your .env file")
        
        self.client = OpenAI(api_key=api_key)
        self.system_prompt = self._load_system_prompt()
        
    def _load_system_prompt(self) -> str:
        """Load the detailed evaluation prompt from ref.txt"""
        try:
            with open('ref.txt', 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error("ref.txt not found. Using default prompt.")
            return "You are an expert exam evaluator. Evaluate the student answers according to the marking scheme."
    
    def load_structured_paper(self, paper_path: str) -> Dict[str, Any]:
        """Load structured question paper with marking scheme"""
        try:
            with open(paper_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Paper file not found: {paper_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in paper file: {paper_path}")
            raise
    
    def load_student_answers(self, answers_path: str) -> str:
        """Load student answer sheet"""
        try:
            with open(answers_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Student answers file not found: {answers_path}")
            raise
    
    def create_evaluation_prompt(self, structured_paper: Dict[str, Any], student_answers: str) -> str:
        """Create the evaluation prompt combining marking scheme and student answers"""
        
        prompt = f"""
## EVALUATION TASK

You are evaluating a {structured_paper['paper_info']['subject']} paper for {structured_paper['paper_info']['class']}.

### PAPER DETAILS:
- **Paper**: {structured_paper['paper_info']['title']}
- **Academic Year**: {structured_paper['paper_info']['academic_session']}
- **Total Marks**: {structured_paper['paper_info']['max_marks']}
- **Duration**: {structured_paper['paper_info']['time_allowed']}

### SECTION-WISE BREAKDOWN:
"""
        
        for section_key, section in structured_paper['sections'].items():
            prompt += f"- **{section['title']}**: {section['marks']} marks\n"
        
        prompt += "\n### DETAILED MARKING SCHEME:\n\n"
        
        # Add detailed marking scheme for each section
        for section_key, section in structured_paper['sections'].items():
            prompt += f"## {section['title']} ({section['marks']} marks)\n\n"
            
            for question_key, question in section['questions'].items():
                prompt += f"### Question {question['id']} ({question['marks']} marks)\n"
                
                if 'passage' in question:
                    prompt += f"**Passage**: {question['passage']['title']}\n\n"
                
                if 'sub_questions' in question:
                    for sub_q_key, sub_q in question['sub_questions'].items():
                        prompt += f"#### Sub-question {sub_q_key} ({sub_q['marks']} marks)\n"
                        prompt += f"**Question**: {sub_q['question']}\n"
                        
                        if 'answer' in sub_q:
                            prompt += f"**Expected Answer**: {sub_q['answer']}\n"
                        
                        if 'marking_criteria' in sub_q:
                            prompt += "**Marking Criteria**:\n"
                            for criteria_key, criteria in sub_q['marking_criteria'].items():
                                prompt += f"- **{criteria_key}**: {criteria}\n"
                        
                        prompt += "\n"
                else:
                    # Direct question without sub-questions
                    if 'question' in question:
                        prompt += f"**Question**: {question['question']}\n"
                    
                    if 'answer' in question:
                        prompt += f"**Expected Answer**: {question['answer']}\n"
                    
                    if 'marking_criteria' in question:
                        prompt += "**Marking Criteria**:\n"
                        for criteria_key, criteria in question['marking_criteria'].items():
                            prompt += f"- **{criteria_key}**: {criteria}\n"
                
                prompt += "\n---\n\n"
        
        prompt += f"""
### STUDENT ANSWERS TO EVALUATE:

```
{student_answers}
```

### CRITICAL EVALUATION INSTRUCTIONS:

Please evaluate the student's answers according to the marking scheme provided above. Follow these essential guidelines:

**MARKING APPROACH:**
1. Be FAIR and BALANCED - look for evidence of understanding, not just perfect answers
2. Award PARTIAL MARKS generously when students show some comprehension
3. For MCQs: Only correct option gets full marks, incorrect options get 0
4. For written answers: Use 0.5 mark increments to reward partial understanding
5. CALCULATE TOTALS CORRECTLY - double-check all arithmetic

**For each question and sub-question, provide:**
1. Quote the relevant part of the student's answer
2. Award marks based on the marking criteria (be generous with partial marks)
3. Provide detailed justification for marks awarded/deducted
4. Acknowledge what the student did correctly first
5. Identify missing elements that could have earned additional marks
6. Provide constructive feedback for improvement

**IMPORTANT:** Ensure your final total calculation is mathematically correct. Add up all individual marks to get section totals, then add section totals for the grand total.

Provide your evaluation in the following format:

## EVALUATION REPORT

### Paper: {structured_paper['paper_info']['title']}
### Academic Session: {structured_paper['paper_info']['academic_session']}
### Total Marks: {structured_paper['paper_info']['max_marks']}

---

[For each section, provide detailed evaluation with fair marking]

### SECTION TOTALS:
- **Section A (Reading Skills)**: X/22 marks
- **Section B (Creative Writing)**: X/18 marks  
- **Section C (Literature)**: X/40 marks

### FINAL SUMMARY:
- **Total Marks Obtained**: X/{structured_paper['paper_info']['max_marks']} (Verify this calculation)
- **Percentage**: X%
- **Overall Performance**: [Brief summary]
- **Key Strengths**: [List specific strengths demonstrated]
- **Areas for Improvement**: [List specific areas with actionable suggestions]
- **Recommendations**: [Constructive suggestions for future improvement]
"""
        
        return prompt
    
    def evaluate_answers(self, 
                        paper_path: str, 
                        answers_path: str, 
                        model: str = "gpt-4o-mini",
                        temperature: float = 0.1) -> Dict[str, Any]:
        """
        Main evaluation function that processes student answers against marking scheme
        
        Args:
            paper_path: Path to structured question paper JSON
            answers_path: Path to student answers text file
            model: OpenAI model to use for evaluation
            temperature: Temperature for model response (lower = more consistent)
            
        Returns:
            Dictionary containing evaluation results
        """
        
        try:
            # Load paper and answers
            logger.info(f"Loading structured paper from: {paper_path}")
            structured_paper = self.load_structured_paper(paper_path)
            
            logger.info(f"Loading student answers from: {answers_path}")
            student_answers = self.load_student_answers(answers_path)
            
            # Create evaluation prompt
            logger.info("Creating evaluation prompt...")
            evaluation_prompt = self.create_evaluation_prompt(structured_paper, student_answers)
            
            # Call OpenAI API for evaluation
            logger.info(f"Calling OpenAI API with model: {model}")
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=temperature,
                max_tokens=4000
            )
            
            evaluation_result = response.choices[0].message.content
            
            # Parse and structure the result
            result = {
                "paper_info": {
                    "title": structured_paper['paper_info']['title'],
                    "academic_session": structured_paper['paper_info']['academic_session'],
                    "max_marks": structured_paper['paper_info']['max_marks'],
                    "subject": structured_paper['paper_info']['subject']
                },
                "evaluation": evaluation_result,
                "model_used": model,
                "evaluation_timestamp": None,  # You can add timestamp if needed
                "success": True
            }
            
            logger.info("Evaluation completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error during evaluation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "evaluation": None
            }
    
    def save_evaluation_report(self, evaluation_result: Dict[str, Any], output_path: str):
        """Save evaluation report to file"""
        try:
            if evaluation_result["success"]:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write("# PROCTORIQ AUTOMATED EVALUATION REPORT\n\n")
                    f.write(f"**Paper**: {evaluation_result['paper_info']['title']}\n")
                    f.write(f"**Academic Session**: {evaluation_result['paper_info']['academic_session']}\n")
                    f.write(f"**Subject**: {evaluation_result['paper_info']['subject']}\n")
                    f.write(f"**Model Used**: {evaluation_result['model_used']}\n\n")
                    f.write("---\n\n")
                    f.write(evaluation_result["evaluation"])
                
                logger.info(f"Evaluation report saved to: {output_path}")
            else:
                logger.error(f"Cannot save report due to evaluation error: {evaluation_result['error']}")
                
        except Exception as e:
            logger.error(f"Error saving evaluation report: {str(e)}")
    
    def batch_evaluate(self, evaluations: List[Tuple[str, str, str]]) -> List[Dict[str, Any]]:
        """
        Batch evaluation for multiple student answer sheets
        
        Args:
            evaluations: List of tuples (paper_path, answers_path, output_path)
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for i, (paper_path, answers_path, output_path) in enumerate(evaluations, 1):
            logger.info(f"Processing evaluation {i}/{len(evaluations)}")
            
            result = self.evaluate_answers(paper_path, answers_path)
            
            if result["success"]:
                self.save_evaluation_report(result, output_path)
            
            results.append(result)
        
        return results

# Example usage and testing functions
def test_evaluator():
    """Test function to demonstrate evaluator usage"""
    evaluator = ExamEvaluator()
    
    # Test with Paper 1 and Student Answer Paper 1 Variation 1
    paper_path = "docs/Paper1_Structured.json"
    answers_path = "docs/Student_Answer_Paper1_Variation1.txt"
    output_path = "evaluation_reports/Paper1_Student1_Report.md"
    
    # Create reports directory if it doesn't exist
    os.makedirs("evaluation_reports", exist_ok=True)
    
    print("🚀 Starting ProctorIQ Evaluation...")
    print(f"📄 Paper: {paper_path}")
    print(f"📝 Student Answers: {answers_path}")
    print(f"📊 Report Output: {output_path}")
    print("="*50)
    
    # Perform evaluation
    result = evaluator.evaluate_answers(paper_path, answers_path)
    
    if result["success"]:
        print("✅ Evaluation completed successfully!")
        evaluator.save_evaluation_report(result, output_path)
        print(f"📁 Report saved to: {output_path}")
        
        # Print a preview of the evaluation
        print("\n" + "="*50)
        print("📋 EVALUATION PREVIEW:")
        print("="*50)
        preview = result["evaluation"][:500] + "..." if len(result["evaluation"]) > 500 else result["evaluation"]
        print(preview)
        
    else:
        print(f"❌ Evaluation failed: {result['error']}")

if __name__ == "__main__":
    test_evaluator()
