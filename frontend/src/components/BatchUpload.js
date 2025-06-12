import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../AuthContext';

const BatchUpload = ({ onUploadComplete }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [pollInterval, setPollInterval] = useState(null);

  const { user } = useAuth();
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file) => {
    // Validate file type
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validTypes.includes(fileExtension)) {
      alert('Please upload a CSV or Excel file (.csv, .xlsx, .xls)');
      return;
    }

    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      alert('File size must be less than 10MB');
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API}/employees/batch-upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setUploadId(response.data.upload_id);
      
      // Start polling for status updates
      const interval = setInterval(() => {
        pollUploadStatus(response.data.upload_id);
      }, 2000);
      
      setPollInterval(interval);

    } catch (error) {
      console.error('Upload error:', error);
      alert('Failed to upload file: ' + (error.response?.data?.detail || error.message));
      setUploading(false);
    }
  };

  const pollUploadStatus = async (uploadId) => {
    try {
      const response = await axios.get(`${API}/employees/batch-upload/${uploadId}/status`);
      const status = response.data;
      
      setUploadStatus(status);

      if (status.status === 'completed' || status.status === 'failed') {
        clearInterval(pollInterval);
        setPollInterval(null);
        setUploading(false);
        
        if (onUploadComplete) {
          onUploadComplete(status);
        }
      }
    } catch (error) {
      console.error('Status polling error:', error);
      clearInterval(pollInterval);
      setPollInterval(null);
      setUploading(false);
    }
  };

  const downloadTemplate = () => {
    const csvContent = `first_name,last_name,middle_name,ssn,date_of_birth,email,phone,license_number,license_type,license_state
John,Doe,Michael,123-45-6789,1980-01-15,john.doe@example.com,555-123-4567,12345,MD,CA
Jane,Smith,,987-65-4321,1975-05-20,jane.smith@example.com,555-987-6543,67890,RN,NY`;
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'employee_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Batch Employee Upload</h2>
        <button
          onClick={downloadTemplate}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
        >
          Download Template
        </button>
      </div>

      {!uploading && !uploadStatus && (
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center">
            <svg
              className="w-12 h-12 text-gray-400 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Upload Employee Data
            </h3>
            
            <p className="text-gray-600 mb-4">
              Drag and drop your CSV or Excel file here, or click to browse
            </p>
            
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={handleFileInput}
              className="hidden"
              id="file-upload"
            />
            
            <label
              htmlFor="file-upload"
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 cursor-pointer"
            >
              Choose File
            </label>
            
            <p className="text-sm text-gray-500 mt-2">
              Supports CSV, Excel (.xlsx, .xls) • Max 10MB
            </p>
          </div>
        </div>
      )}

      {uploading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Processing Upload...
          </h3>
          {uploadStatus && (
            <div className="max-w-md mx-auto">
              <div className="bg-gray-200 rounded-full h-2 mb-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadStatus.progress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600">
                {uploadStatus.processed_rows} of {uploadStatus.total_rows} processed
              </p>
            </div>
          )}
        </div>
      )}

      {uploadStatus && !uploading && (
        <div className="bg-gray-50 rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Upload {uploadStatus.status === 'completed' ? 'Completed' : 'Failed'}
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{uploadStatus.total_rows}</div>
              <div className="text-sm text-gray-600">Total Rows</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{uploadStatus.successful_imports}</div>
              <div className="text-sm text-gray-600">Successful</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{uploadStatus.failed_imports}</div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{uploadStatus.progress}%</div>
              <div className="text-sm text-gray-600">Complete</div>
            </div>
          </div>

          {uploadStatus.errors && uploadStatus.errors.length > 0 && (
            <div>
              <h4 className="font-medium text-gray-900 mb-2">
                Errors ({uploadStatus.errors.length} shown):
              </h4>
              <div className="max-h-40 overflow-y-auto">
                {uploadStatus.errors.map((error, index) => (
                  <div key={index} className="text-sm text-red-600 mb-1">
                    Row {error.row}: {error.error}
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={() => {
              setUploadStatus(null);
              setUploadId(null);
            }}
            className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            Upload Another File
          </button>
        </div>
      )}

      <div className="mt-6 bg-blue-50 border-l-4 border-blue-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">
              File Format Requirements
            </h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>Required columns: first_name, last_name</li>
                <li>Optional: middle_name, ssn, date_of_birth, email, phone, license_number, license_type, license_state</li>
                <li>Column names are flexible (e.g., "First Name" or "firstname" both work)</li>
                <li>Duplicate employees will be skipped</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BatchUpload;