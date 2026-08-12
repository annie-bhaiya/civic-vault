import { useState, useEffect, useRef } from 'react';
import { api, API_BASE_URL } from '../api/client';
import { Link, useSearchParams } from 'react-router-dom';
import { Upload, FileText, Image as ImageIcon, Eye, Edit, Trash2, Type, Lock, Folder as FolderIcon, ShieldCheck, Plus, Edit2, ShieldAlert } from 'lucide-react';

const CIVIC_TAXONOMY = [
  "Aadhaar Card", "PAN Card", "Passport", "Voter ID", "Driving License", 
  "10th Certificate/Marksheet", "12th Certificate/Marksheet", "Ration Card", "Marriage Certificate", "Other"
];

export default function Dashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [documents, setDocuments] = useState([]);
  const [folders, setFolders] = useState([]);
  const [activeFolderId, setActiveFolderId] = useState(searchParams.get('folderId') || null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadType, setUploadType] = useState("Aadhaar Card");
  
  const fileInputRef = useRef(null);

  const fetchData = async () => {
    try {
      const [docRes, folderRes] = await Promise.all([
        api.get('/documents/'),
        api.get('/folders/')
      ]);
      setDocuments(docRes.data);
      setFolders(folderRes.data);
      
      const targetFolder = searchParams.get('folderId');
      if (targetFolder) {
        setActiveFolderId(targetFolder);
      } else if (!activeFolderId && folderRes.data.length > 0) {
        setActiveFolderId(folderRes.data[0].id);
      }
    } catch (error) {
      console.error("Failed to fetch vault data", error);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // --- Folder Management ---
  const handleCreateFolder = async () => {
    const name = window.prompt("Enter new folder name:");
    if (!name) return;
    try {
      const res = await api.post('/folders/', { name });
      setActiveFolderId(res.data.id);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || "Failed to create folder");
    }
  };
  const triggerShareGate = (id) => {
    const pin = window.prompt("SHARE-GATE SECURED\nEnter your master Export PIN to download this file:\n(Default MVP PIN: 1234)");
    if (pin) {
      window.location.href = `${API_BASE_URL}/documents/${id}/download?pin=${pin}`;
    }
  };
  const handleRenameFolder = async (folder) => {
    if (folder.is_immutable) return alert("System folders cannot be renamed.");
    const name = window.prompt("Rename folder to:", folder.name);
    if (!name || name === folder.name) return;
    try {
      await api.patch(`/folders/${folder.id}/rename`, { name });
      fetchData();
    } catch (error) {
      alert("Failed to rename folder");
    }
  };

  const handleDeleteFolder = async (folder) => {
    if (folder.is_immutable) return alert("System folders cannot be deleted.");
    const hasDocs = documents.some(doc => doc.folder_id === folder.id);
    if (hasDocs) return alert("Folder is not empty. Move or delete its documents first.");
    if (!window.confirm(`Delete folder '${folder.name}'?`)) return;
    
    try {
      await api.delete(`/folders/${folder.id}`);
      setActiveFolderId(folders[0].id); // Fallback to root
      fetchData();
    } catch (error) {
      alert("Failed to delete folder");
    }
  };

  const updateFolderUrl = (id) => {
    setActiveFolderId(id);
    setSearchParams({ folderId: id });
  };

  // --- Document Management ---
  const handleFileSelect = (e) => {
    if (e.target.files[0]) {
      setUploadFile(e.target.files[0]);
      setShowUploadModal(true);
    }
  };

  const executeUpload = async () => {
    if (!uploadFile || !activeFolderId) return;
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('title', uploadFile.name.split('.')[0]);
    formData.append('document_type', uploadType);
    formData.append('folder_id', activeFolderId);

    setIsUploading(true);
    try {
      await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      fetchData();
      setShowUploadModal(false);
      setUploadFile(null);
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDoc = async (id) => {
    if (!window.confirm("Permanently delete this encrypted file?")) return;
    try {
      await api.delete(`/documents/${id}`);
      fetchData();
    } catch (error) {
      console.error("Delete failed", error);
    }
  };

  const activeFolder = folders.find(f => f.id === activeFolderId);
  const activeDocs = documents.filter(doc => doc.folder_id === activeFolderId);

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      
      {/* SIDEBAR: Folder Organization */}
      <div className="w-72 bg-slate-900 text-slate-300 flex flex-col h-full border-r border-slate-800">
        <div className="p-6 pb-4 border-b border-slate-800 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-blue-500"/> Civic Vault
            </h1>
            <p className="text-xs text-slate-500 mt-1 uppercase tracking-wider">Encrypted Ontology</p>
          </div>
          <button onClick={handleCreateFolder} className="p-1.5 bg-slate-800 hover:bg-slate-700 rounded text-white transition" title="New Folder">
            <Plus className="w-4 h-4" />
          </button>
        </div>
        
        {/* NEW: Smart Audit Link */}
        <div className="p-4 border-b border-slate-800">
          <Link to="/audit" className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white py-2 rounded-lg font-medium transition shadow-md">
            <ShieldAlert className="w-4 h-4" /> Run Civic Audit
          </Link>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {folders.map(folder => (
            <button
              key={folder.id}
              onClick={() => updateFolderUrl(folder.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-left text-sm ${
                activeFolderId === folder.id 
                  ? 'bg-blue-600 text-white shadow-md' 
                  : 'hover:bg-slate-800 hover:text-white'
              }`}
            >
              <FolderIcon className={`w-4 h-4 ${folder.is_immutable && activeFolderId !== folder.id ? 'text-amber-500' : ''}`} />
              <span className="truncate">{folder.name}</span>
              {folder.is_immutable && (
                <Lock className="w-3 h-3 ml-auto opacity-50" title="Immutable System Folder" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="bg-white border-b px-8 py-5 flex justify-between items-center shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-2xl font-bold text-gray-800">
              {activeFolder?.name || "Loading..."}
            </h2>
            {activeFolder && !activeFolder.is_immutable && (
              <div className="flex items-center gap-1 opacity-60 hover:opacity-100 transition">
                <button onClick={() => handleRenameFolder(activeFolder)} className="p-1.5 hover:bg-gray-100 rounded text-gray-600" title="Rename Folder">
                  <Edit2 className="w-4 h-4" />
                </button>
                <button onClick={() => handleDeleteFolder(activeFolder)} className="p-1.5 hover:bg-red-50 rounded text-red-600" title="Delete Folder">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
          <div>
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} className="hidden" />
            <button 
              onClick={() => fileInputRef.current.click()}
              className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg hover:bg-blue-700 transition font-medium shadow-sm"
            >
              <Upload className="w-5 h-5" /> Add to Folder
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {activeDocs.map((doc) => (
              <div key={doc.id} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition flex flex-col relative group">
                
                {doc.is_locked && (
                  <div className="absolute top-4 left-4 p-1.5 bg-slate-800 rounded-md text-white shadow-sm">
                    <Lock className="w-4 h-4" />
                  </div>
                )}
                
                <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => handleDeleteDoc(doc.id)} className="p-1.5 bg-red-50 rounded-md text-red-600 hover:bg-red-100">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-start justify-between mb-3 mt-2">
                  <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
                    {doc.content_type.includes('pdf') ? <FileText className="w-7 h-7" /> : <ImageIcon className="w-7 h-7" />}
                  </div>
                </div>
                
                <h3 className="font-semibold text-gray-800 truncate mb-1 pr-8">{doc.title}</h3>
                <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-3">{doc.document_type}</p>
                
                <div className="flex justify-between items-center mb-5 text-sm text-gray-500 border-t pt-3">
                  <span className="truncate">{doc.original_filename}</span>
                  <span className="font-mono bg-gray-100 px-2 py-0.5 rounded ml-2">
                    {(doc.file_size_bytes / 1024).toFixed(1)} KB
                  </span>
                </div>
                
                <div className="mt-auto flex gap-2">
                   <a
                    href={`${API_BASE_URL}/documents/${doc.id}/preview`} 
                    target="_blank" rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-1 bg-gray-50 border text-gray-700 px-3 py-2 rounded-lg hover:bg-gray-100 transition text-sm font-medium"
                  >
                    <Eye className="w-4 h-4" /> Preview
                  </a>
                  <button 
                    onClick={() => triggerShareGate(doc.id)}
                    className="flex-1 flex items-center justify-center gap-1 bg-gray-50 border border-gray-200 text-gray-700 px-3 py-2 rounded-lg hover:bg-red-50 hover:text-red-700 hover:border-red-200 transition text-sm font-medium"
                  >
                    <Lock className="w-4 h-4" /> Export
                  </button>
                  <Link 
                    to={`/editor/${doc.id}`}
                    className="flex items-center justify-center gap-1 bg-slate-800 text-white px-3 py-2 rounded-lg hover:bg-slate-900 transition text-sm font-medium"
                  >
                    <Edit className="w-4 h-4" /> Edit
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* UPLOAD MODAL */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md">
            <h3 className="text-xl font-bold text-gray-800 mb-4">Ontology Tagging</h3>
            <p className="text-sm text-gray-500 mb-6">Categorize this document to maintain strict civic taxonomy in your vault.</p>
            
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">Document Type</label>
              <select 
                value={uploadType} 
                onChange={(e) => setUploadType(e.target.value)}
                className="w-full border-gray-300 rounded-lg p-2.5 bg-gray-50 border focus:ring-2 focus:ring-blue-500"
              >
                {CIVIC_TAXONOMY.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            
            <div className="flex gap-3">
              <button 
                onClick={() => { setShowUploadModal(false); setUploadFile(null); }}
                className="flex-1 py-2.5 rounded-lg border text-gray-600 hover:bg-gray-50 font-medium transition"
              >
                Cancel
              </button>
              <button 
                onClick={executeUpload}
                disabled={isUploading}
                className="flex-1 py-2.5 rounded-lg bg-blue-600 text-white hover:bg-blue-700 font-medium transition disabled:opacity-50"
              >
                {isUploading ? 'Encrypting...' : 'Secure Upload'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}