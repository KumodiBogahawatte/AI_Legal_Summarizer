import React, { useState } from "react";
import {
  Button,
  Menu,
  MenuItem,
  CircularProgress,
  Snackbar,
  Alert,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import DescriptionIcon from "@mui/icons-material/Description";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

interface ExportButtonProps {
  documentId: number;
  documentTitle?: string;
  contentElementId?: string; // ID of the HTML element to export
}

const ExportButton: React.FC<ExportButtonProps> = ({
  documentId,
  documentTitle = "Legal Document",
  contentElementId = "case-analysis-container",
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [exporting, setExporting] = useState(false);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "info";
  }>({
    open: false,
    message: "",
    severity: "info",
  });

  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const showNotification = (
    message: string,
    severity: "success" | "error" | "info"
  ) => {
    setNotification({ open: true, message, severity });
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  const sanitizeFilename = (filename: string): string => {
    return filename
      .replace(/[^a-z0-9]/gi, "_")
      .replace(/_+/g, "_")
      .toLowerCase();
  };

  const exportToPDF = async () => {
    handleClose();
    setExporting(true);
    showNotification("Generating PDF...", "info");

    try {
      const element = document.getElementById(contentElementId);

      if (!element) {
        throw new Error("Content element not found");
      }

      // Clone the element to avoid modifying the original
      const clone = element.cloneNode(true) as HTMLElement;
      clone.style.width = "210mm"; // A4 width
      clone.style.padding = "20mm";
      clone.style.background = "white";

      document.body.appendChild(clone);

      const canvas = await html2canvas(clone, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: "#ffffff",
      });

      document.body.removeChild(clone);

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
      });

      const imgWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      // Add first page
      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      // Add additional pages if needed
      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      const filename = `${sanitizeFilename(documentTitle)}_analysis.pdf`;
      pdf.save(filename);

      showNotification("PDF exported successfully!", "success");
    } catch (error) {
      console.error("PDF export error:", error);
      showNotification("Failed to export PDF. Please try again.", "error");
    } finally {
      setExporting(false);
    }
  };

  const exportToWord = async () => {
    handleClose();
    setExporting(true);
    showNotification("Generating Word document...", "info");

    try {
      const element = document.getElementById(contentElementId);

      if (!element) {
        throw new Error("Content element not found");
      }

      // Get the HTML content
      const htmlContent = element.innerHTML;

      // Create a simple HTML document structure
      const htmlDocument = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>${documentTitle}</title>
          <style>
            body {
              font-family: 'Times New Roman', serif;
              line-height: 1.6;
              color: #333;
              max-width: 800px;
              margin: 0 auto;
              padding: 20px;
            }
            h1, h2, h3 { color: #2c3e50; }
            h1 { font-size: 24pt; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
            h2 { font-size: 18pt; margin-top: 20px; }
            h3 { font-size: 14pt; margin-top: 15px; }
            p { margin: 10px 0; text-align: justify; }
            .card { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
            .badge { padding: 3px 8px; border-radius: 3px; font-weight: bold; }
          </style>
        </head>
        <body>
          ${htmlContent}
        </body>
        </html>
      `;

      // Create blob and download
      const blob = new Blob([htmlDocument], {
        type: "application/msword",
      });

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${sanitizeFilename(documentTitle)}_analysis.doc`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      showNotification("Word document exported successfully!", "success");
    } catch (error) {
      console.error("Word export error:", error);
      showNotification(
        "Failed to export Word document. Please try again.",
        "error"
      );
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <Button
        variant="contained"
        startIcon={
          exporting ? (
            <CircularProgress size={20} color="inherit" />
          ) : (
            <DownloadIcon />
          )
        }
        onClick={handleClick}
        disabled={exporting}
        sx={{
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          color: "white",
          fontWeight: 600,
          padding: "10px 20px",
          borderRadius: "8px",
          textTransform: "none",
          boxShadow: "0 4px 6px rgba(102, 126, 234, 0.4)",
          "&:hover": {
            background: "linear-gradient(135deg, #764ba2 0%, #667eea 100%)",
            boxShadow: "0 6px 10px rgba(102, 126, 234, 0.6)",
          },
          "&:disabled": {
            opacity: 0.6,
          },
        }}
      >
        {exporting ? "Exporting..." : "Export"}
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          "aria-labelledby": "export-button",
        }}
        PaperProps={{
          sx: {
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            borderRadius: "8px",
            minWidth: "200px",
          },
        }}
      >
        <MenuItem
          onClick={exportToPDF}
          sx={{
            padding: "12px 20px",
            "&:hover": {
              background: "rgba(102, 126, 234, 0.1)",
            },
          }}
        >
          <PictureAsPdfIcon sx={{ mr: 1.5, color: "#e74c3c" }} />
          Export as PDF
        </MenuItem>
        <MenuItem
          onClick={exportToWord}
          sx={{
            padding: "12px 20px",
            "&:hover": {
              background: "rgba(102, 126, 234, 0.1)",
            },
          }}
        >
          <DescriptionIcon sx={{ mr: 1.5, color: "#2980b9" }} />
          Export as Word
        </MenuItem>
      </Menu>

      <Snackbar
        open={notification.open}
        autoHideDuration={4000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert
          onClose={handleCloseNotification}
          severity={notification.severity}
          sx={{ width: "100%" }}
          variant="filled"
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default ExportButton;
