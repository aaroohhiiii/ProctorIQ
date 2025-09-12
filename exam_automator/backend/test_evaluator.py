#!/usr/bin/env python3
"""
ProctorIQ Evaluator Test Script
Test the automated evaluation system with sample data
"""

import os
import sys
from evaluator import ExamEvaluator

def main():
    """Test the ExamEvaluator with sample data"""
    print("🚀 ProctorIQ Automated Evaluation System")
    print("=" * 50)
    
    # File paths (corrected to actual structure)
    paper_path = "./docs/Paper1_Structured.json"
    answers_path = "./docs/Student_Answer_Better.txt"
    output_path = "./evaluation_reports/Paper1_Better_Student_Evaluation.md"
    
    # Create output directory
    os.makedirs("./evaluation_reports", exist_ok=True)
    
    print(f"📄 Question Paper: {paper_path}")
    print(f"📝 Student Answers: {answers_path}")
    print(f"📊 Output Report: {output_path}")
    print("-" * 50)
    
    # Check if files exist
    if not os.path.exists(paper_path):
        print(f"❌ Error: Paper file not found at {paper_path}")
        return
    
    if not os.path.exists(answers_path):
        print(f"❌ Error: Student answers file not found at {answers_path}")
        return
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in the .env file")
        return
    
    print("✅ All files found. Starting evaluation...")
    print("🤖 Initializing evaluator...")
    
    try:
        # Initialize evaluator
        evaluator = ExamEvaluator()
        print("✅ Evaluator initialized successfully!")
        print("🤖 Calling OpenAI API for evaluation...")
        
        # Perform evaluation
        result = evaluator.evaluate_answers(paper_path, answers_path)
        
        if result["success"]:
            print("✅ Evaluation completed successfully!")
            
            # Save the report
            evaluator.save_evaluation_report(result, output_path)
            print(f"📁 Report saved to: {output_path}")
            
            # Show preview
            print("\n" + "=" * 50)
            print("📋 EVALUATION PREVIEW:")
            print("=" * 50)
            
            preview = result["evaluation"][:800] + "..." if len(result["evaluation"]) > 800 else result["evaluation"]
            print(preview)
            
            print("\n" + "=" * 50)
            print(f"📊 Full report available at: {output_path}")
            print("🎉 ProctorIQ evaluation completed!")
            
        else:
            print(f"❌ Evaluation failed: {result['error']}")
    
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
