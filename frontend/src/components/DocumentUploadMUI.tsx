import React, { useState } from "react";
import axios from "axios";
import {
  Box,
  Button,
  Typography,
  LinearProgress,
  Alert,
  Paper,
  Chip,
  Stack,
} from "@mui/material";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import InsertDriveFileIcon from "@mui/icons-material/InsertDriveFile";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";

interface DocumentUploadProps {
  onUploadSuccess: (data: any) => void;
}

const DocumentUploadMUI: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  const uploadDocument = async () => {
    if (!file) {
      setError("Please select a PDF file");
      return;
    }

    // Check file size (limit to 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError("File size exceeds 10MB limit");
      return;
    }

    setUploading(true);
    setError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post(
        "http://127.0.0.1:8000/api/documents/upload-sri-lanka",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
          timeout: 30000,
          onUploadProgress: (progressEvent) => {
            const percentCompleted = progressEvent.total
              ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
              : 0;
            setUploadProgress(percentCompleted);
          },
        }
      );

      console.log("Upload successful:", res.data);
      setUploadProgress(100);
      setUploading(false);
      onUploadSuccess(res.data);

      // Reset after success
      setTimeout(() => {
        setFile(null);
        setUploadProgress(0);
      }, 2000);
    } catch (err: any) {
      console.error("Upload error details:", err);

      setUploading(false);
      setUploadProgress(0);

      if (err.code === "ECONNABORTED") {
        setError("Request timed out. Please try again.");
      } else if (err.response) {
        let errorMessage = "Upload failed";

        if (err.response.data?.detail) {
          errorMessage = err.response.data.detail;
        } else if (err.response.data?.error) {
          errorMessage = err.response.data.error;
        } else if (err.response.data?.message) {
          errorMessage = err.response.data.message;
        } else if (typeof err.response.data === "string") {
          errorMessage = err.response.data;
        } else if (err.response.status === 500) {
          errorMessage = "Server error (500). Check backend logs.";
        }

        setError(`Server Error: ${errorMessage}`);
      } else if (err.request) {
        setError("No response from server. Is the backend running?");
      } else {
        setError(`Error: ${err.message}`);
      }
    }
  };

  return (
    <Paper
      elevation={3}
      sx={{
        padding: 3,
        marginBottom: 3,
        background: "linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)",
        borderRadius: 3,
      }}
    >
      <Stack spacing={2}>
        <Box>
          <Typography
            variant="h5"
            gutterBottom
            sx={{
              fontWeight: 600,
              color: "#2c3e50",
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <CloudUploadIcon /> Upload Sri Lankan Legal Document
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Supported formats: Sri Lankan Law Reports (SLR) and New Law Reports
            (NLR) in PDF format
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box
          sx={{
            border: "2px dashed #3498db",
            borderRadius: 2,
            padding: 3,
            textAlign: "center",
            backgroundColor: "rgba(255, 255, 255, 0.7)",
            cursor: "pointer",
            transition: "all 0.3s ease",
            "&:hover": {
              borderColor: "#2980b9",
              backgroundColor: "rgba(255, 255, 255, 0.9)",
            },
          }}
          onClick={() => document.getElementById("file-input")?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />

          {file ? (
            <Stack spacing={1} alignItems="center">
              <InsertDriveFileIcon sx={{ fontSize: 48, color: "#3498db" }} />
              <Typography variant="body1" fontWeight={600}>
                {file.name}
              </Typography>
              <Chip
                label={formatFileSize(file.size)}
                size="small"
                color="primary"
                variant="outlined"
              />
            </Stack>
          ) : (
            <Stack spacing={1} alignItems="center">
              <CloudUploadIcon sx={{ fontSize: 48, color: "#95a5a6" }} />
              <Typography variant="body1" color="text.secondary">
                Click to select a PDF file or drag and drop
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Maximum file size: 10MB
              </Typography>
            </Stack>
          )}
        </Box>

        {uploading && (
          <Box>
            <LinearProgress
              variant="determinate"
              value={uploadProgress}
              sx={{
                height: 8,
                borderRadius: 4,
                backgroundColor: "#e0e0e0",
                "& .MuiLinearProgress-bar": {
                  borderRadius: 4,
                  background:
                    "linear-gradient(90deg, #667eea 0%, #764ba2 100%)",
                },
              }}
            />
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mt: 0.5, display: "block", textAlign: "center" }}
            >
              Uploading... {uploadProgress}%
            </Typography>
          </Box>
        )}

        {uploadProgress === 100 && !uploading && (
          <Alert
            severity="success"
            icon={<CheckCircleIcon fontSize="inherit" />}
          >
            Upload completed successfully!
          </Alert>
        )}

        <Box sx={{ display: "flex", gap: 2 }}>
          <Button
            variant="contained"
            onClick={uploadDocument}
            disabled={!file || uploading}
            startIcon={<CloudUploadIcon />}
            fullWidth
            sx={{
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "white",
              fontWeight: 600,
              padding: "12px",
              borderRadius: 2,
              textTransform: "none",
              fontSize: "1rem",
              boxShadow: "0 4px 6px rgba(102, 126, 234, 0.4)",
              "&:hover": {
                background: "linear-gradient(135deg, #764ba2 0%, #667eea 100%)",
                boxShadow: "0 6px 10px rgba(102, 126, 234, 0.6)",
              },
              "&:disabled": {
                opacity: 0.6,
                background: "#95a5a6",
              },
            }}
          >
            {uploading ? "Uploading..." : "Upload & Analyze"}
          </Button>

          {file && !uploading && (
            <Button
              variant="outlined"
              onClick={() => {
                setFile(null);
                setError(null);
                setUploadProgress(0);
              }}
              sx={{
                borderColor: "#e74c3c",
                color: "#e74c3c",
                fontWeight: 600,
                textTransform: "none",
                "&:hover": {
                  borderColor: "#c0392b",
                  backgroundColor: "rgba(231, 76, 60, 0.1)",
                },
              }}
            >
              Clear
            </Button>
          )}
        </Box>
      </Stack>
    </Paper>
  );
};

export default DocumentUploadMUI;
