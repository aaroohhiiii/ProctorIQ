import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Paper,
  CircularProgress,
  Alert,
  Button,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  LinearProgress,
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Download,
  Home,
  CloudUpload,
  Person,
  School,
  CalendarToday,
  Assessment,
  PictureAsPdf,
} from '@mui/icons-material';

import { apiService, EvaluationResults } from '../services/api';
import { PDFGenerator } from '../components/PDFGenerator';

const ResultsPage: React.FC = () => {
  const { uploadId } = useParams<{ uploadId: string }>();
  const [results, setResults] = useState<EvaluationResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (uploadId) {
      fetchResults(uploadId);
    }
  }, [uploadId]);

  const fetchResults = async (id: string) => {
    try {
      setLoading(true);
      const data = await apiService.getEvaluationResults(id);
      setResults(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch results');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getPercentageColor = (percentage: number) => {
    if (percentage >= 80) return 'success';
    if (percentage >= 60) return 'warning';
    return 'error';
  };

  const generatePDF = async () => {
    if (!results) return;

    try {
      setIsGeneratingPdf(true);
      await PDFGenerator.generatePDFReport(results);
    } catch (error) {
      console.error('Error generating PDF:', error);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading evaluation results...
        </Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert
          severity="error"
          action={
            <Button component={Link} to="/upload" color="inherit" size="small">
              Upload New
            </Button>
          }
        >
          {error}
        </Alert>
      </Container>
    );
  }

  if (!results) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Alert severity="info">No results found for this upload.</Alert>
      </Container>
    );
  }

  const evaluation = results.evaluation_results;
  const percentage = evaluation.percentage || 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <div ref={printRef}>
        {/* Header */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            ProctorIQ Evaluation Results
          </Typography>
          <Chip
            icon={<CheckCircle />}
            label="Evaluation Complete"
            color="success"
            size="medium"
          />
        </Box>

      {/* Student Information */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom color="primary">
            Student Information
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Person sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary">
                  Student Name
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={500}>
                {results.student_info.name}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <School sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary">
                  Exam ID
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={500}>
                {results.student_info.exam_id}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={4}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <CalendarToday sx={{ mr: 1, color: 'text.secondary' }} />
                <Typography variant="body2" color="text.secondary">
                  Evaluated On
                </Typography>
              </Box>
              <Typography variant="body1" fontWeight={500}>
                {formatDate(results.processing_info.processing_timestamp)}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Overall Score */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom color="primary">
            Overall Score
          </Typography>
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h2" component="div" color={`${getPercentageColor(percentage)}.main`}>
                  {percentage.toFixed(1)}%
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  {evaluation.total_marks_awarded} / {evaluation.total_possible_marks} marks
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box>
                <Typography variant="body2" gutterBottom>
                  Performance Distribution
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={percentage}
                  color={getPercentageColor(percentage)}
                  sx={{ height: 12, borderRadius: 6, mb: 2 }}
                />
                <Typography variant="body2" color="text.secondary">
                  Grade: {percentage >= 80 ? 'A' : percentage >= 60 ? 'B' : percentage >= 40 ? 'C' : 'D'}
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Section-wise Results */}
      {evaluation.section_wise_marks && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Section-wise Performance
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(evaluation.section_wise_marks).map(([section, marks]: [string, any]) => (
                <Grid item xs={12} sm={6} md={4} key={section}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="subtitle1" gutterBottom>
                      {section.replace('_', ' ').toUpperCase()}
                    </Typography>
                    <Typography variant="h6" color="primary">
                      {marks.awarded} / {marks.total}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {((marks.awarded / marks.total) * 100).toFixed(1)}%
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Detailed Question Results */}
      {evaluation.question_evaluations && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Question-wise Evaluation
            </Typography>
            <List>
              {evaluation.question_evaluations.map((question: any, index: number) => (
                <React.Fragment key={index}>
                  <ListItem sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                    <Box sx={{ width: '100%', mb: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="subtitle1" fontWeight={600}>
                          Question {question.question_id}
                        </Typography>
                        <Chip
                          label={`${question.marks_awarded}/${question.total_marks}`}
                          color={question.marks_awarded === question.total_marks ? 'success' : 'warning'}
                          size="small"
                        />
                      </Box>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {question.feedback}
                    </Typography>
                    {question.missing_elements && question.missing_elements.length > 0 && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="error.main">
                          Missing elements: {question.missing_elements.join(', ')}
                        </Typography>
                      </Box>
                    )}
                  </ListItem>
                  {index < evaluation.question_evaluations.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Overall Feedback */}
      {evaluation.overall_feedback && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="primary">
              Overall Feedback
            </Typography>
            <Typography variant="body1" sx={{ whiteSpace: 'pre-line' }}>
              {evaluation.overall_feedback}
            </Typography>
          </CardContent>
        </Card>
      )}
      </div>

      {/* Action Buttons */}
      <Box id="action-buttons" sx={{ textAlign: 'center', mt: 4 }}>
        <Button
          onClick={generatePDF}
          variant="contained"
          startIcon={isGeneratingPdf ? <CircularProgress size={20} /> : <PictureAsPdf />}
          disabled={isGeneratingPdf}
          sx={{ mr: 2 }}
        >
          {isGeneratingPdf ? 'Generating PDF...' : 'Download PDF Report'}
        </Button>
        <Button
          component={Link}
          to="/"
          variant="outlined"
          startIcon={<Home />}
          sx={{ mr: 2 }}
        >
          Home
        </Button>
        <Button
          component={Link}
          to="/upload"
          variant="contained"
          startIcon={<CloudUpload />}
        >
          Upload Another
        </Button>
      </Box>
    </Container>
  );
};

export default ResultsPage;
