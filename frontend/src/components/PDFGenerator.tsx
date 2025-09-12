import React from 'react';
import jsPDF from 'jspdf';
import { EvaluationResults } from '../services/api';

interface PDFGeneratorProps {
  results: EvaluationResults;
  onComplete: () => void;
  onError: (error: string) => void;
}

export class PDFGenerator {
  static async generatePDFReport(results: EvaluationResults): Promise<void> {
    try {
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      let yPosition = 20;
      const margin = 20;
      const lineHeight = 7;

      // Helper function to add text with word wrapping
      const addText = (text: string, x: number, y: number, maxWidth: number, fontSize: number = 12): number => {
        pdf.setFontSize(fontSize);
        const lines = pdf.splitTextToSize(text, maxWidth);
        pdf.text(lines, x, y);
        return y + (lines.length * lineHeight);
      };

      // Header
      pdf.setFillColor(25, 118, 210); // Primary blue
      pdf.rect(0, 0, pageWidth, 30, 'F');
      
      pdf.setTextColor(255, 255, 255);
      pdf.setFontSize(24);
      pdf.setFont('helvetica', 'bold');
      pdf.text('ProctorIQ Evaluation Report', pageWidth / 2, 20, { align: 'center' });

      yPosition = 45;
      pdf.setTextColor(0, 0, 0);

      // Student Information Section
      pdf.setFontSize(16);
      pdf.setFont('helvetica', 'bold');
      yPosition = addText('Student Information', margin, yPosition, pageWidth - 2 * margin, 16);
      yPosition += 5;

      pdf.setDrawColor(200, 200, 200);
      pdf.line(margin, yPosition, pageWidth - margin, yPosition);
      yPosition += 10;

      pdf.setFontSize(12);
      pdf.setFont('helvetica', 'normal');
      yPosition = addText(`Student Name: ${results.student_info.name}`, margin, yPosition, pageWidth - 2 * margin);
      yPosition = addText(`Exam ID: ${results.student_info.exam_id}`, margin, yPosition, pageWidth - 2 * margin);
      yPosition = addText(`Paper Number: ${results.student_info.paper_number || 'N/A'}`, margin, yPosition, pageWidth - 2 * margin);
      yPosition = addText(`Evaluated On: ${new Date(results.processing_info.processing_timestamp).toLocaleString()}`, margin, yPosition, pageWidth - 2 * margin);
      yPosition += 10;

      // Overall Score Section
      pdf.setFontSize(16);
      pdf.setFont('helvetica', 'bold');
      yPosition = addText('Overall Performance', margin, yPosition, pageWidth - 2 * margin, 16);
      yPosition += 5;

      pdf.line(margin, yPosition, pageWidth - margin, yPosition);
      yPosition += 10;

      const evaluation = results.evaluation_results;
      const percentage = evaluation.percentage || 0;
      
      // Score box
      pdf.setFillColor(245, 245, 245);
      pdf.rect(margin, yPosition, pageWidth - 2 * margin, 25, 'F');
      
      pdf.setFontSize(20);
      pdf.setFont('helvetica', 'bold');
      pdf.setTextColor(25, 118, 210);
      pdf.text(`${percentage.toFixed(1)}%`, pageWidth / 2, yPosition + 10, { align: 'center' });
      
      pdf.setFontSize(12);
      pdf.setTextColor(0, 0, 0);
      pdf.text(`${evaluation.total_marks_awarded} / ${evaluation.total_possible_marks} marks`, pageWidth / 2, yPosition + 20, { align: 'center' });
      
      yPosition += 35;

      // Grade
      const grade = percentage >= 80 ? 'A' : percentage >= 60 ? 'B' : percentage >= 40 ? 'C' : 'D';
      yPosition = addText(`Grade: ${grade}`, margin, yPosition, pageWidth - 2 * margin);
      yPosition += 15;

      // Section-wise Performance
      if (evaluation.section_wise_marks) {
        pdf.setFontSize(16);
        pdf.setFont('helvetica', 'bold');
        yPosition = addText('Section-wise Performance', margin, yPosition, pageWidth - 2 * margin, 16);
        yPosition += 5;

        pdf.line(margin, yPosition, pageWidth - margin, yPosition);
        yPosition += 10;

        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'normal');

        Object.entries(evaluation.section_wise_marks).forEach(([section, marks]: [string, any]) => {
          const sectionPercentage = ((marks.awarded / marks.total) * 100).toFixed(1);
          yPosition = addText(`${section.replace('_', ' ').toUpperCase()}: ${marks.awarded}/${marks.total} (${sectionPercentage}%)`, margin + 10, yPosition, pageWidth - 2 * margin - 10);
        });

        yPosition += 10;
      }

      // Question-wise Evaluation
      if (evaluation.question_evaluations && evaluation.question_evaluations.length > 0) {
        // Check if we need a new page
        if (yPosition > pageHeight - 60) {
          pdf.addPage();
          yPosition = 20;
        }

        pdf.setFontSize(16);
        pdf.setFont('helvetica', 'bold');
        yPosition = addText('Question-wise Evaluation', margin, yPosition, pageWidth - 2 * margin, 16);
        yPosition += 5;

        pdf.line(margin, yPosition, pageWidth - margin, yPosition);
        yPosition += 10;

        evaluation.question_evaluations.forEach((question: any, index: number) => {
          // Check if we need a new page for each question
          if (yPosition > pageHeight - 40) {
            pdf.addPage();
            yPosition = 20;
          }

          pdf.setFontSize(14);
          pdf.setFont('helvetica', 'bold');
          yPosition = addText(`Question ${question.question_id}`, margin, yPosition, pageWidth - 2 * margin, 14);
          
          pdf.setFontSize(12);
          pdf.setFont('helvetica', 'normal');
          yPosition = addText(`Marks: ${question.marks_awarded}/${question.total_marks}`, margin + 10, yPosition, pageWidth - 2 * margin - 10);
          yPosition = addText(`Feedback: ${question.feedback}`, margin + 10, yPosition, pageWidth - 2 * margin - 10);
          
          if (question.missing_elements && question.missing_elements.length > 0) {
            yPosition = addText(`Missing Elements: ${question.missing_elements.join(', ')}`, margin + 10, yPosition, pageWidth - 2 * margin - 10);
          }
          
          yPosition += 8;
        });
      }

      // Overall Feedback
      if (evaluation.overall_feedback) {
        // Check if we need a new page
        if (yPosition > pageHeight - 60) {
          pdf.addPage();
          yPosition = 20;
        }

        pdf.setFontSize(16);
        pdf.setFont('helvetica', 'bold');
        yPosition = addText('Overall Feedback', margin, yPosition, pageWidth - 2 * margin, 16);
        yPosition += 5;

        pdf.line(margin, yPosition, pageWidth - margin, yPosition);
        yPosition += 10;

        pdf.setFontSize(12);
        pdf.setFont('helvetica', 'normal');
        yPosition = addText(evaluation.overall_feedback, margin, yPosition, pageWidth - 2 * margin);
      }

      // Footer
      const footerY = pageHeight - 15;
      pdf.setFontSize(10);
      pdf.setTextColor(128, 128, 128);
      pdf.text('Generated by ProctorIQ - Automated Exam Evaluation System', pageWidth / 2, footerY, { align: 'center' });
      pdf.text(`Generated on: ${new Date().toLocaleString()}`, pageWidth / 2, footerY + 5, { align: 'center' });

      // Generate filename
      const studentName = results.student_info.name.replace(/[^a-zA-Z0-9]/g, '_');
      const examId = results.student_info.exam_id.replace(/[^a-zA-Z0-9]/g, '_');
      const date = new Date().toISOString().split('T')[0];
      const filename = `ProctorIQ_Evaluation_${studentName}_${examId}_${date}.pdf`;

      // Save the PDF
      pdf.save(filename);

    } catch (error) {
      console.error('Error generating PDF:', error);
      throw new Error('Failed to generate PDF report');
    }
  }
}

export default PDFGenerator;
