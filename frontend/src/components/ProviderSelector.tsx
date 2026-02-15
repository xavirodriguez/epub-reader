import React, { useState, useEffect } from 'react';
import { Server, Cloud, Zap, CheckCircle, XCircle } from 'lucide-react';
import { backendService, TTSProvider } from '../services/backendService';

export const ProviderSelector: React.FC = () => {
  const [provider, setProvider] = useState<TTSProvider>(TTSProvider.Auto);
  const [backendHealth, setBackendHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Cargar preferencia guardada
    const saved = localStorage.getItem('tts_provider') as TTSProvider;
    if (saved) {
      setProvider(saved);
      backendService.setProvider(saved);
    }

    // Verificar salud del backend
    checkHealth();
  }, []);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const health = await backendService.healthCheck();
      setBackendHealth(health);
    } catch (error) {
      setBackendHealth({ status: 'unhealthy' });
    }
    setLoading(false);
  };

  const handleProviderChange = (newProvider: TTSProvider) => {
    setProvider(newProvider);
    localStorage.setItem('tts_provider', newProvider);
    backendService.setProvider(newProvider);
  };

  const isBackendHealthy = backendHealth?.status === 'healthy';

  return (
    <div className="bg-white rounded-xl p-4 border shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm text-slate-700">Motor TTS</h3>
        <button
          onClick={checkHealth}
          disabled={loading}
          className="text-xs text-indigo-600 hover:text-indigo-700"
        >
          {loading ? 'Verificant...' : 'Verificar'}
        </button>
      </div>

      {/* Selector de provider */}
      <div className="space-y-2">
        <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
          <input
            type="radio"
            name="tts-provider"
            checked={provider === TTSProvider.Auto}
            onChange={() => handleProviderChange(TTSProvider.Auto)}
            className="text-indigo-600"
          />
          <Zap className="w-5 h-5 text-amber-500" />
          <div className="flex-1">
            <div className="font-medium text-sm">Auto (Recomanat)</div>
            <div className="text-xs text-slate-500">Local + Gemini fallback</div>
          </div>
        </label>

        <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
          <input
            type="radio"
            name="tts-provider"
            checked={provider === TTSProvider.Local}
            onChange={() => handleProviderChange(TTSProvider.Local)}
            className="text-indigo-600"
            disabled={!isBackendHealthy}
          />
          <Server className="w-5 h-5 text-blue-500" />
          <div className="flex-1">
            <div className="font-medium text-sm">Només Local</div>
            <div className="text-xs text-slate-500">Sense límits, més ràpid</div>
          </div>
          {isBackendHealthy ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500" />
          )}
        </label>

        <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
          <input
            type="radio"
            name="tts-provider"
            checked={provider === TTSProvider.Gemini}
            onChange={() => handleProviderChange(TTSProvider.Gemini)}
            className="text-indigo-600"
          />
          <Cloud className="w-5 h-5 text-purple-500" />
          <div className="flex-1">
            <div className="font-medium text-sm">Només Gemini</div>
            <div className="text-xs text-slate-500">Qualitat màxima, amb quota</div>
          </div>
        </label>
      </div>

      {/* Estado del backend */}
      {backendHealth && (
        <div className="mt-4 p-3 bg-slate-50 rounded-lg text-xs">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium">Backend Local:</span>
            <span className={`font-semibold ${
              isBackendHealthy ? 'text-green-600' : 'text-red-600'
            }`}>
              {backendHealth.status}
            </span>
          </div>

          {backendHealth.engines && (
            <div className="space-y-1">
              {Object.entries(backendHealth.engines).map(([engine, healthy]) => (
                <div key={engine} className="flex items-center justify-between text-slate-600">
                  <span>{engine}:</span>
                  <span>{healthy ? '✓' : '✗'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
