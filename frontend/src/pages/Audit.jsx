import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Link } from 'react-router-dom';
import { ShieldAlert, AlertTriangle, Info, ShieldCheck, ArrowLeft, BookOpen, Clock, AlertCircle } from 'lucide-react';

export default function Audit() {
  const [report, setReport] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        const response = await api.get('/audit/report');
        setReport(response.data);
      } catch (error) {
        console.error("Failed to load audit report", error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAudit();
  }, []);

  if (isLoading) return <div className="p-10 text-center">Running Civic Audit...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-12">
      <div className="max-w-5xl mx-auto">
        
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <ShieldAlert className="w-8 h-8 text-blue-600" /> Smart Civic Audit
            </h1>
            <p className="text-gray-500 mt-1">Cross-referencing engine & temporal tracking</p>
          </div>
          <Link to="/" className="flex items-center gap-2 bg-white border px-4 py-2 rounded-lg text-gray-600 hover:bg-gray-50 transition">
            <ArrowLeft className="w-4 h-4"/> Back to Vault
          </Link>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Discrepancy Engine Panel */}
          <div className="lg:col-span-2 space-y-6">
            <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500"/> Ranked Discrepancies
            </h2>
            
            {report.discrepancies.length === 0 ? (
              <div className="bg-white border rounded-xl p-8 text-center shadow-sm">
                <ShieldCheck className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-800">No Discrepancies Found</h3>
                <p className="text-sm text-gray-500 mt-1">Make sure you have fed OCR data via the Document Editor.</p>
              </div>
            ) : (
              report.discrepancies.map((disc, idx) => (
                <div key={idx} className={`bg-white border-l-4 rounded-xl p-5 shadow-sm ${
                  disc.severity === 'Critical' ? 'border-red-500' : 
                  disc.severity === 'Moderate' ? 'border-amber-500' : 'border-blue-500'
                }`}>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-gray-800">{disc.title}</h3>
                    <span className={`text-xs font-bold px-2 py-1 rounded uppercase ${
                      disc.severity === 'Critical' ? 'bg-red-100 text-red-700' : 
                      disc.severity === 'Moderate' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                    }`}>{disc.severity}</span>
                  </div>
                  <p className="text-sm text-gray-600">{disc.description}</p>
                </div>
              ))
            )}

            {/* Temporal Alerts */}
            <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2 mt-8">
              <Clock className="w-5 h-5 text-blue-500"/> Temporal Expirations
            </h2>
            {report.temporal_alerts.map((alert, idx) => (
              <div key={idx} className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex gap-4 shadow-sm">
                <AlertCircle className="w-6 h-6 text-blue-600 shrink-0" />
                <div>
                  <h4 className="font-semibold text-blue-900">{alert.document_type}</h4>
                  <p className="text-sm text-blue-800 mt-1">{alert.message}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Hardcoded How-To Guides */}
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-500"/> Resolution Guides
            </h2>
            
            {report.guides.map((guide, idx) => (
              <div key={idx} className="bg-white border rounded-xl shadow-sm overflow-hidden">
                <div className="bg-slate-900 p-4">
                  <h3 className="font-bold text-white text-sm">{guide.title}</h3>
                </div>
                <div className="p-4">
                  <p className="text-xs text-gray-600 mb-4">{guide.content}</p>
                  
                  <div className="mb-3">
                    <strong className="text-xs text-green-600 uppercase tracking-wider block mb-1">Do's</strong>
                    <ul className="text-xs text-gray-600 list-disc pl-4 space-y-1">
                      {guide.dos.map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  </div>
                  
                  <div className="mb-4">
                    <strong className="text-xs text-red-600 uppercase tracking-wider block mb-1">Don'ts</strong>
                    <ul className="text-xs text-gray-600 list-disc pl-4 space-y-1">
                      {guide.donts.map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  </div>
                  
                  <a href={guide.link} target="_blank" rel="noopener noreferrer" className="block text-center text-xs font-semibold bg-indigo-50 text-indigo-700 py-2 rounded hover:bg-indigo-100 transition">
                    Visit Official Portal
                  </a>
                </div>
              </div>
            ))}
          </div>

        </div>
      </div>
    </div>
  );
}