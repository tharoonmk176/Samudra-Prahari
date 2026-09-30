import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export const generateTacticalPDF = async (results: any[], reportType: 'AGGREGATED' | 'SINGLE_COMPONENT' | 'STITCHED_MAP', specificName?: string) => {
  const doc = new jsPDF('p', 'pt', 'a4');
  const pageWidth = doc.internal.pageSize.getWidth();
  
  // Header
  doc.setFont("helvetica", "bold");
  doc.setFontSize(22);
  doc.setTextColor(15, 23, 42); // slate-900
  doc.text("SAMUDRA PRAHARI", pageWidth / 2, 50, { align: "center" });
  
  doc.setFontSize(12);
  doc.setTextColor(51, 65, 85); // slate-700
  doc.text("AUTONOMOUS MARINE ANOMALY & DEBRIS DETECTION SYSTEM", pageWidth / 2, 70, { align: "center" });
  
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(100, 116, 139); // slate-500
  doc.text("OFFICIAL TACTICAL ANALYSIS REPORT", pageWidth / 2, 90, { align: "center" });

  // Metadata Box
  doc.setDrawColor(203, 213, 225); // slate-300
  doc.setFillColor(248, 250, 252); // slate-50
  doc.rect(40, 110, pageWidth - 80, 60, "FD");
  
  doc.setFont("courier", "bold");
  doc.setFontSize(9);
  doc.setTextColor(71, 85, 105);
  doc.text(`OPERATION ID:   ${reportType}${specificName ? ` [${specificName}]` : ''}`, 50, 130);
  doc.text(`GENERATED:      ${new Date().toISOString().replace('T', ' ').substring(0, 19)} UTC`, 50, 145);
  doc.text(`CLASSIFICATION: CONFIDENTIAL / OFFICIAL USE ONLY`, 50, 160);

  // Executive Summary
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(15, 23, 42);
  doc.text("1. EXECUTIVE SUMMARY", 40, 210);
  
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.setTextColor(51, 65, 85);
  
  const anomaliesCount = results.filter(r => r.report_data && r.report_data.length > 0).reduce((acc, curr) => acc + curr.report_data.length, 0);
  const summaryText = `This report summarizes the acoustic and thermal analysis of ${results.length} sonar telemetry records. The neural network pipeline identified a total of ${anomaliesCount} anomalous targets.`;
  const splitSummary = doc.splitTextToSize(summaryText, pageWidth - 80);
  doc.text(splitSummary, 40, 230);

  // Ledger Table
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(15, 23, 42);
  doc.text("2. ANOMALY LEDGER", 40, 280);

  const tableBody = results.flatMap(r => 
    (r.report_data || []).map((d: any) => [
      r.name.length > 20 ? r.name.substring(0, 20) + '...' : r.name,
      d.class_name,
      `${(d.confidence * 100).toFixed(1)}%`,
      d.lat ? d.lat.toFixed(5) : 'N/A',
      d.lon ? d.lon.toFixed(5) : 'N/A',
      r.status || 'PENDING'
    ])
  );

  autoTable(doc, {
    startY: 300,
    head: [['FILE REF', 'CLASS', 'CONF', 'LATITUDE', 'LONGITUDE', 'STATUS']],
    body: tableBody.length > 0 ? tableBody : [['No anomalies detected', '', '', '', '', '']],
    theme: 'grid',
    headStyles: { fillColor: [15, 23, 42], textColor: 255, fontStyle: 'bold', halign: 'center' },
    bodyStyles: { textColor: [51, 65, 85], halign: 'center' },
    alternateRowStyles: { fillColor: [248, 250, 252] },
    margin: { left: 40, right: 40 }
  });

  // Visual Evidence
  let cursorY = (doc as any).lastAutoTable.finalY + 40;
  
  // Create a helper to fetch and add images
  const addImageToDoc = async (url: string, title: string, x: number, y: number, w: number, h: number) => {
    try {
       const img = new Image();
       img.crossOrigin = "Anonymous";
       img.src = url.startsWith("/outputs") ? `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}` + url : url;
       await new Promise((resolve, reject) => {
         img.onload = resolve;
         img.onerror = reject;
       });
       
       const canvas = document.createElement("canvas");
       canvas.width = img.width;
       canvas.height = img.height;
       const ctx = canvas.getContext("2d");
       if(ctx) {
          ctx.drawImage(img, 0, 0);
          const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
          doc.addImage(dataUrl, 'JPEG', x, y, w, h);
          doc.setFont("helvetica", "bold");
          doc.setFontSize(10);
          doc.setTextColor(51, 65, 85);
          doc.text(title, x, y - 10);
          return true;
       }
    } catch(e) {
       console.error("Failed to load image for PDF", e);
    }
    return false;
  };

  doc.addPage();
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.setTextColor(15, 23, 42);
  doc.text("3. VISUAL EVIDENCE & COMPONENT BREAKDOWN", 40, 50);
  
  cursorY = 90;

  for (const res of results) {
     if (cursorY > doc.internal.pageSize.getHeight() - 100) {
        doc.addPage();
        cursorY = 50;
     }

     doc.setFont("helvetica", "bold");
     doc.setFontSize(12);
     doc.setTextColor(37, 99, 235); // blue-600
     doc.text(`TARGET RECORD: ${res.name}`, 40, cursorY);
     cursorY += 40;
     
     const imgWidth = 220;
     const imgHeight = 220;
     
     // Row 1
     if (res.raw_url) await addImageToDoc(res.raw_url, "1. Raw Sonar Telemetry", 40, cursorY, imgWidth, imgHeight);
     if (res.processed_url) await addImageToDoc(res.processed_url, "2. DSP Filtered Telemetry", 300, cursorY, imgWidth, imgHeight);
     
     cursorY += imgHeight + 40;
     if (cursorY > doc.internal.pageSize.getHeight() - 250) {
        doc.addPage();
        cursorY = 50;
     }

     // Row 2
     if (res.vis_url) await addImageToDoc(res.vis_url, "3. AI Target Detection", 40, cursorY, imgWidth, imgHeight);
     if (res.anomaly_url) await addImageToDoc(res.anomaly_url, "4. Thermal Anomaly Map", 300, cursorY, imgWidth, imgHeight);

     cursorY += imgHeight + 40;
     
     // Row 3
     if (res.segmentation_url) {
        if (cursorY > doc.internal.pageSize.getHeight() - 250) {
           doc.addPage();
           cursorY = 50;
        }
        await addImageToDoc(res.segmentation_url, "5. U-Net Segmentation Mask", 40, cursorY, imgWidth, imgHeight);
        cursorY += imgHeight + 40;
     }
  }

  doc.save(`Samudra_Prahari_${reportType}_${new Date().getTime()}.pdf`);
};
