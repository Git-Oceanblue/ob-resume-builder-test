# Resume Builder Project Flow Diagram

## System Architecture Overview

```mermaid
graph TB
    subgraph "User Interface Layer"
        A[User Browser] --> B[React Frontend App]
        B --> C[FileUpload Component]
        B --> D[ResumeForm Component]
        B --> E[GeneratedResume Component]
        B --> F[MissingPointsTracker Component]
    end

    subgraph "Frontend Processing"
        C --> G[File Validation<br/>PDF/DOCX/TXT]
        G --> H[Drag & Drop Interface]
        H --> I[Streaming Upload]
    end

    subgraph "AWS Infrastructure"
        J[CloudFront CDN] --> K[S3 Bucket<br/>Frontend Hosting]
        L[Lambda Function URL] --> M[AWS Lambda<br/>Backend API]
        N[CloudWatch Logs] --> M
    end

    subgraph "Backend Processing"
        M --> O[FastAPI Application]
        O --> P[File Parser<br/>extract_text_from_file]
        P --> Q[AI Parser<br/>stream_resume_processing]
        Q --> R[OpenAI GPT-4o-mini API]
        R --> S[Token Logger<br/>Cost Tracking]
        S --> T[Chunk Resume<br/>Section Detection]
    end

    subgraph "Data Processing Pipeline"
        T --> U[Professional Summary<br/>Extraction]
        T --> V[Employment History<br/>Extraction]
        T --> W[Education<br/>Extraction]
        T --> X[Certifications<br/>Extraction]
        T --> Y[Technical Skills<br/>Extraction]
        U --> Z[Structured JSON Data]
        V --> Z
        W --> Z
        X --> Z
        Y --> Z
    end

    subgraph "Output Generation"
        Z --> AA[Resume Preview]
        Z --> BB[Word Document<br/>Generation]
        Z --> CC[Print Functionality]
        AA --> DD[Download Options]
        BB --> DD
        CC --> DD
    end

    %% Connections
    I --> L
    B --> J
    O --> R
    Z --> B
    DD --> A

    %% Styling
    classDef frontend fill:#e1f5fe
    classDef backend fill:#f3e5f5
    classDef aws fill:#fff3e0
    classDef ai fill:#e8f5e8
    classDef output fill:#fce4ec

    class A,B,C,D,E,F,G,H,I frontend
    class O,P,Q,S,T,U,V,W,X,Y,Z backend
    class J,K,L,M,N aws
    class R ai
    class AA,BB,CC,DD output
```

## Detailed Component Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant CF as CloudFront
    participant S3 as S3 Bucket
    participant L as Lambda
    participant AI as OpenAI API
    participant P as File Parser
    participant A as AI Parser

    U->>F: Upload Resume File
    F->>F: Validate File Type (PDF/DOCX/TXT)
    F->>L: POST /api/stream-resume-processing
    L->>P: Extract Text from File
    P->>P: Parse PDF/DOCX/TXT
    P-->>L: Return Extracted Text
    L->>A: Process with AI
    A->>AI: Send Text + Function Schema
    AI-->>A: Return Structured Data
    A->>A: Clean & Validate Data
    A-->>L: Return Processed Data
    L-->>F: Stream Response (Server-Sent Events)
    F->>F: Update UI Progress
    F->>F: Display Extracted Data
    U->>F: Review & Edit Data
    F->>F: Generate Word Document
    F->>U: Download Resume
