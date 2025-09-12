#!/usr/bin/env python3
"""
Test script for Vector-Enhanced ProctorIQ Evaluator
Tests the integration between evaluator and vector database
"""

import os
import sys
from pathlib import Path

# Add the services directory to path
sys.path.append(str(Path(__file__).parent / "services"))

def test_vector_evaluator():
    """Test the vector-enhanced evaluator"""
    try:
        print("🚀 Testing Vector-Enhanced ProctorIQ Evaluator...")
        
        # Import the enhanced evaluator
        from vector_evaluator import VectorEnhancedEvaluator, load_evaluator_from_env
        
        # Initialize evaluator
        print("📊 Initializing evaluator...")
        evaluator = load_evaluator_from_env()
        print(f"✅ Evaluator initialized (Vector DB: {evaluator.use_vector_db})")
        
        # Test paths
        paper_path = "./docs/Paper1_Structured.json"
        student_answer_path = "./docs/Student_Answer_Paper1_Variation1.txt"
        
        # Check if test files exist
        if not os.path.exists(paper_path):
            print(f"❌ Test file not found: {paper_path}")
            return False
            
        if not os.path.exists(student_answer_path):
            print(f"❌ Test file not found: {student_answer_path}")
            return False
        
        print("📝 Running evaluation with vector enhancement...")
        
        # Load student answer
        with open(student_answer_path, 'r', encoding='utf-8') as file:
            student_answer_text = file.read()
        
        print(f"📄 Student answer loaded: {len(student_answer_text)} characters")
        
        # Run evaluation
        evaluation = evaluator.evaluate_complete_exam(paper_path, student_answer_text)
        
        # Display results
        print("\n" + "="*50)
        print("📊 EVALUATION RESULTS")
        print("="*50)
        print(f"Total Score: {evaluation.total_marks_awarded:.1f}/{evaluation.total_possible_marks}")
        print(f"Percentage: {evaluation.percentage:.1f}%")
        print(f"Vector Context Used: {len(evaluation.vector_context_summary)} questions")
        
        print("\n📋 Section-wise Performance:")
        for section, marks in evaluation.section_wise_marks.items():
            percentage = (marks['awarded'] / marks['total'] * 100) if marks['total'] > 0 else 0
            print(f"  {section}: {marks['awarded']:.1f}/{marks['total']} ({percentage:.1f}%)")
        
        print("\n🔍 Vector Context Usage:")
        for question_id, context_count in evaluation.vector_context_summary.items():
            print(f"  Question {question_id}: {context_count} context sources")
        
        # Generate and save report
        report_path = "./evaluation_reports/vector_enhanced_report.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        evaluator.save_evaluation_report(evaluation, report_path)
        
        print(f"\n✅ Test completed successfully!")
        print(f"📄 Report saved: {report_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vector_context():
    """Test vector context retrieval specifically"""
    try:
        print("\n🔍 Testing Vector Context Retrieval...")
        
        from vector_evaluator import VectorEnhancedEvaluator, load_evaluator_from_env
        
        evaluator = load_evaluator_from_env()
        
        if not evaluator.use_vector_db:
            print("⚠️ Vector DB not available for context testing")
            return False
        
        # Test context retrieval for different questions
        test_queries = [
            "What textual evidence tells us that Pip was trembling?",
            "Poetry analysis and literary devices",
            "Creative writing essay structure"
        ]
        
        for query in test_queries:
            print(f"\n📝 Query: {query}")
            context = evaluator.get_vector_context(query, "1")
            print(f"   Found {len(context)} context items")
            
            for i, ctx in enumerate(context[:2]):  # Show first 2
                print(f"   Context {i+1}: {ctx[:100]}...")
        
        print("✅ Vector context test completed")
        return True
        
    except Exception as e:
        print(f"❌ Vector context test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ProctorIQ Vector-Enhanced Evaluator Test Suite")
    print("="*60)
    
    # Change to backend directory
    os.chdir(Path(__file__).parent)
    
    # Run tests
    success1 = test_vector_context()
    success2 = test_vector_evaluator()
    
    print("\n" + "="*60)
    if success1 and success2:
        print("🎉 All tests passed! Vector-Enhanced Evaluator is ready.")
    else:
        print("❌ Some tests failed. Check the errors above.")
