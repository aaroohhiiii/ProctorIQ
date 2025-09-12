import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  CircularProgress,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  LinearProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
} from '@mui/material';
import {
  CloudUpload,
  InsertDriveFile,
  Delete,
  Send,
  CheckCircle,
  Error,
  ExpandMore,
  Group,
  Assessment,
  Timer,
} from '@mui/icons-material';

import { apiService } from '../services/api';

interface UploadedFile {
  file: File;
  studentName: string;
  preview?: string;
}

interface BatchProcessingResult {
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
}

interface BatchStatistics {
  total_students: number;
  successful: number;
  failed: number;
  average_percentage: number;
  total_marks_awarded: number;
  total_possible_marks: number;
}

const BatchUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [examId, setExamId] = useState('');
  const [paperNumber, setPaperNumber] = useState('');
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [processingResults, setProcessingResults] = useState<BatchProcessingResult[]>([]);
  const [statistics, setStatistics] = useState<BatchStatistics | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);

  // Extract student name from filename
  const extractStudentName = (filename: string): string => {
    // Remove extension
    const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
    
    // Common patterns to try
    const patterns = [
      // Pattern: StudentName_ExamName or StudentName-ExamName
      /^([^_-]+)(?:[_-].*)?$/,
      // Pattern: LastName_FirstName format
      /^([A-Za-z]+_[A-Za-z]+)(?:_.*)?$/,
      // Pattern: just use the filename if no pattern matches
      /^(.+)$/
    ];
    
    for (const pattern of patterns) {
      const match = nameWithoutExt.match(pattern);
      if (match) {
        return match[1].replace(/[_-]/g, ' ').trim();
      }
    }
    
    return nameWithoutExt;
  };

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      studentName: extractStudentName(file.name),
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
    }));
    setUploadedFiles((prev) => [...prev, ...newFiles]);
    setError(null);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpeg', '.jpg', '.png', '.bmp', '.tiff', '.gif'],
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/rtf': ['.rtf'],
    },
    multiple: true,
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const updateStudentName = (index: number, newName: string) => {
    setUploadedFiles((prev) => 
      prev.map((file, i) => 
        i === index ? { ...file, studentName: newName } : file
      )
    );
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleBatchUpload = async () => {
    if (!examId.trim()) {
      setError('Exam ID is required');
      return;
    }
    if (uploadedFiles.length === 0) {
      setError('Please upload at least one file');
      return;
    }

    // Check for duplicate student names
    const studentNames = uploadedFiles.map(f => f.studentName.trim().toLowerCase());
    const duplicates = studentNames.filter((name, index) => studentNames.indexOf(name) !== index);
    if (duplicates.length > 0) {
      setError(`Duplicate student names found. Please ensure all student names are unique.`);
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('exam_id', examId);
      if (paperNumber) {
        formData.append('paper_number', paperNumber);
      }

      // Append files with student names
      uploadedFiles.forEach((uploadedFile, index) => {
        formData.append('files', uploadedFile.file);
        formData.append('student_names', uploadedFile.studentName.trim());
      });

      const response = await apiService.uploadMultipleAnswerSheets(formData);
      
      setBatchId(response.batch_id);
      setSuccess(`Successfully uploaded ${uploadedFiles.length} student answer sheets. Batch ID: ${response.batch_id}`);
      
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleBatchProcess = async () => {
    if (!batchId) {
      setError('No batch to process');
      return;
    }

    setProcessing(true);
    setError(null);
    setProcessingProgress(0);

    try {
      // Start processing with progress simulation
      const progressInterval = setInterval(() => {
        setProcessingProgress(prev => {
          if (prev >= 95) {
            clearInterval(progressInterval);
            return 95; // Keep at 95% until actual completion
          }
          return prev + Math.random() * 15; // Random progress increments
        });
      }, 2000);

      const response = await apiService.processBatchAnswerSheets(batchId);
      
      clearInterval(progressInterval);
      setProcessingProgress(100);
      
      setProcessingResults(response.results);
      setStatistics(response.statistics);
      setSuccess(`Batch processing completed: ${response.statistics.successful}/${response.statistics.total_students} successful`);
      
    } catch (err: any) {
      setError(err.message || 'Processing failed');
    } finally {
      setProcessing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getGradeColor = (percentage: number) => {
    if (percentage >= 90) return '#4caf50'; // Green
    if (percentage >= 80) return '#8bc34a'; // Light green
    if (percentage >= 70) return '#ff9800'; // Orange
    if (percentage >= 60) return '#ff5722'; // Red-orange
    return '#f44336'; // Red
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" component="h1" gutterBottom align="center" color="primary">
        Batch Upload Answer Sheets
      </Typography>
      
      <Typography variant="h6" gutterBottom align="center" color="text.secondary" sx={{ mb: 4 }}>
        Upload multiple student answer sheets for automated evaluation
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* Exam Configuration */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Exam Configuration
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Exam ID"
                    value={examId}
                    onChange={(e) => setExamId(e.target.value)}
                    required
                    disabled={uploading || processing}
                    placeholder="e.g., MIDTERM-2024, FINAL-ENG"
                    helperText="Enter the unique identifier for this exam"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Paper Number (Optional)</InputLabel>
                    <Select
                      value={paperNumber}
                      label="Paper Number (Optional)"
                      onChange={(e) => setPaperNumber(e.target.value)}
                      disabled={uploading || processing}
                    >
                      <MenuItem value="">
                        <em>Auto-detect</em>
                      </MenuItem>
                      <MenuItem value="1">Paper 1</MenuItem>
                      <MenuItem value="2">Paper 2</MenuItem>
                      <MenuItem value="3">Paper 3</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* File Upload */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Upload Multiple Student Files
              </Typography>
              
              {/* Dropzone */}
              <Paper
                {...getRootProps()}
                sx={{
                  p: 4,
                  textAlign: 'center',
                  cursor: 'pointer',
                  border: '2px dashed',
                  borderColor: isDragActive ? 'primary.main' : 'grey.300',
                  backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
                  transition: 'all 0.3s ease',
                  mb: 3,
                  '&:hover': {
                    borderColor: 'primary.main',
                    backgroundColor: 'action.hover',
                  },
                }}
              >
                <input {...getInputProps()} />
                <CloudUpload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  {isDragActive
                    ? 'Drop student files here...'
                    : 'Drag & drop student answer sheets here'}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  or click to browse files
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Supported formats: PDF, Images (JPG/PNG/BMP/TIFF/GIF), Text files (TXT/MD/CSV), Word documents (DOC/DOCX), RTF (Max 50MB per file)
                </Typography>
              </Paper>

              {/* Uploaded Files List */}
              {uploadedFiles.length > 0 && (
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Uploaded Files ({uploadedFiles.length} students)
                  </Typography>
                  <List>
                    {uploadedFiles.map((uploadedFile, index) => (
                      <ListItem
                        key={index}
                        sx={{
                          border: 1,
                          borderColor: 'grey.200',
                          borderRadius: 1,
                          mb: 1,
                        }}
                      >
                        <ListItemIcon>
                          <InsertDriveFile color="primary" />
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                              <Typography variant="body1">
                                {uploadedFile.file.name}
                              </Typography>
                              <Chip
                                label={formatFileSize(uploadedFile.file.size)}
                                size="small"
                                variant="outlined"
                              />
                            </Box>
                          }
                          secondary={
                            <TextField
                              size="small"
                              label="Student Name"
                              value={uploadedFile.studentName}
                              onChange={(e) => updateStudentName(index, e.target.value)}
                              disabled={uploading || processing}
                              sx={{ mt: 1, maxWidth: 300 }}
                            />
                          }
                        />
                        <Button
                          size="small"
                          color="error"
                          onClick={() => removeFile(index)}
                          disabled={uploading || processing}
                          startIcon={<Delete />}
                        >
                          Remove
                        </Button>
                      </ListItem>
                    ))}
                  </List>

                  <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'center' }}>
                    <Button
                      variant="contained"
                      onClick={handleBatchUpload}
                      disabled={uploading || uploadedFiles.length === 0 || processing}
                      startIcon={uploading ? <CircularProgress size={20} /> : <CloudUpload />}
                      size="large"
                    >
                      {uploading ? 'Uploading...' : `Upload ${uploadedFiles.length} Files`}
                    </Button>
                    
                    {batchId && (
                      <Button
                        variant="contained"
                        color="secondary"
                        onClick={handleBatchProcess}
                        disabled={processing}
                        startIcon={processing ? <CircularProgress size={20} /> : <Send />}
                        size="large"
                      >
                        {processing ? 'Processing...' : 'Process Batch'}
                      </Button>
                    )}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Processing Progress */}
        {processing && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Processing Progress
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                  <Timer color="primary" />
                  <Typography variant="body1">
                    Processing {uploadedFiles.length} student answer sheets in parallel...
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={processingProgress} 
                  sx={{ height: 8, borderRadius: 4 }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {Math.round(processingProgress)}% Complete
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Batch Results */}
        {statistics && processingResults.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Batch Processing Results
                </Typography>

                {/* Statistics Summary */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'primary.light', color: 'white' }}>
                      <Group sx={{ fontSize: 40, mb: 1 }} />
                      <Typography variant="h4">{statistics.total_students}</Typography>
                      <Typography variant="body2">Total Students</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'success.light', color: 'white' }}>
                      <CheckCircle sx={{ fontSize: 40, mb: 1 }} />
                      <Typography variant="h4">{statistics.successful}</Typography>
                      <Typography variant="body2">Successful</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'error.light', color: 'white' }}>
                      <Error sx={{ fontSize: 40, mb: 1 }} />
                      <Typography variant="h4">{statistics.failed}</Typography>
                      <Typography variant="body2">Failed</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center', bgcolor: 'info.light', color: 'white' }}>
                      <Assessment sx={{ fontSize: 40, mb: 1 }} />
                      <Typography variant="h4">{Math.round(statistics.average_percentage)}%</Typography>
                      <Typography variant="body2">Average Score</Typography>
                    </Paper>
                  </Grid>
                </Grid>

                {/* Individual Results */}
                <Typography variant="h6" gutterBottom>
                  Individual Student Results
                </Typography>
                
                {processingResults.map((result, index) => (
                  <Accordion key={index}>
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                        <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                          {result.student_name}
                        </Typography>
                        <Chip
                          label={result.status}
                          color={getStatusColor(result.status)}
                          size="small"
                        />
                        {result.evaluation && (
                          <Chip
                            label={`${Math.round(result.evaluation.percentage)}%`}
                            sx={{ 
                              bgcolor: getGradeColor(result.evaluation.percentage),
                              color: 'white'
                            }}
                            size="small"
                          />
                        )}
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      {result.status === 'success' && result.evaluation ? (
                        <Box>
                          <Grid container spacing={2} sx={{ mb: 2 }}>
                            <Grid item xs={12} sm={4}>
                              <Typography variant="body2" color="text.secondary">Score</Typography>
                              <Typography variant="h6">
                                {result.evaluation.total_marks} / {result.evaluation.possible_marks}
                              </Typography>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <Typography variant="body2" color="text.secondary">Percentage</Typography>
                              <Typography variant="h6" sx={{ color: getGradeColor(result.evaluation.percentage) }}>
                                {Math.round(result.evaluation.percentage)}%
                              </Typography>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <Button
                                variant="outlined"
                                size="small"
                                onClick={() => navigate(`/results/${result.upload_id}`)}
                              >
                                View Details
                              </Button>
                            </Grid>
                          </Grid>
                          <Divider sx={{ my: 2 }} />
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            Overall Feedback:
                          </Typography>
                          <Typography variant="body1">
                            {result.evaluation.overall_feedback}
                          </Typography>
                        </Box>
                      ) : (
                        <Alert severity="error">
                          <Typography variant="body2">
                            Processing failed: {result.error}
                          </Typography>
                        </Alert>
                      )}
                    </AccordionDetails>
                  </Accordion>
                ))}
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Container>
  );
};

export default BatchUploadPage;
