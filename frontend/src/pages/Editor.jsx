import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, API_BASE_URL } from '../api/client';
import { ArrowLeft, Save, FileArchive, Lock, ScanText, Wand2 } from 'lucide-react';

// PHASE 6: Common Civic & General Portal Presets
const PORTAL_PRESETS = [
  { label: "Passport Photo (100KB)", type: "image", format: "JPEG", maxKb: 100, w: 413, h: 531 },
  { label: "Digital Signature (20KB)", type: "image", format: "JPEG", maxKb: 20, w: 140, h: 60 },
  { label: "Govt Portal Image (200KB)", type: "image", format: "JPEG", maxKb: 200, w: '', h: '' },
  { label: "Identity Card/KYC (500KB)", type: "pdf", maxKb: 500, mode: "standard" },
  { label: "Standard Certificate (1MB)", type: "pdf", maxKb: 1000, mode: "standard" },
  { label: "Extreme Compression (150KB)", type: "pdf", maxKb: 150, mode: "extreme" }
];

export default function Editor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Editor State
  const [targetFormat, setTargetFormat] = useState('PDF');
  const [quality, setQuality] = useState(85);
  const [targetSize, setTargetSize] = useState(''); 
  const [resizeW, setResizeW] = useState('');
  const [resizeH, setResizeH] = useState('');
  
  const [pdfCompressMode, setPdfCompressMode] = useState('standard');
  const [pdfPassword, setPdfPassword] = useState(''); 
  const [unlockPassword, setUnlockPassword] = useState(''); 
  
  // OCR & KYC State
  const [ocrText, setOcrText] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [watermarkText, setWatermarkText] = useState(`PROVIDED SOLELY FOR KYC PURPOSES ON ${new Date().toLocaleDateString()}`);

  useEffect(() => {
    const fetchDoc = async () => {
      try {
        const response = await api.get('/documents/');
        const doc = response.data.find(d => d.id === id);
        setDocument(doc);
      } catch (error) {
        console.error("Failed to load document", error);
      }
    };
    fetchDoc();
  }, [id]);

  const handleImageEdit = async () => {
    setIsProcessing(true);
    try {
      const response = await api.post(`/editor/${id}/image`, {
        target_format: targetFormat,
        quality: parseInt(quality),
        target_size_kb: targetSize ? parseInt(targetSize) : null,
        resize_width: resizeW ? parseInt(resizeW) : null,
        resize_height: resizeH ? parseInt(resizeH) : null,
        save_as_new: true
      });
      navigate(`/?folderId=${response.data.folder_id}`);
    } catch (error) {
      if (error.response?.data?.detail) alert(error.response.data.detail);
      else alert("Failed to process image.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePdfCompress = async () => {
    setIsProcessing(true);
    try {
      const response = await api.post(`/editor/${id}/compress-pdf`, { 
        mode: pdfCompressMode,
        password: document?.is_locked ? unlockPassword : null,
        target_size_kb: targetSize ? parseInt(targetSize) : null
      });
      navigate(`/?folderId=${response.data.folder_id}`);
    } catch (error) {
      if (error.response?.data?.detail) alert(error.response.data.detail);
      else alert("Failed to compress PDF.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handlePdfLock = async () => {
    if (!pdfPassword) return alert("Please enter a password first.");
    setIsProcessing(true);
    try {
      const response = await api.post(`/editor/${id}/lock-pdf`, { password: pdfPassword });
      navigate(`/?folderId=${response.data.folder_id}`);
    } catch (error) {
      alert("Failed to lock PDF.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleWatermark = async () => {
    setIsProcessing(true);
    try {
      const response = await api.post(`/editor/${id}/watermark`, { 
        text: watermarkText,
        password: document?.is_locked ? unlockPassword : null
      });
      navigate(`/?folderId=${response.data.folder_id}`);
    } catch (error) {
      alert("Failed to apply watermark. Check password if locked.");
    } finally {
      setIsProcessing(false);
    }
  };

  const runOCR = async () => {
    setIsScanning(true);
    setOcrText('');
    try {
      const response = await api.post(`/editor/${id}/ocr?password=${unlockPassword}`);
      setOcrText(response.data.text || "No text found.");
    } catch (error) {
      alert("OCR Scan failed. Check password if locked.");
    } finally {
      setIsScanning(false);
    }
  };

  if (!document) return <div className="p-10 text-center">Loading encrypted file...</div>;

  const isImage = document.content_type.startsWith('image/');
  const isPdf = document.content_type === 'application/pdf';

  return (
    <div className="max-w-5xl mx-auto p-6">
      <button onClick={() => navigate(`/?folderId=${document.folder_id}`)} className="flex items-center gap-2 text-gray-500 hover:text-gray-800 mb-6 transition">
        <ArrowLeft className="w-4 h-4" /> Back to Vault
      </button>

      <div className="bg-white border rounded-xl shadow-sm overflow-hidden flex flex-col md:flex-row">
        
        {/* Left Side: Preview, OCR & Intelligence */}
        <div className="md:w-1/2 flex flex-col bg-gray-50 border-r min-h-[400px]">
          <div className="flex-1 flex flex-col items-center justify-center p-6 border-b">
            {isImage ? (
              <img src={`${API_BASE_URL}/documents/${id}/preview`} alt="Preview" className="max-w-full max-h-[400px] object-contain rounded shadow-sm border" />
            ) : (
              <div className="text-center text-gray-500">
                {document.is_locked ? <Lock className="w-16 h-16 mx-auto mb-2 opacity-30" /> : <FileArchive className="w-16 h-16 mx-auto mb-2 opacity-50" />}
                <p>{document.is_locked ? 'Encrypted PDF' : 'PDF Loaded'}</p>
              </div>
            )}
          </div>
          
          <div className="p-4 bg-white border-b">
            <div className="flex justify-between items-center mb-2">
              <h4 className="font-semibold text-gray-700 text-sm flex items-center gap-2"><ScanText className="w-4 h-4"/> Offline OCR Reader</h4>
              <button onClick={runOCR} disabled={isScanning} className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded transition">
                {isScanning ? 'Scanning...' : 'Extract Text'}
              </button>
            </div>
            <div className="h-24 bg-slate-900 border rounded p-3 text-xs font-mono text-green-400 overflow-y-auto whitespace-pre-wrap">
              {ocrText || "Click 'Extract Text' to dump document text securely..."}
            </div>
          </div>

          <div className="p-4 bg-blue-50">
            <h4 className="font-semibold text-blue-900 text-sm mb-3">Verify & Feed Discrepancy Engine</h4>
            <div className="space-y-2 mb-3">
              <input type="text" placeholder="Verified Name" defaultValue={document.extracted_name || ''} id="verName" className="w-full border-blue-200 rounded p-2 text-sm" />
              <input type="date" placeholder="Verified DOB" defaultValue={document.extracted_dob || ''} id="verDob" className="w-full border-blue-200 rounded p-2 text-sm text-gray-600" />
              <div className="flex items-center gap-2">
                <span className="text-xs text-blue-800 font-medium whitespace-nowrap">Last Biometric Update:</span>
                <input type="date" defaultValue={document.biometric_update_date || ''} id="verBio" className="w-full border-blue-200 rounded p-1.5 text-sm text-gray-600" />
              </div>
            </div>
            <button 
              onClick={async () => {
                try {
                  await api.patch(`/audit/documents/${id}`, {
                    extracted_name: window.document.getElementById('verName').value,
                    extracted_dob: window.document.getElementById('verDob').value,
                    biometric_update_date: window.document.getElementById('verBio').value
                  });
                  alert("Intelligence Data Saved!");
                } catch (e) { alert("Failed to save data. Check console for details."); }
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium py-2 rounded transition"
            >
              Save to Database
            </button>
          </div>
        </div>

        {/* Right Side: Tools */}
        <div className="md:w-1/2 p-6 overflow-y-auto">
          <div className="mb-6 pb-4 border-b">
            <h2 className="text-2xl font-bold text-gray-800">Smart Engine</h2>
            <p className="text-gray-500 text-sm">Target constraints and format editing.</p>
          </div>

          {/* PHASE 6: Application Smart Presets */}
          <div className="mb-6 p-4 bg-indigo-50 border border-indigo-100 rounded-lg">
            <label className="block text-sm font-bold text-indigo-900 mb-2 flex items-center gap-2">
              <Wand2 className="w-4 h-4"/> 1-Click Application Presets
            </label>
            <div className="grid grid-cols-2 gap-2">
              {PORTAL_PRESETS.filter(p => isImage ? p.type === 'image' : p.type === 'pdf').map(preset => (
                <button
                  key={preset.label}
                  onClick={() => {
                    if (preset.type === 'image') {
                      setTargetFormat(preset.format);
                      setTargetSize(preset.maxKb.toString());
                      setResizeW(preset.w ? preset.w.toString() : '');
                      setResizeH(preset.h ? preset.h.toString() : '');
                    } else {
                      setPdfCompressMode(preset.mode);
                      setTargetSize(preset.maxKb.toString());
                    }
                  }}
                  className="text-xs bg-white border border-indigo-200 text-indigo-700 py-1.5 px-2 rounded hover:bg-indigo-600 hover:text-white transition text-left font-medium"
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <p className="text-xs text-indigo-600 mt-2 italic">Clicking a preset will instantly auto-fill common portal dimensions and limits below.</p>
          </div>
            
          {/* Smart Size Constraint - Global */}
          <div className="mb-6 p-4 bg-amber-50 border border-amber-100 rounded-lg">
            <label className="block text-sm font-bold text-amber-900 mb-1">Target Max File Size (Optional)</label>
            <div className="flex items-center gap-2">
              <input 
                type="number" 
                placeholder="e.g. 150" 
                value={targetSize} 
                onChange={(e) => setTargetSize(e.target.value)}
                className="w-full border-amber-200 rounded p-2 text-sm"
              />
              <span className="text-amber-800 font-medium">KB</span>
            </div>
          </div>

          {isImage && (
            <div className="space-y-4 border-b pb-6 mb-6">
              <div className="flex items-center gap-2 mb-2">
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Width (px)</label>
                  <input type="number" placeholder="Auto" value={resizeW} onChange={e => setResizeW(e.target.value)} className="w-full border rounded p-2 text-sm" />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-medium text-gray-600 mb-1">Height (px)</label>
                  <input type="number" placeholder="Auto" value={resizeH} onChange={e => setResizeH(e.target.value)} className="w-full border rounded p-2 text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Convert Format</label>
                <select value={targetFormat} onChange={(e) => setTargetFormat(e.target.value)} className="w-full border rounded-lg p-2 bg-white">
                  <option value="PDF">Document (PDF)</option>
                  <option value="JPEG">Image (JPEG)</option>
                  <option value="PNG">Image (PNG)</option>
                </select>
              </div>
              <button onClick={handleImageEdit} disabled={isProcessing} className="w-full mt-4 flex items-center justify-center gap-2 bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition">
                <Save className="w-5 h-5" /> {isProcessing ? 'Processing in Memory...' : 'Apply & Save as New'}
              </button>
            </div>
          )}

          {isPdf && (
            <div className="space-y-8 border-b pb-6 mb-6">
              <div className="space-y-3 pb-6 border-b">
                <label className="block text-sm font-medium text-gray-700">Compression Level</label>
                <select value={pdfCompressMode} onChange={(e) => setPdfCompressMode(e.target.value)} className="w-full border rounded-lg p-2 bg-white">
                  <option value="standard">Standard (Lossless)</option>
                  <option value="extreme">Extreme (Lossy Scan)</option>
                </select>
                
                {document.is_locked && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg">
                    <label className="block text-sm font-medium text-red-800 mb-1 flex items-center gap-1">
                      <Lock className="w-4 h-4"/> Unlock Document to Process
                    </label>
                    <input 
                      type="password" 
                      placeholder="Enter PDF password..." 
                      value={unlockPassword}
                      onChange={(e) => setUnlockPassword(e.target.value)}
                      className="w-full border-red-200 rounded p-2 text-sm"
                    />
                  </div>
                )}
                <button onClick={handlePdfCompress} disabled={isProcessing} className="w-full flex items-center justify-center gap-2 bg-indigo-600 text-white p-2.5 rounded-lg hover:bg-indigo-700 transition">
                  <FileArchive className="w-4 h-4" /> Compress PDF
                </button>
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-700">Add Password Protection</label>
                <input 
                  type="password" 
                  placeholder="Enter strict password..." 
                  value={pdfPassword}
                  onChange={(e) => setPdfPassword(e.target.value)}
                  className="w-full border rounded-lg p-2 bg-white"
                />
                <button onClick={handlePdfLock} disabled={isProcessing} className="w-full flex items-center justify-center gap-2 bg-slate-800 text-white p-2.5 rounded-lg hover:bg-slate-900 transition">
                  <Lock className="w-4 h-4" /> Encrypt PDF
                </button>
              </div>
            </div>
          )}

          {/* Phase 5: KYC Watermark Stamping */}
          <div className="mb-6 p-4 bg-slate-50 border rounded-lg">
            <label className="block text-sm font-bold text-slate-800 mb-1 flex items-center gap-2">
              <ScanText className="w-4 h-4"/> Anti-Misuse KYC Stamp
            </label>
            <p className="text-xs text-slate-500 mb-2">Visually stamps your document before exporting to third parties.</p>
            <input 
              type="text" 
              value={watermarkText} 
              onChange={(e) => setWatermarkText(e.target.value)}
              className="w-full border-slate-200 rounded p-2 text-xs mb-3 font-mono text-slate-600"
            />
            {document.is_locked && (
              <input 
                type="password" placeholder="PDF Password Required..." 
                value={unlockPassword} onChange={(e) => setUnlockPassword(e.target.value)}
                className="w-full border-red-200 rounded p-2 text-xs mb-3"
              />
            )}
            <button 
              onClick={handleWatermark} disabled={isProcessing}
              className="w-full bg-slate-800 hover:bg-slate-900 text-white p-2.5 text-sm font-medium rounded-lg transition"
            >
              Apply Permanent Stamp
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}