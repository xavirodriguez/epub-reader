
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Play, Square, ChevronLeft, ChevronRight, Upload, Menu, X, Book as BookIcon, Download, Loader2, AlertCircle, Coffee, Sparkles, Users } from 'lucide-react';
import { geminiTTS } from './services/geminiService';
import { decodeBase64, decodeAudioData, createWavBlob } from './services/audioService';
import { VoiceName, Chapter, BookMetadata, PlaybackState, Dialect } from './types';

declare const ePub: any;

const App: React.FC = () => {
  const [book, setBook] = useState<any>(null);
  const [rendition, setRendition] = useState<any>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [metadata, setMetadata] = useState<BookMetadata | null>(null);
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isWaitingQuota, setIsWaitingQuota] = useState(false);
  const [exportProgress, setExportProgress] = useState<{current: number, total: number} | null>(null);
  
  const [playback, setPlayback] = useState<PlaybackState>({
    isPlaying: false,
    isPaused: false,
    currentChapterIndex: 0,
    currentSentenceIndex: 0,
    voice: VoiceName.Kore,
    dialect: Dialect.Standard
  });

  const audioContextRef = useRef<AudioContext | null>(null);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const viewerRef = useRef<HTMLDivElement>(null);

  // FIX: Silenciar l'error de ResizeObserver
  useEffect(() => {
    const errorHandler = (e: any) => {
      if (e.message?.includes('ResizeObserver') || e.message?.includes('undelivered notifications')) {
        e.stopImmediatePropagation();
      }
    };
    window.addEventListener('error', errorHandler);
    return () => window.removeEventListener('error', errorHandler);
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
        setMetadata({ title: meta.title, author: meta.creator, cover: await newBook.coverUrl() });
        const nav = await newBook.loaded.navigation;
        setChapters(nav.toc.map((item: any) => ({ id: item.id, title: item.label, href: item.href })));
        
        if (viewerRef.current) {
          viewerRef.current.innerHTML = '';
          const newRendition = newBook.renderTo(viewerRef.current, { width: '100%', height: '100%', flow: 'paginated' });
          setRendition(newRendition);
          // Usem requestAnimationFrame per evitar conflictes de ResizeObserver
          requestAnimationFrame(() => newRendition.display());
        }
        setIsLoading(false);
      };
      reader.readAsArrayBuffer(file);
    } catch (err) { setError("Error carregant EPUB"); setIsLoading(false); }
  };

  const stopAudio = useCallback(() => {
    if (currentSourceRef.current) { try { currentSourceRef.current.stop(); } catch (e) {} currentSourceRef.current = null; }
    setPlayback(prev => ({ ...prev, isPlaying: false }));
    setIsWaitingQuota(false);
  }, []);

  // fragments massius (6000 caràcters) per reduir crides
  const chunkText = (text: string, maxLen: number = 6000): string[] => {
    const paragraphs = text.split(/\n+/).filter(p => p.trim().length > 0);
    const chunks: string[] = [];
    let currentChunk = "";
    for (const para of paragraphs) {
      if ((currentChunk + para).length <= maxLen) {
        currentChunk += (currentChunk ? "\n\n" : "") + para;
      } else {
        if (currentChunk.trim()) chunks.push(currentChunk.trim());
        currentChunk = para;
      }
    }
    if (currentChunk.trim()) chunks.push(currentChunk.trim());
    return chunks;
  };

  const playNextChunk = async (chunks: string[], index: number) => {
    if (index >= chunks.length) { stopAudio(); return; }
    setPlayback(prev => ({ ...prev, currentSentenceIndex: index, isPlaying: true }));
    setIsWaitingQuota(false);
    try {
      const base64Audio = await geminiTTS.generateSpeech(chunks[index], playback.voice, playback.dialect);
      if (base64Audio && audioContextRef.current) {
        const buffer = await decodeAudioData(decodeBase64(base64Audio), audioContextRef.current);
        const source = audioContextRef.current.createBufferSource();
        source.buffer = buffer;
        source.connect(audioContextRef.current.destination);
        currentSourceRef.current = source;
        source.start(0);
        source.onended = () => { if (currentSourceRef.current === source) setTimeout(() => playNextChunk(chunks, index + 1), 10000); };
      }
    } catch (err: any) {
      if (err?.message?.includes('429')) { setIsWaitingQuota(true); setError("IA saturada. Aturant..."); }
      else { setError("Error en narració."); stopAudio(); }
    }
  };

  // Funció per baixar una meitat del capítol
  const downloadSegment = async (chapter: Chapter, part: 1 | 2) => {
    if (!book) return;
    setError(null);
    setExportProgress({ current: 0, total: 1 });
    try {
      const section = book.spine.get(chapter.href);
      await section.load(book.load.bind(book));
      const fullText = section.document.body.innerText;
      
      // Dividim el text del capítol en dues meitats
      const midPoint = Math.floor(fullText.length / 2);
      const targetText = part === 1 ? fullText.substring(0, midPoint) : fullText.substring(midPoint);
      
      const chunks = chunkText(targetText, 6000);
      setExportProgress({ current: 0, total: chunks.length });
      
      const pcmChunks: Int16Array[] = [];
      for (let i = 0; i < chunks.length; i++) {
        setExportProgress({ current: i + 1, total: chunks.length });
        const base64 = await geminiTTS.generateSpeech(chunks[i], playback.voice, playback.dialect);
        if (base64) {
          pcmChunks.push(new Int16Array(decodeBase64(base64).buffer));
        }
        if (i < chunks.length - 1) await new Promise(r => setTimeout(r, 15000));
      }

      const totalLen = pcmChunks.reduce((acc, chunk) => acc + chunk.length, 0);
      const combinedPcm = new Int16Array(totalLen);
      let offset = 0;
      for (const chunk of pcmChunks) { combinedPcm.set(chunk, offset); offset += chunk.length; }

      const blob = createWavBlob(combinedPcm, 24000);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter.title.substring(0,20)}_Part${part}.wav`;
      a.click();
    } catch (err: any) {
      setError(err.message?.includes('429') ? "Quota esgotada. Prova-ho en uns minuts." : "Error en descàrrega.");
    } finally {
      setExportProgress(null);
    }
  };

  const handleTogglePlay = async () => {
    if (playback.isPlaying) { stopAudio(); return; }
    if (!rendition) return;
    const contents = rendition.getContents();
    if (!contents || contents.length === 0) return;
    let text = '';
    contents.forEach((c: any) => text += c.document.body.innerText);
    const chunks = chunkText(text);
    if (chunks.length > 0) playNextChunk(chunks, 0);
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      <header className="h-16 flex items-center justify-between px-4 md:px-8 border-b bg-white z-20">
        <div className="flex items-center gap-3">
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 hover:bg-slate-100 rounded-lg lg:hidden">
            <Menu className="w-6 h-6 text-slate-600" />
          </button>
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-1.5 rounded-lg"><BookIcon className="w-5 h-5 text-white" /></div>
            <h1 className="font-bold text-xl">Lector <span className="text-indigo-600">Partit</span></h1>
          </div>
        </div>
        <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-full flex items-center gap-2 text-sm font-medium transition-all">
          <Upload className="w-4 h-4" /> <span className="hidden sm:inline">Pujar EPUB</span>
          <input type="file" accept=".epub" onChange={handleFileUpload} className="hidden" />
        </label>
      </header>

      <div className="flex flex-1 overflow-hidden relative">
        <aside className={`fixed lg:static inset-y-0 left-0 w-80 bg-white border-r z-40 transform transition-transform duration-300 ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'} flex flex-col`}>
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="font-semibold text-slate-700 uppercase text-xs tracking-widest">Capítols</h2>
            <button onClick={() => setIsSidebarOpen(false)} className="lg:hidden"><X /></button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {chapters.map((c, i) => (
              <div key={i} className="flex flex-col p-1 rounded-lg hover:bg-indigo-50 border border-transparent hover:border-indigo-100 group">
                <button onClick={() => { rendition.display(c.href); setIsSidebarOpen(false); stopAudio(); }} className="text-left px-3 py-2 text-sm text-slate-600 font-medium truncate">
                  {c.title}
                </button>
                <div className="flex gap-2 px-3 pb-1">
                  <button onClick={() => downloadSegment(c, 1)} className="text-[10px] bg-white border border-indigo-200 px-2 py-1 rounded hover:bg-indigo-600 hover:text-white flex items-center gap-1 transition-colors">
                    <Download className="w-3 h-3" /> Part 1
                  </button>
                  <button onClick={() => downloadSegment(c, 2)} className="text-[10px] bg-white border border-indigo-200 px-2 py-1 rounded hover:bg-indigo-600 hover:text-white flex items-center gap-1 transition-colors">
                    <Download className="w-3 h-3" /> Part 2
                  </button>
                </div>
              </div>
            ))}
          </div>
        </aside>

        <main className="flex-1 flex flex-col bg-slate-50 relative overflow-hidden">
          {(isLoading || isWaitingQuota || exportProgress) && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/90 backdrop-blur-sm z-50">
              <div className="text-center bg-white p-10 rounded-[3rem] shadow-2xl border border-slate-100 max-w-sm">
                {isWaitingQuota ? <Coffee className="w-16 h-16 text-amber-500 animate-bounce mx-auto mb-6" /> : <Loader2 className="w-14 h-14 text-indigo-600 animate-spin mx-auto mb-6" />}
                <h3 className="text-xl font-bold text-slate-800 mb-2">
                  {isWaitingQuota ? 'Límit IA' : exportProgress ? 'Creant Àudio' : 'Carregant'}
                </h3>
                <p className="text-slate-500 text-sm mb-4">
                  {isWaitingQuota ? "L'API necessita descansar." : 
                   exportProgress ? `Processant part ${exportProgress.current} de ${exportProgress.total}...` : 
                   "Preparant EPUB..."}
                </p>
                {exportProgress && (
                  <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-600" style={{ width: `${(exportProgress.current / exportProgress.total) * 100}%` }} />
                  </div>
                )}
              </div>
            </div>
          )}

          {error && <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-red-50 text-red-700 px-6 py-3 rounded-2xl border border-red-200 shadow-xl z-50 flex items-center gap-3">
            <AlertCircle className="w-5 h-5" /> <span className="text-sm font-medium">{error}</span>
          </div>}

          <div className="flex-1 w-full h-full relative overflow-hidden">
            <div ref={viewerRef} className="absolute inset-0" />
          </div>

          {book && (
            <div className="absolute inset-x-0 bottom-32 flex justify-between px-8 pointer-events-none">
              <button onClick={() => rendition?.prev()} className="pointer-events-auto p-4 bg-white/90 rounded-full shadow-lg"><ChevronLeft /></button>
              <button onClick={() => rendition?.next()} className="pointer-events-auto p-4 bg-white/90 rounded-full shadow-lg"><ChevronRight /></button>
            </div>
          )}
        </main>
      </div>

      {book && (
        <footer className="h-24 bg-white border-t px-8 flex items-center justify-between z-30 shadow-lg">
          <div className="flex-1 hidden md:block">
            <div className="flex items-center gap-2 text-indigo-600 mb-1">
              <Sparkles className="w-4 h-4" />
              <span className="text-[10px] font-bold uppercase">Optimitzat per a Grans Volums</span>
            </div>
            <p className="text-xs text-slate-400 truncate max-w-xs">{metadata?.title}</p>
          </div>

          <button onClick={handleTogglePlay} disabled={isLoading || !!exportProgress} className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${playback.isPlaying ? 'bg-red-500' : 'bg-indigo-600 hover:bg-indigo-700 shadow-xl shadow-indigo-200'}`}>
            {playback.isPlaying ? <Square className="w-6 h-6 text-white" /> : <Play className="w-7 h-7 text-white ml-1" />}
          </button>

          <div className="flex-1 flex justify-end">
            <select value={playback.dialect} onChange={(e) => setPlayback(p => ({ ...p, dialect: e.target.value as Dialect }))} className="bg-slate-50 border rounded-lg px-2 py-1 text-xs font-medium outline-none">
              <option value={Dialect.Standard}>Català Estàndard</option>
              <option value={Dialect.Valencian}>Valencià</option>
            </select>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;
