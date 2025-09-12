import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  CloudUpload,
  Visibility,
  Refresh,
  CheckCircle,
  Schedule,
  Error,
} from '@mui/icons-material';

import { apiService, UploadSession } from '../services/api';

const HistoryPage: React.FC = () => {
  const [uploads, setUploads] = useState<UploadSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchUploads();
  }, []);

  const fetchUploads = async () => {
    try {
      setLoading(true);
      const data = await apiService.listUploads();
      setUploads(data.uploads);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch upload history');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusChip = (status: string, processed: boolean) => {
    if (processed) {
      return <Chip icon={<CheckCircle />} label="Completed" color="success" size="small" />;
    } else if (status === 'uploaded') {
      return <Chip icon={<Schedule />} label="Pending" color="warning" size="small" />;
    } else {
      return <Chip icon={<Error />} label="Failed" color="error" size="small" />;
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4, textAlign: 'center' }}>
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading upload history...
        </Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert
          severity="error"
          action={
            <Button onClick={fetchUploads} color="inherit" size="small">
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1">
          Evaluation History
        </Typography>
        <Box>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchUploads} color="primary">
              <Refresh />
            </IconButton>
          </Tooltip>
          <Button
            component={Link}
            to="/upload"
            variant="contained"
            startIcon={<CloudUpload />}
            sx={{ ml: 1 }}
          >
            New Upload
          </Button>
        </Box>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="primary" gutterBottom>
                {uploads.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Uploads
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="success.main" gutterBottom>
                {uploads.filter((u) => u.processed).length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="warning.main" gutterBottom>
                {uploads.filter((u) => !u.processed && u.status === 'uploaded').length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Pending
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h4" color="text.secondary" gutterBottom>
                {uploads.reduce((sum, u) => sum + u.files_count, 0)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Files
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Upload History Table */}
      {uploads.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" gutterBottom>
            No uploads found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Start by uploading your first answer sheet for evaluation.
          </Typography>
          <Button
            component={Link}
            to="/upload"
            variant="contained"
            startIcon={<CloudUpload />}
          >
            Upload Answer Sheet
          </Button>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Student Name</TableCell>
                <TableCell>Exam ID</TableCell>
                <TableCell>Upload Date</TableCell>
                <TableCell>Files</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {uploads.map((upload) => (
                <TableRow key={upload.upload_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {upload.student_name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {upload.exam_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {formatDate(upload.upload_timestamp)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={`${upload.files_count} file${upload.files_count !== 1 ? 's' : ''}`}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    {getStatusChip(upload.status, upload.processed)}
                  </TableCell>
                  <TableCell align="center">
                    {upload.processed ? (
                      <Tooltip title="View Results">
                        <IconButton
                          component={Link}
                          to={`/results/${upload.upload_id}`}
                          color="primary"
                          size="small"
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Tooltip title="Processing...">
                        <IconButton disabled size="small">
                          <Schedule />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Container>
  );
};

export default HistoryPage;
