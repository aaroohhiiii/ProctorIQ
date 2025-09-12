import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface UploadResponse {
  message: string;
  upload_id: string;
  files_count: number;
  metadata: {
    upload_id: string;
    student_name: string;
    exam_id: string;
    paper_number?: string;
    upload_timestamp: string;
    files: Array<{
      original_name: string;
      saved_name: string;
      file_path: string;
      file_size: number;
      content_type: string;
    }>;
    status: string;
    processed: boolean;
  };
}

export interface ProcessingResponse {
  message: string;
  upload_id: string;
  student_name: string;
  processed_files: Array<{
    file_name: string;
    extracted_text: string;
    text_length: number;
  }>;
  evaluation: {
    total_marks: number;
    possible_marks: number;
    percentage: number;
    overall_feedback: string;
  };
  detailed_results: any;
}

export interface UploadSession {
  upload_id: string;
  student_name: string;
  exam_id: string;
  upload_timestamp: string;
  status: string;
  processed: boolean;
  files_count: number;
}

export interface EvaluationResults {
  upload_id: string;
  student_info: {
    name: string;
    exam_id: string;
    paper_number?: string;
  };
  processing_info: {
    upload_timestamp: string;
    processing_timestamp: string;
    files_count: number;
  };
  evaluation_results: any;
}

export interface BatchUploadResponse {
  message: string;
  batch_id: string;
  total_students: number;
  uploaded_sessions: Array<{
    upload_id: string;
    student_name: string;
    files_count: number;
  }>;
}

export interface BatchProcessingResponse {
  message: string;
  batch_id: string;
  statistics: {
    total_students: number;
    successful: number;
    failed: number;
    average_percentage: number;
    total_marks_awarded: number;
    total_possible_marks: number;
  };
  results: Array<{
    upload_id: string;
    student_name: string;
    status: 'success' | 'error';
    evaluation?: {
      total_marks: number;
      possible_marks: number;
      percentage: number;
      overall_feedback: string;
    };
    error?: string;
  }>;
}

export interface BatchResults {
  batch_id: string;
  batch_info: {
    exam_id: string;
    paper_number?: string;
    total_students: number;
  };
  processing_info: {
    upload_timestamp: string;
    processing_timestamp: string;
  };
  statistics: {
    total_students: number;
    successful: number;
    failed: number;
    average_percentage: number;
    total_marks_awarded: number;
    total_possible_marks: number;
  };
  results: Array<{
    upload_id: string;
    student_name: string;
    status: 'success' | 'error';
    evaluation?: {
      total_marks: number;
      possible_marks: number;
      percentage: number;
      overall_feedback: string;
    };
    error?: string;
  }>;
}

class ApiService {
  private api = axios.create({
    baseURL: `${API_BASE_URL}/api/v1`,
    timeout: 120000, // Increased to 2 minutes for AI evaluation processing
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Upload answer sheet files
  async uploadAnswerSheet(
    files: File[],
    studentName: string,
    examId: string,
    paperNumber?: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    
    // Add files
    files.forEach((file) => {
      formData.append('files', file);
    });
    
    // Add form fields
    formData.append('student_name', studentName);
    formData.append('exam_id', examId);
    if (paperNumber) {
      formData.append('paper_number', paperNumber);
    }

    const response = await this.api.post('/upload/answer-sheet', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  // Process uploaded answer sheet
  async processAnswerSheet(uploadId: string): Promise<ProcessingResponse> {
    const response = await this.api.post(`/process/answer-sheet/${uploadId}`);
    return response.data;
  }

  // Get evaluation results
  async getEvaluationResults(uploadId: string): Promise<EvaluationResults> {
    const response = await this.api.get(`/results/${uploadId}`);
    return response.data;
  }

  // List all uploads
  async listUploads(): Promise<{ uploads: UploadSession[]; total_count: number }> {
    const response = await this.api.get('/uploads');
    return response.data;
  }

  // Get available question papers
  async getQuestionPapers(): Promise<any> {
    const response = await this.api.get('/papers');
    return response.data;
  }

  // Get system status
  async getSystemStatus(): Promise<any> {
    const response = await this.api.get('/status');
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/health`);
    return response.data;
  }

  // Upload multiple answer sheets (batch upload)
  async uploadMultipleAnswerSheets(formData: FormData): Promise<BatchUploadResponse> {
    const response = await this.api.post('/upload/multiple-answer-sheets', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  }

  // Process batch answer sheets
  async processBatchAnswerSheets(batchId: string): Promise<BatchProcessingResponse> {
    const response = await this.api.post(`/process/batch/${batchId}`);
    return response.data;
  }

  // Get batch evaluation results
  async getBatchEvaluationResults(batchId: string): Promise<BatchResults> {
    const response = await this.api.get(`/batch/results/${batchId}`);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
