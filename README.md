# ProctorIQ - Automated Exam Evaluation System

A professional React + FastAPI application for automated evaluation of student answer sheets using AI.

## Features

- 🚀 **Professional File Upload**: Drag & drop interface for answer sheets (PDF, images)
- 🤖 **AI-Powered Evaluation**: GPT-4 based intelligent assessment
- 📊 **Detailed Results**: Comprehensive evaluation reports with feedback
- 🎯 **Vector Database Integration**: Enhanced context retrieval for better accuracy
- 📈 **Performance Analytics**: Section-wise and question-wise analysis
- 🔒 **Secure Processing**: Enterprise-grade security for student data

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **OpenAI GPT-4**: Advanced language model for evaluation
- **Pinecone**: Vector database for context retrieval
- **Tesseract OCR**: Text extraction from images
- **PyMuPDF**: PDF text extraction

### Frontend
- **React 18**: Modern React with TypeScript
- **Material-UI**: Professional UI component library
- **React Router**: Client-side routing
- **Axios**: HTTP client for API communication
- **React Dropzone**: File upload interface

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Tesseract OCR (for image text extraction)

### Backend Setup

1. **Install Python dependencies:**
   ```bash
   cd exam_automator
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp ../.env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Install Tesseract OCR:**
   ```bash
   # macOS
   brew install tesseract
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr
   
   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

4. **Run the backend:**
   ```bash
   cd backend
   python main.py
   ```

   The API will be available at: `http://localhost:8000`
   API docs: `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   npm start
   ```

   The app will be available at: `http://localhost:3000`

## Usage

1. **Upload Answer Sheets:**
   - Go to the Upload page
   - Enter student information
   - Drag & drop or select answer sheet files
   - Submit for evaluation

2. **View Results:**
   - Automatic redirect to results after processing
   - Detailed evaluation with marks and feedback
   - Section-wise performance analysis

3. **Browse History:**
   - View all past evaluations
   - Track processing status
   - Quick access to results

## API Endpoints

### Core Endpoints
- `POST /api/v1/upload/answer-sheet` - Upload answer sheet files
- `POST /api/v1/process/answer-sheet/{upload_id}` - Process uploaded files
- `GET /api/v1/results/{upload_id}` - Get evaluation results
- `GET /api/v1/uploads` - List all upload sessions

### Utility Endpoints
- `GET /health` - Health check
- `GET /api/v1/papers` - List available question papers
- `GET /api/v1/status` - System status

## Configuration

### Environment Variables
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional (for vector database)
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=index_name

# Frontend
REACT_APP_API_URL=http://localhost:8000
```

### File Upload Limits
- Max file size: 50MB per file
- Supported formats: PDF, JPG, PNG, BMP, TIFF
- Multiple files per upload session

## Development

### Backend Development
```bash
# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest tests/

# Format code
black .
```

### Frontend Development
```bash
# Start dev server
npm start

# Build for production
npm run build

# Run tests
npm test
```

## Project Structure

```
proctoriq/
├── exam_automator/
│   ├── backend/
│   │   ├── main.py              # FastAPI application
│   │   ├── api/                 # API routes
│   │   ├── services/            # Business logic
│   │   ├── ocr/                 # OCR processing
│   │   ├── config/              # Configuration
│   │   └── docs/                # Question papers
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── services/            # API services
│   │   └── App.tsx             # Main app
│   └── package.json
└── README.md
```

## Production Deployment

### Backend (Docker)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY exam_automator/ .
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Nginx)
```bash
npm run build
# Serve build/ directory with nginx or similar
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, please open an issue in the GitHub repository or contact the development team.
