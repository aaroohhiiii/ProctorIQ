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
} from '@mui/material';
import {
  CloudUpload,
  InsertDriveFile,
  Delete,
  Send,
  CheckCircle,
  Error,
} from '@mui/icons-material';

import { apiService } from '../services/api';

interface UploadedFile {
  file: File;
  preview?: string;
}

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [studentName, setStudentName] = useState('');
  const [examId, setExamId] = useState('');
  const [paperNumber, setPaperNumber] = useState('');
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
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

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleSubmit = async () => {
    if (!studentName.trim()) {
      setError('Student name is required');
      return;
    }
    if (!examId.trim()) {
      setError('Exam ID is required');
      return;
    }
    if (uploadedFiles.length === 0) {
      setError('Please upload at least one file');
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      // Upload files
      const uploadResponse = await apiService.uploadAnswerSheet(
        uploadedFiles.map((f) => f.file),
        studentName.trim(),
        examId.trim(),
        paperNumber.trim() || undefined
      );

      setSuccess('Files uploaded successfully! AI evaluation in progress...');
      setProcessing(true);
      setUploading(false); // Upload is complete, now processing

      // Process the uploaded files (this may take 1-2 minutes)
      const processResponse = await apiService.processAnswerSheet(uploadResponse.upload_id);

      setSuccess('Evaluation completed successfully!');
      
      // Navigate to results page after a short delay
      setTimeout(() => {
        navigate(`/results/${uploadResponse.upload_id}`);
      }, 2000);

    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
    } finally {
      setUploading(false);
      setProcessing(false);
    }
  };

  const isFormValid = studentName.trim() && examId.trim() && uploadedFiles.length > 0;

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom textAlign="center">
        Upload Answer Sheet
      </Typography>
      <Typography variant="body1" textAlign="center" color="text.secondary" sx={{ mb: 4 }}>
        Upload student answer sheets for automated evaluation
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert 
          severity="success" 
          sx={{ mb: 3 }}
          icon={processing ? <CircularProgress size={20} /> : <CheckCircle />}
        >
          <Box display="flex" alignItems="center" gap={1}>
            {success}
            {processing && (
              <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                (This may take 1-2 minutes for AI evaluation)
              </Typography>
            )}
          </Box>
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* Student Information */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Student Information
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Student Name"
                    value={studentName}
                    onChange={(e) => setStudentName(e.target.value)}
                    required
                    disabled={uploading || processing}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Exam ID"
                    value={examId}
                    onChange={(e) => setExamId(e.target.value)}
                    required
                    disabled={uploading || processing}
                    placeholder="e.g., MIDTERM-2024, FINAL-ENG"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Paper Number (Optional)</InputLabel>
                    <Select
                      value={paperNumber}
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
                Upload Files
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
                  {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
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
                    Uploaded Files ({uploadedFiles.length})
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
                          primary={uploadedFile.file.name}
                          secondary={`${formatFileSize(uploadedFile.file.size)} • ${uploadedFile.file.type}`}
                        />
                        <Chip
                          label={uploadedFile.file.type.startsWith('image/') ? 'Image' : 'PDF'}
                          size="small"
                          color="primary"
                          variant="outlined"
                          sx={{ mr: 1 }}
                        />
                        <Button
                          size="small"
                          color="error"
                          onClick={() => removeFile(index)}
                          disabled={uploading || processing}
                        >
                          <Delete />
                        </Button>
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Submit Button */}
        <Grid item xs={12}>
          <Box sx={{ textAlign: 'center' }}>
            <Button
              variant="contained"
              size="large"
              onClick={handleSubmit}
              disabled={!isFormValid || uploading || processing}
              startIcon={
                uploading || processing ? (
                  <CircularProgress size={20} />
                ) : (
                  <Send />
                )
              }
              sx={{ px: 6, py: 1.5 }}
            >
              {processing
                ? 'AI Evaluation in Progress...'
                : uploading
                ? 'Uploading...'
                : 'Submit for Evaluation'}
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Container>
  );
};

export default UploadPage;
