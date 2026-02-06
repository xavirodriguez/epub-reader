
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { BookOpen, Play, Pause, Square, ChevronLeft, ChevronRight, Upload, Volume2, Settings2, Menu, X, Book as BookIcon, Languages, Download, Loader2, AlertCircle, Clock, Coffee } from 'lucide-react';
import { geminiTTS } from './services/geminiService';
import { decodeBase64, decodeAudioData, createWavBlob } from './services/audioService';
import { VoiceName, Chapter, BookMetadata, PlaybackState, Dialect } from './types';
import { SUPPORTED_VOICES, APP_NAME } from './constants';

declare const ePub: any;

const App: React.FC = () => {
  const [book, setBook] = useState<any>(null);
  const [rendition, setRendition] = useState<any>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [metadata, setMetadata] = useState<BookMetadata | null>(null);
  const [currentLocation, setCurrentLocation] = useState<string>('');
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWaitingQuota, setIsWaitingQuota] = useState(false);
  const [exportProgress, setExportProgress] = useState<{current: number, total: number, isWaiting?: boolean} | null>(null);
  
  const [playback, setPlayback] = useState<PlaybackState>({
    isPlaying: false,
    isPaused: false,
    currentChapterIndex: 0,
    currentSentenceIndex: 0,
    voice: VoiceName.Kore,
    dialect: Dialect.Standard
  });

  const [currentTextChunks, setCurrentTextChunks] = useState<string[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const viewerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleError = (e: any) => {
      const isResizeObserverError = 
        e.message?.includes('ResizeObserver loop') || 
        (e.error && e.error.message?.includes('ResizeObserver loop'));

      if (isResizeObserverError) {
        e.stopImmediatePropagation();
        e.preventDefault();
      }
    };
    
    window.addEventListener('error', handleError, true);
    return () => window.removeEventListener('error', handleError, true);
  }, []);

  useEffect(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
    }
  }, []);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setError(null);

    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const data = e.target?.result;
        if (!data) return;

        const newBook = ePub(data);
        setBook(newBook);

        const meta = await newBook.loaded.metadata;
        setMetadata({
          title: meta.title,
          author: meta.creator,
          cover: await newBook.coverUrl()
        });

        const nav = await newBook.loaded.navigation;
        const chaptersList = nav.toc.map((item: any) => ({
          id: item.id,
          title: item.label,
          href: item.href
        }));
        setChapters(chaptersList);

        if (viewerRef.current) {
          viewerRef.current.innerHTML = '';
          const newRendition = newBook.renderTo(viewerRef.current, {
            width: '100%',
            height: '100%',
            flow: 'paginated',
            manager: 'default',
            allowScriptedContent: true
          });
          setRendition(newRendition);
          await newRendition.display();

          newRendition.on('relocated', (location: any) => {
            setCurrentLocation(location.start.cfi);
          });
        }
        setIsLoading(false);
      };
      reader.readAsArrayBuffer(file);
    } catch (err) {
      setError("Error carregant el fitxer EPUB.");
      setIsLoading(false);
    }
  };

  const stopAudio = useCallback(() => {
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (e) {}
      currentSourceRef.current = null;
    }
    setPlayback(prev => ({ ...prev, isPlaying: false, isPaused: false }));
    setIsWaitingQuota(false);
  }, []);

  /**
   * Ultra-aggressive chunking to minimize the number of API calls.
   * We target 5000 characters per request.
   */
  const chunkText = (text: string, maxLen: number = 5000): string[] => {
    const paragraphs = text.split(/\n+/).filter(p => p.trim().length > 0);
    const chunks: string[] = [];
    let currentChunk = "";

    for (const para of paragraphs) {
      // If adding this paragraph fits, add it
      if ((currentChunk + para).length <= maxLen) {
        currentChunk += (currentChunk ? "\n\n" : "") + para;
      } else {
        // If current chunk is already big enough, push it
        if (currentChunk.trim()) {
          chunks.push(currentChunk.trim());
        }
        
        // Handle oversized paragraphs by splitting into sentences
        if (para.length > maxLen) {
          const sentences = para.match(/[^.!?]+[.!?]+/g) || [para];
          currentChunk = "";
          for (const sentence of sentences) {
            if ((currentChunk + sentence).length > maxLen) {
              if (currentChunk.trim()) chunks.push(currentChunk.trim());
              currentChunk = sentence;
            } else {
              currentChunk += (currentChunk ? " " : "") + sentence;
            }
          }
        } else {
          currentChunk = para;
        }
      }
    }
    
    if (currentChunk.trim()) chunks.push(currentChunk.trim());
    return chunks;
  };

  const playNextChunk = async (chunks: string[], index: number) => {
    if (index >= chunks.length) {
      stopAudio();
      return;
    }

    setPlayback(prev => ({ ...prev, currentSentenceIndex: index, isPlaying: true }));
    setError(null);
    setIsWaitingQuota(false);

    try {
      const base64Audio = await geminiTTS.generateSpeech(chunks[index], playback.voice, playback.dialect);
      if (base64Audio && audioContextRef.current) {
        const decoded = decodeBase64(base64Audio);
        const buffer = await decodeAudioData(decoded, audioContextRef.current);
        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);
        currentSourceRef.current = source;
        source.start(0);
        
        source.onended = () => {
          if (currentSourceRef.current === source) {
            // Wait 10s between requests to be extra safe on free tier RPM
            setTimeout(() => playNextChunk(chunks, index + 1), 10000);
          }
        };
      }
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.includes('429')) {
        setIsWaitingQuota(true);
        setError("S'ha esgotat la quota gratuita temporalment. L'aplicació s'ha pausat per a recuperar l'accés.");
      } else {
        setError("S'ha produït un error de connexió.");
        stopAudio();
      }
    }
  };

  const downloadChapterAudio = async (chapter: Chapter) => {
    if (!book) return;
    setExportProgress({ current: 0, total: 1 });
    setError(null);
    
    try {
      const section = book.spine.get(chapter.href);
      await section.load(book.load.bind(book));
      const doc = section.document;
      const text = doc.body.innerText;
      
      const chunks = chunkText(text, 5000); // Maximize each request payload
      
      if (chunks.length === 0) {
        setExportProgress(null);
        return;
      }

      setExportProgress({ current: 0, total: chunks.length });
      const pcmChunks: Int16Array[] = [];

      for (let i = 0; i < chunks.length; i++) {
        setExportProgress({ current: i + 1, total: chunks.length, isWaiting: false });
        
        try {
          const base64Audio = await geminiTTS.generateSpeech(chunks[i], playback.voice, playback.dialect);
          if (base64Audio) {
            const rawBytes = decodeBase64(base64Audio);
            pcmChunks.push(new Int16Array(rawBytes.buffer));
          }
          // Mandatory cooldown for export to prevent 429
          await new Promise(resolve => setTimeout(resolve, 12000));
        } catch (innerErr: any) {
           const msg = innerErr?.message || "";
           if (msg.includes('429')) {
              setExportProgress(prev => prev ? { ...prev, isWaiting: true } : null);
              throw new Error("QUOTA_EXCEEDED");
           }
           throw innerErr;
        }
      }

      const totalLen = pcmChunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const combinedPcm = new Int16Array(totalLen);
      let offset = 0;
      for (const chunk of pcmChunks) {
        combinedPcm.set(chunk, offset);
        offset += chunk.length;
      }

      const blob = createWavBlob(combinedPcm, 24000);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter.title.replace(/[/\\?%*:|"<>]/g, '-')}.wav`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      if (err.message === "QUOTA_EXCEEDED") {
        setError("La quota gratuita està saturada. S'ha de fer una pausa de 5 minuts.");
      } else {
        setError("Error en generar l'àudio.");
      }
    } finally {
      setExportProgress(null);
    }
  };

  const handleTogglePlay = async () => {
    if (playback.isPlaying) {
      stopAudio();
      return;
    }
    setError(null);
    if (!rendition) return;
    
    const contents = rendition.getContents();
    if (!contents || contents.length === 0) return;

    let fullPageText = '';
    contents.forEach((content: any) => {
      const body = content.document.body;
      if (body) fullPageText += body.innerText;
    });

    const chunks = chunkText(fullPageText, 5000);
    if (chunks.length === 0) return;
    
    setCurrentTextChunks(chunks);
    playNextChunk(chunks, 0);
  };

  const jumpToChapter = (href: string) => {
    if (rendition) {
      rendition.display(href);
      setIsSidebarOpen(false);
      stopAudio();
      setError(null);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="h-16 flex items-center justify-between px-4 md:px-8 border-b bg-white z-20 sticky top-0">
        <div className="flex items-center gap-3">
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
            <Menu className="w-6 h-6 text-slate-600" />
          </button>
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-1.5 rounded-lg">
              <BookIcon className="w-5 h-5 text-white" />
            </div>
            <h1 className="font-bold text-xl tracking-tight hidden sm:block">{APP_NAME}</h1>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-full flex items-center gap-2 text-sm font-medium transition-all shadow-sm">
            <Upload className="w-4 h-4" />
            <span className="hidden sm:inline">Upload EPUB</span>
            <input type="file" accept=".epub" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden relative">
        {isSidebarOpen && <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-30 lg:hidden" onClick={() => setIsSidebarOpen(false)} />}

        {/* Sidebar */}
        <aside className={`
          fixed lg:static inset-y-0 left-0 w-80 bg-white border-r z-40 transform transition-transform duration-300 ease-in-out
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 lg:w-0 lg:opacity-0'}
          flex flex-col
        `}>
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-slate-700 uppercase text-xs tracking-widest">Capítols</h2>
            <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden p-1">
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {chapters.length > 0 ? (
              chapters.map((chapter, idx) => (
                <div key={chapter.id + idx} className="group flex items-center gap-1 rounded-lg hover:bg-indigo-50 transition-all">
                  <button
                    onClick={() => jumpToChapter(chapter.href)}
                    className="flex-1 text-left px-3 py-2.5 text-sm text-slate-600 hover:text-indigo-600 line-clamp-2 transition-colors"
                  >
                    {chapter.title}
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); downloadChapterAudio(chapter); }}
                    className="p-2 opacity-0 group-hover:opacity-100 hover:bg-indigo-100 rounded-md text-indigo-600 transition-all"
                    title="Exportar àudio del capítol"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-slate-400 text-sm">No hi ha capítols</div>
            )}
          </div>
          {metadata && (
            <div className="p-4 border-t bg-slate-50">
              <div className="flex items-center gap-3">
                {metadata.cover && <img src={metadata.cover} alt="Cover" className="w-12 h-16 object-cover rounded shadow-sm" />}
                <div className="min-w-0">
                  <p className="font-bold text-sm text-slate-800 truncate">{metadata.title}</p>
                  <p className="text-xs text-slate-500 truncate">{metadata.author}</p>
                </div>
              </div>
            </div>
          )}
        </aside>

        {/* Main */}
        <main className="flex-1 flex flex-col bg-slate-50 relative overflow-hidden">
          {(isLoading || exportProgress || isWaitingQuota) && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm z-50">
              <div className="text-center bg-white p-10 rounded-[3rem] shadow-2xl border border-slate-100 max-w-sm">
                {isWaitingQuota ? (
                  <Coffee className="w-16 h-16 text-amber-500 animate-bounce mx-auto mb-6" />
                ) : (
                  <Loader2 className={`w-14 h-14 ${exportProgress?.isWaiting ? 'text-amber-500' : 'text-indigo-600'} animate-spin mx-auto mb-6`} />
                )}
                
                <h3 className="text-xl font-bold text-slate-800 mb-2">
                  {isWaitingQuota ? 'Pausa de Quota' : exportProgress ? 'Generant Àudio' : 'Carregant Llibre'}
                </h3>
                
                <p className="text-slate-500 text-sm leading-relaxed mb-6 px-4">
                  {isWaitingQuota 
                    ? "S'ha arribat al límit de la capa gratuita. L'aplicació està esperant uns minuts per a poder continuar sense errors." 
                    : exportProgress 
                    ? `Processant el bloc ${exportProgress.current} de ${exportProgress.total}...`
                    : "S'està preparant el visor del llibre."}
                </p>

                {exportProgress && (
                  <div className="w-full">
                    <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden mb-2">
                      <div 
                        className={`h-full ${exportProgress.isWaiting ? 'bg-amber-500' : 'bg-indigo-600'} transition-all duration-700 ease-out`} 
                        style={{ width: `${(exportProgress.current / exportProgress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}

                {isWaitingQuota && (
                  <button 
                    onClick={stopAudio}
                    className="mt-4 px-6 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-full text-xs font-bold transition-colors"
                  >
                    Aturar lectura
                  </button>
                )}
              </div>
            </div>
          )}

          {!book && !isLoading && (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-lg mx-auto">
              <div className="bg-indigo-100 p-6 rounded-3xl mb-6">
                <BookOpen className="w-16 h-16 text-indigo-600" />
              </div>
              <h2 className="text-3xl font-bold text-slate-800 mb-4">Lector d'Audiollibres IA</h2>
              <p className="text-slate-500 mb-8 leading-relaxed">
                Puja el teu EPUB i escolta'l amb veus realistes. Hem optimitzat el sistema per a funcionar amb la capa gratuita de Gemini 2.5 Flash.
              </p>
              <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3 rounded-full flex items-center gap-3 font-semibold transition-all shadow-xl hover:scale-105 active:scale-95">
                <Upload className="w-5 h-5" />
                <span>Triar fitxer EPUB</span>
                <input type="file" accept=".epub" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>
          )}

          {error && !isWaitingQuota && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-red-50 text-red-700 px-6 py-4 rounded-2xl border border-red-200 shadow-xl z-50 flex items-center gap-3 max-w-md animate-in slide-in-from-top-4">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-bold">Problema de connexió</p>
                <p className="text-xs opacity-80">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="p-1 hover:bg-red-100 rounded">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="flex-1 w-full h-full relative overflow-hidden bg-slate-50">
             <div ref={viewerRef} className={`absolute inset-0 ${book ? 'opacity-100' : 'opacity-0'} transition-opacity duration-500`} />
          </div>

          {book && (
            <div className="absolute inset-x-0 bottom-32 flex justify-between px-8 pointer-events-none">
              <button onClick={() => rendition?.prev()} className="pointer-events-auto p-4 bg-white/90 hover:bg-white rounded-full shadow-lg border border-slate-200 transition-all hover:scale-110">
                <ChevronLeft className="w-6 h-6 text-slate-700" />
              </button>
              <button onClick={() => rendition?.next()} className="pointer-events-auto p-4 bg-white/90 hover:bg-white rounded-full shadow-lg border border-slate-200 transition-all hover:scale-110">
                <ChevronRight className="w-6 h-6 text-slate-700" />
              </button>
            </div>
          )}
        </main>
      </div>

      {/* Footer */}
      {book && (
        <footer className="h-28 sm:h-24 bg-white border-t px-4 md:px-8 flex flex-col sm:flex-row items-center justify-between z-30 shadow-[0_-4px_20px_-5px_rgba(0,0,0,0.1)] gap-2 py-2 sm:py-0">
          <div className="flex items-center gap-4 flex-1 w-full sm:w-auto">
            <div className="flex flex-col sm:flex-row gap-4 w-full">
              <div className="min-w-[120px]">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Veu</p>
                <select value={playback.voice} onChange={(e) => setPlayback(prev => ({ ...prev, voice: e.target.value as VoiceName }))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-medium focus:ring-2 focus:ring-indigo-500 outline-none">
                  {SUPPORTED_VOICES.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </div>
              <div className="min-w-[150px]">
                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1 flex items-center gap-1"><Languages className="w-3 h-3" /> Variant</p>
                <select value={playback.dialect} onChange={(e) => setPlayback(prev => ({ ...prev, dialect: e.target.value as Dialect }))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs font-medium focus:ring-2 focus:ring-indigo-500 outline-none">
                  <option value={Dialect.Standard}>{Dialect.Standard}</option>
                  <option value={Dialect.Valencian}>{Dialect.Valencian}</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 flex-1 justify-center relative">
            <button onClick={handleTogglePlay} disabled={isLoading || isWaitingQuota}
              className={`w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center transition-all shadow-lg active:scale-95 ${playback.isPlaying ? 'bg-red-500 hover:bg-red-600' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
              {playback.isPlaying ? <Square className="w-5 h-5 sm:w-6 sm:h-6 text-white fill-white" /> : <Play className="w-6 h-6 sm:w-7 sm:h-7 text-white fill-white ml-1" />}
            </button>
            {playback.isPlaying && (
              <div className="fixed bottom-32 left-1/2 -translate-x-1/2 bg-indigo-900/95 backdrop-blur px-6 py-4 rounded-2xl border border-indigo-500/30 text-white w-[90%] max-w-xl text-center shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="flex items-center gap-3 justify-center mb-2">
                  <Clock className="w-4 h-4 text-indigo-300 animate-pulse" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-300">Optimització de Quota • {playback.dialect}</span>
                </div>
                <p className="text-sm font-medium italic opacity-90 line-clamp-2">"{currentTextChunks[playback.currentSentenceIndex]?.substring(0, 150)}..."</p>
              </div>
            )}
          </div>

          <div className="flex items-center gap-6 flex-1 justify-end hidden sm:flex">
             <div className="text-right">
               <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-0.5">Mode Capa Gratuïta</p>
               <p className={`text-sm font-semibold ${isWaitingQuota ? 'text-amber-500' : 'text-emerald-500'}`}>{isWaitingQuota ? 'Esperant...' : 'Actiu'}</p>
             </div>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;
