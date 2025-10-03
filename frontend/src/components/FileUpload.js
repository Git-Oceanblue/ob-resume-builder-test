import React, { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiFileText, FiAlertCircle, FiCheckCircle, FiLoader, FiFile } from 'react-icons/fi';

// API base URL - Use environment variable for production
const API_BASE_URL = process.env.REACT_APP_API_URL;

const FileUpload = ({ onResumeDataExtracted, setLoading }) => {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  
  // 🚀 STREAMING STATE MANAGEMENT
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingProgress, setStreamingProgress] = useState(0);
  const [currentMessage, setCurrentMessage] = useState('');
  const [processingStartTime, setProcessingStartTime] = useState(null);
  const [detectedSections, setDetectedSections] = useState([]);
  const [currentAgent, setCurrentAgent] = useState('');

  // Debug: Log progress changes
  useEffect(() => {
    console.log('📊 Progress state changed to:', streamingProgress);
  }, [streamingProgress]);

  useEffect(() => {
    console.log('💬 Message state changed to:', currentMessage);
  }, [currentMessage]);

  // Handle file drop using react-dropzone
  const onDrop = useCallback((acceptedFiles) => {
    // Accept only the first file if multiple are uploaded
    const selectedFile = acceptedFiles[0];
    
    if (!selectedFile) return;
    
    // Validate file type
    const validTypes = ['.pdf', '.docx', '.txt'];
    const extension = '.' + selectedFile.name.split('.').pop().toLowerCase();
    
    // Check for DOC files specifically and reject with backend's error message
    if (extension === '.doc') {
      setError('DOC files are not currently supported. Please save your resume as a DOCX, PDF, or TXT file and try again.');
      return;
    }
    
    if (!validTypes.includes(extension)) {
      setError('Invalid file type. Please upload PDF, DOCX, or TXT files.');
      return;
    }
    
    // Validate file size (max 10MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size exceeds 10MB limit.');
      return;
    }
    
    // Clear any previous errors and set the file
    setError('');
    setFile(selectedFile);
  }, []);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'text/plain': ['.txt']
    },
    onDropRejected: (rejectedFiles) => {
      const docFile = rejectedFiles.find(file => 
        file.file.name.toLowerCase().endsWith('.doc')
      );
      if (docFile) {
        setError('DOC files are not currently supported. Please save your resume as a DOCX, PDF, or TXT file and try again.');
      }
    }
  });
  
  // 🚀 REVOLUTIONARY STREAMING UPLOAD FUNCTION
  const handleStreamingSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file to upload.');
      return;
    }
    
    // Reset streaming state
    setIsStreaming(true);
    setLoading(true);
    setError('');
    setStreamingProgress(0);
    setCurrentMessage('');
    setDetectedSections([]);
    setCurrentAgent('');
    setProcessingStartTime(Date.now());
    
    try {
      // Create form data for file upload
      const formData = new FormData();
      formData.append('file', file);
      
      // 🔥 INITIATE STREAMING UPLOAD TO NEW ENDPOINT
      console.log('🚀 Starting fetch to:', `${API_BASE_URL}api/stream-resume-processing`);
      
      const response = await fetch(`${API_BASE_URL}api/stream-resume-processing`, {
        method: 'POST',
        body: formData,
        headers: {
          // Don't set Content-Type for FormData, let browser set it
        }
      });
      
      console.log('📡 Response status:', response.status);
      console.log('📡 Response headers:', [...response.headers.entries()]);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Response error:', errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      
      // 🌊 SETUP SERVER-SENT EVENTS READER
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      console.log('📖 Starting to read stream...');
      
      while (true) {
        const { value, done } = await reader.read();
        
        if (done) {
          console.log('✅ Stream reading completed');
          break;
        }
        
        // Decode the chunk and add to buffer
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        console.log('📦 Received chunk:', chunk.substring(0, 100) + '...');
        
        // Process complete events
        const events = buffer.split('\n\n');
        buffer = events.pop(); // Keep incomplete event in buffer
        
        for (const event of events) {
          if (event.startsWith('data: ')) {
            try {
              const eventData = event.slice(6);
              if (eventData === '[DONE]') {
                console.log('🏁 Received DONE signal');
                continue;
              }
              const data = JSON.parse(eventData);
              console.log('📨 Parsed event:', data);
              handleStreamingEvent(data);
            } catch (parseError) {
              console.error('❌ Parse error:', parseError, 'Event:', event);
            }
          }
        }
      }
      
    } catch (streamingError) {
      setError(`Streaming failed: ${streamingError.message}`);
    } finally {
      setIsStreaming(false);
      setLoading(false);
    }
  };
  
  // 📊 HANDLE INDIVIDUAL STREAMING EVENTS
  const handleStreamingEvent = (data) => {
    console.log('📡 Streaming Event:', data.type, data.progress, data.message);
    
    switch (data.type) {
      case 'connection':
        console.log('🔄 Setting progress to:', data.progress || 5);
        setStreamingProgress(data.progress || 5);
        setCurrentMessage(data.message || 'Connected to server');
        break;
        
      case 'progress':
        console.log('🔄 Setting progress to:', data.progress || 0);
        setStreamingProgress(data.progress || 0);
        setCurrentMessage(data.message || '');
        break;
        
      case 'sections_detected':
        setStreamingProgress(data.progress || 20);
        setCurrentMessage(data.message || '');
        if (data.sections) {
          setDetectedSections(data.sections);
        }
        break;
        
      case 'processing_start':
        setStreamingProgress(data.progress || 30);
        setCurrentMessage(data.message || '');
        break;
        
      case 'agent_processing':
        setStreamingProgress(data.progress || 40);
        setCurrentMessage(data.message || '');
        if (data.current_agent) {
          setCurrentAgent(data.current_agent);
        }
        break;
        
      case 'processing_strategy':
        setStreamingProgress(data.progress || 15);
        setCurrentMessage(data.message || '');
        break;
        
      case 'complete':
        setStreamingProgress(100);
        setCurrentMessage(data.message || 'Processing complete! 🎉');
        setCurrentAgent('');
        break;
        
      case 'final_data':
        setStreamingProgress(100);
        setCurrentMessage('Processing complete! 🎉');
        setCurrentAgent('');
        
        // Validate and sanitize final data before passing to parent
        if (data.data) {
          const sanitizedData = sanitizeResumeData(data.data);
          onResumeDataExtracted(sanitizedData);
        }
        break;
        
      case 'error':
        setError(data.message || 'Unknown streaming error');
        break;
        
      default:
        // Log unknown events for debugging
        console.log('🔍 Unknown event type:', data.type, data);
    }
  };
  
  // 🔧 DATA SANITIZATION FUNCTION
  const sanitizeResumeData = (data) => {
    
    try {
      const sanitized = {
        name: data.name || '',
        title: data.title || '',
        requisitionNumber: data.requisitionNumber || '',
        professionalSummary: Array.isArray(data.professionalSummary) ? data.professionalSummary : [],
        summarySections: Array.isArray(data.summarySections) ? data.summarySections : [],
        subsections: Array.isArray(data.subsections) ? data.subsections : [],
        employmentHistory: Array.isArray(data.employmentHistory) ? data.employmentHistory : [],
        education: Array.isArray(data.education) ? data.education : [],
        certifications: Array.isArray(data.certifications) ? data.certifications : [],
        technicalSkills: (data.technicalSkills && typeof data.technicalSkills === 'object') ? data.technicalSkills : {},
        skillCategories: Array.isArray(data.skillCategories) ? data.skillCategories : []
      };
      
      // Ensure employment history has proper structure
      sanitized.employmentHistory = sanitized.employmentHistory.map(job => ({
        companyName: job.companyName || '',
        roleName: job.roleName || '',
        workPeriod: job.workPeriod || '',
        location: job.location || '',
        responsibilities: Array.isArray(job.responsibilities) ? job.responsibilities : (job.responsibilities ? [job.responsibilities] : []),
        projects: Array.isArray(job.projects) ? job.projects.map(project => ({
          projectName: project.projectName || '',
          projectResponsibilities: Array.isArray(project.projectResponsibilities) ? project.projectResponsibilities : [],
          keyTechnologies: project.keyTechnologies || '',
          period: project.period || ''
        })) : [],
        subsections: Array.isArray(job.subsections) ? job.subsections.map(subsection => ({
          title: subsection.title || '',
          content: Array.isArray(subsection.content) ? subsection.content : []
        })) : [],
        keyTechnologies: job.keyTechnologies || ''
      }));
      
      // Ensure summary subsections have proper structure
      if (Array.isArray(data.summarySections)) {
        sanitized.summarySections = data.summarySections.map(subsection => ({
          title: subsection.title || '',
          content: Array.isArray(subsection.content) ? subsection.content : []
        }));
      } else if (Array.isArray(data.subsections)) {
        sanitized.summarySections = data.subsections.map(subsection => ({
          title: subsection.title || '',
          content: Array.isArray(subsection.content) ? subsection.content : []
        }));
        sanitized.subsections = sanitized.summarySections; // For compatibility
      }
      
      // Ensure skill categories have proper structure
      if (Array.isArray(data.skillCategories)) {
        sanitized.skillCategories = data.skillCategories.map(category => ({
          categoryName: category.categoryName || '',
          skills: Array.isArray(category.skills) ? category.skills : [],
          subCategories: Array.isArray(category.subCategories) ? category.subCategories.map(subCategory => ({
            name: subCategory.name || '',
            skills: Array.isArray(subCategory.skills) ? subCategory.skills : []
          })) : []
        }));
      }
      
      // Ensure education has proper structure
      sanitized.education = sanitized.education.map(edu => ({
        degree: edu.degree || '',
        areaOfStudy: edu.areaOfStudy || '',
        school: edu.school || '',
        location: edu.location || '',
        date: edu.date || '',
        wasAwarded: edu.wasAwarded !== undefined ? edu.wasAwarded : true
      }));
      
      // Ensure certifications have proper structure
      sanitized.certifications = sanitized.certifications.map(cert => ({
        name: cert.name || '',
        issuedBy: cert.issuedBy || '',
        dateObtained: cert.dateObtained || '',
        certificationNumber: cert.certificationNumber || '',
        expirationDate: cert.expirationDate || ''
      }));

      return sanitized;

    } catch (error) {
      
      // Return safe default structure
      return {
        name: '',
        title: '',
        requisitionNumber: '',
        professionalSummary: [],
        summarySections: [],
        subsections: [],
        employmentHistory: [],
        education: [],
        certifications: [],
        technicalSkills: {},
        skillCategories: []
      };
    }
  };

  
  return (
    <div className="max-w-4xl mx-auto animate-slide-up">
      {/* Header Section */}
      <div className="text-center mb-8">
        <div className="flex items-center justify-center mb-4">
          <FiFile className="text-6xl text-ocean-blue mr-4" />
          <div>
            <h2 className="text-3xl font-bold text-ocean-dark">Upload Resume</h2>
          </div>
        </div>
      </div>
      
      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 text-red-700 p-6 mb-8 rounded-lg shadow-md animate-fade-in">
          <div className="flex items-start">
            <FiAlertCircle className="mt-1 mr-3 text-xl flex-shrink-0" />
            <div>
              <h4 className="font-semibold mb-1">Upload Error</h4>
              <span>{error}</span>
            </div>
          </div>
        </div>
      )}
      
      {/* File Drop Zone */}
      <div 
        {...getRootProps()} 
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 transform hover:scale-105 mb-8 ${
          isDragActive 
            ? 'border-ocean-blue bg-blue-50 shadow-lg' 
            : 'border-gray-300 hover:border-ocean-blue hover:bg-blue-50'
        }`}
      >
        <input {...getInputProps()} />
        
        {/* Upload Icon and Animation */}
        <div className="mb-6">
          <FiUpload className={`mx-auto text-6xl transition-all duration-300 ${
            isDragActive ? 'text-ocean-blue animate-bounce' : 'text-gray-400'
          }`} />
        </div>
        
        {/* Upload Text */}
        <div className="space-y-2">
          <h3 className="text-xl font-semibold text-ocean-dark">
            {isDragActive ? 'Drop resume here' : 'Drag & drop resume here'}
          </h3>
          <p className="text-gray-600">
            or click to select file
          </p>
          <div className="flex items-center justify-center space-x-4 mt-4">
            <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">PDF</span>
            <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">DOCX</span>
            <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">TXT</span>
          </div>
          <p className="text-xs text-red-500 mt-2 font-medium">
            ⚠️ DOC files are not supported
          </p>
        </div>
        
        {/* File Size Limit */}
        <div className="mt-6 text-sm text-gray-500">
          Maximum file size: 10MB
        </div>
      </div>
      
      {/* Selected File Display */}
      {file && (
        <div className="bg-gradient-to-r from-ocean-dark to-ocean-blue rounded-xl p-6 mb-8 text-white shadow-lg animate-fade-in">
          <div className="flex items-center">
            <FiFileText className="text-3xl mr-4" />
            <div className="flex-1">
              <h4 className="font-semibold text-lg">{file.name}</h4>
              <p className="text-blue-200">
                {(file.size / 1024 / 1024).toFixed(2)} MB • Ready for processing
              </p>
            </div>
            <div className="text-right">
              <div className="bg-white bg-opacity-20 rounded-lg px-3 py-1">
                <span className="text-sm font-medium">Selected ✓</span>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Streaming Processing Interface */}
      {isStreaming && (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-ocean-blue rounded-2xl p-8 mb-8 shadow-xl animate-fade-in">
          <div className="text-center mb-6">
            <h3 className="text-2xl font-bold text-ocean-dark mb-2">⚡ AI Processing in Progress</h3>
            <p className="text-ocean-blue font-medium">{currentMessage}</p>
            <p className="text-sm text-gray-600 mt-2">Debug: Progress = {streamingProgress}%</p>
          </div>
          
          {/* Enhanced Progress Bar */}
          <div className="relative mb-6">
            <div className="flex justify-between text-sm text-ocean-dark mb-2 font-medium">
              <span>Progress</span>
              <span>{streamingProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div 
                className="bg-gradient-to-r from-ocean-blue to-blue-400 h-4 rounded-full transition-all duration-700 ease-out relative"
                style={{ width: `${streamingProgress}%` }}
              >
                <div className="absolute inset-0 bg-white bg-opacity-30 animate-pulse"></div>
              </div>
            </div>
          </div>
          

          
          {/* Detected Sections */}
          {detectedSections.length > 0 && (
            <div className="mb-6">
              <h4 className="text-lg font-semibold text-ocean-dark mb-3">📋 Resume Sections Found:</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {detectedSections.map((section, index) => (
                  <div 
                    key={index}
                    className="flex items-center px-4 py-3 rounded-lg bg-blue-50 border border-blue-200 text-sm font-medium text-ocean-dark"
                  >
                    <span className="capitalize">{section}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Current Processing Agent */}
          {currentAgent && (
            <div className="mb-4 p-4 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
              <div className="flex items-center">
                <FiLoader className="animate-spin mr-3 text-green-600" />
                <span className="text-green-800 font-medium">
                  Currently processing: <span className="capitalize font-bold">{currentAgent}</span> section
                </span>
              </div>
            </div>
          )}
          
          {/* Processing Time */}
          {processingStartTime && (
            <div className="text-center text-sm text-ocean-blue font-medium">
              ⏱️ Processing for {((Date.now() - processingStartTime) / 1000).toFixed(1)}s
            </div>
          )}
        </div>
      )}
      
      {/* Process Button */}
      <div className="flex justify-center">
        <button 
          onClick={handleStreamingSubmit}
          disabled={!file || isStreaming}
          className={`px-8 py-4 rounded-xl text-white font-semibold text-lg flex items-center transition-all duration-300 transform hover:scale-105 ${
            file && !isStreaming 
              ? 'bg-gradient-to-r from-ocean-blue to-blue-500 hover:from-blue-600 hover:to-blue-700 shadow-lg' 
              : 'bg-gray-400 cursor-not-allowed'
          }`}
        >
          {isStreaming ? (
            <>
              <FiLoader className="animate-spin mr-3 text-xl" />
              Processing Resume...
            </>
          ) : (
            <>
              <FiUpload className="mr-3 text-xl" />
              Process Resume
            </>
          )}
        </button>
      </div>
      
    </div>
  );
};

export default FileUpload; 