```

## Infrastructure Components

```mermaid
graph LR
    subgraph "AWS Cloud Infrastructure"
        subgraph "Frontend Hosting"
            A[CloudFront Distribution] --> B[S3 Bucket<br/>Static Website]
            A --> C[Origin Access Control]
        end
        
        subgraph "Backend Processing"
            D[Lambda Function] --> E[Function URL]
            D --> F[CloudWatch Logs]
            D --> G[IAM Role & Policies]
        end
        
        subgraph "External Services"
            H[OpenAI API] --> D
        end
        
        subgraph "Terraform Management"
            I[Terraform State<br/>S3 Backend] --> J[Infrastructure as Code]
            J --> A
            J --> D
        end
    end

    subgraph "Development Environment"
        K[React Development Server] --> L[Local Testing]
        M[Python Backend] --> N[Local API Testing]
    end

    %% Styling
    classDef aws fill:#ff9800,color:#fff
    classDef dev fill:#2196f3,color:#fff
    classDef external fill:#4caf50,color:#fff

    class A,B,C,D,E,F,G,I,J aws
    class K,L,M,N dev
    class H external
```

## Data Flow Architecture

```mermaid
flowchart TD
    subgraph "Input Processing"
        A[Resume File Upload] --> B[File Type Detection]
        B --> C[Text Extraction]
        C --> D[Content Sanitization]
    end

    subgraph "AI Processing Pipeline"
        D --> E[Section Detection]
        E --> F[Professional Summary<br/>Extraction]
        E --> G[Employment History<br/>Extraction]
        E --> H[Education<br/>Extraction]
        E --> I[Certifications<br/>Extraction]
        E --> J[Skills<br/>Extraction]
    end

    subgraph "Data Structuring"
        F --> K[Structured JSON]
        G --> K
        H --> K
        I --> K
        J --> K
        K --> L[Data Validation]
        L --> M[Clean Data Output]
    end

    subgraph "Output Generation"
        M --> N[Resume Preview]
        M --> O[Word Document]
        M --> P[Print Layout]
        N --> Q[User Download]
        O --> Q
        P --> Q
    end

    %% Styling
    classDef input fill:#e3f2fd
    classDef ai fill:#e8f5e8
    classDef data fill:#fff3e0
    classDef output fill:#fce4ec

    class A,B,C,D input
    class E,F,G,H,I,J ai
    class K,L,M data
    class N,O,P,Q output
```

## Key Features & Technologies

### Frontend (React)
- **FileUpload**: Drag & drop interface with file validation
- **ResumeForm**: Comprehensive editing interface for all resume sections
- **GeneratedResume**: Preview and download functionality
- **MissingPointsTracker**: Quality assurance for AI extraction
- **Streaming**: Real-time progress updates during AI processing

### Backend (FastAPI + Python)
- **File Parser**: Supports PDF, DOCX, and TXT files
- **AI Parser**: OpenAI GPT-4o-mini integration with function calling
- **Token Logger**: Cost tracking and usage analytics
- **Chunk Resume**: Intelligent section detection and parsing
- **Streaming Response**: Server-sent events for real-time updates

### Infrastructure (AWS + Terraform)
- **S3**: Static website hosting for frontend
- **CloudFront**: CDN for global content delivery
- **Lambda**: Serverless backend processing
- **Function URL**: Direct API access without API Gateway
- **CloudWatch**: Logging and monitoring
- **Terraform**: Infrastructure as Code management

### AI Processing
- **OpenAI GPT-4o-mini**: Cost-effective AI processing
- **Function Calling**: Structured data extraction
- **Cache Bypass**: Ensures fresh AI responses
- **Token Optimization**: Efficient prompt engineering
- **Error Handling**: Robust fallback mechanisms

## Project Structure Summary

```
ob-resume-builder-test/
├── frontend/                 # React application
│   ├── src/components/      # UI components
│   ├── public/              # Static assets
│   └── package.json         # Dependencies
├── backend/                 # Python FastAPI backend
│   ├── utils/               # Processing utilities
│   ├── main.py              # FastAPI application
│   └── lambda_handler.py    # AWS Lambda wrapper
├── terraform/               # Infrastructure as Code
│   ├── modules/             # Reusable components
│   └── main.tf              # Main configuration
└── standalone-resume-builder/ # Dummy directory (ignored)
```

This resume builder project demonstrates a modern, scalable architecture combining React frontend, Python backend, AI processing, and AWS cloud infrastructure to provide an intelligent resume parsing and generation service.
