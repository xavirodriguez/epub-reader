/**
 * Cliente para comunicación con backend local.
 */
import axios, { AxiosInstance } from 'axios';

export enum TTSProvider {
  Local = 'local',
  Gemini = 'gemini',
  Auto = 'auto'
}

export enum TTSEngine {
  Piper = 'piper',
  Coqui = 'coqui',
  Bark = 'bark'
}

export interface TTSRequest {
  text: string;
  voice: string;
  language: string;
  engine?: TTSEngine;
  use_cache?: boolean;
}

export interface TTSResponse {
  audio_data: string; // base64
  source: string;
  cached: boolean;
  sample_rate: number;
  duration_seconds?: number;
}

export interface ProcessTextRequest {
  text: string;
  detect_speakers: boolean;
  dialect: string;
}

export interface TextSegment {
  speaker: string;
  text: string;
  original_text?: string;
}

export interface ProcessTextResponse {
  processed_segments: TextSegment[];
  dialect: string;
  metadata: Record<string, any>;
}

class BackendService {
  private client: AxiosInstance;
  private baseUrl: string;
  private provider: TTSProvider = TTSProvider.Auto;
  private isAvailable: boolean = false;

  constructor() {
    this.baseUrl = (import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8000';

    this.client = axios.create({
      baseURL: `${this.baseUrl}/api`,
      timeout: 60000, // 60s timeout
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Interceptor para logging
    this.client.interceptors.response.use(
      response => {
        console.log(`[Backend] ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
        return response;
      },
      error => {
        console.error(`[Backend] Error: ${error.message}`);
        return Promise.reject(error);
      }
    );

    // Verificar disponibilidad al iniciar
    this.checkAvailability();
  }

  async checkAvailability(): Promise<boolean> {
    try {
      const response = await this.client.get('/health/ping', { timeout: 5000 });
      this.isAvailable = response.status === 200;
      console.log(`[Backend] Available: ${this.isAvailable}`);
      return this.isAvailable;
    } catch (error) {
      this.isAvailable = false;
      console.warn('[Backend] Not available, will use Gemini fallback');
      return false;
    }
  }

  setProvider(provider: TTSProvider) {
    this.provider = provider;
    console.log(`[Backend] Provider set to: ${provider}`);
  }

  async generateSpeech(
    text: string,
    voice: string,
    language: string,
    engine?: TTSEngine
  ): Promise<string> {
    // Si no está disponible o es solo Gemini, saltar
    if (!this.isAvailable || this.provider === TTSProvider.Gemini) {
      throw new Error('Backend not available');
    }

    const request: TTSRequest = {
      text,
      voice,
      language,
      engine,
      use_cache: true
    };

    try {
      const response = await this.client.post<TTSResponse>('/tts/generate', request);

      console.log(
        `[Backend] TTS generated: ${response.data.source} ` +
        `(cached: ${response.data.cached}, duration: ${response.data.duration_seconds}s)`
      );

      return response.data.audio_data;

    } catch (error: any) {
      console.error('[Backend] TTS generation failed:', error.message);

      // Si falla y estamos en modo Auto, lanzar para que use Gemini
      if (this.provider === TTSProvider.Auto) {
        throw error;
      }

      throw new Error(`Backend TTS failed: ${error.message}`);
    }
  }

  async processText(
    text: string,
    detectSpeakers: boolean = true,
    dialect: string = 'català'
  ): Promise<ProcessTextResponse> {
    if (!this.isAvailable) {
      throw new Error('Backend not available');
    }

    const request: ProcessTextRequest = {
      text,
      detect_speakers: detectSpeakers,
      dialect
    };

    try {
      const response = await this.client.post<ProcessTextResponse>(
        '/text/process',
        request
      );

      console.log(
        `[Backend] Text processed: ${response.data.processed_segments.length} segments`
      );

      return response.data;

    } catch (error: any) {
      console.error('[Backend] Text processing failed:', error.message);
      throw error;
    }
  }

  async exportChapter(
    chapterText: string,
    voiceNarradora: string = 'narradora',
    voiceHarry: string = 'harry',
    language: string = 'ca',
    dialect: string = 'català',
    engine?: TTSEngine
  ): Promise<string> {
    if (!this.isAvailable) {
      throw new Error('Backend not available');
    }

    try {
      const response = await this.client.post('/chapters/export', {
        chapter_text: chapterText,
        voice_narradora: voiceNarradora,
        voice_harry: voiceHarry,
        language,
        dialect,
        engine
      });

      const taskId = response.data.task_id;
      console.log(`[Backend] Chapter export started: ${taskId}`);

      return taskId;

    } catch (error: any) {
      console.error('[Backend] Chapter export failed:', error.message);
      throw error;
    }
  }

  async getExportStatus(taskId: string): Promise<any> {
    if (!this.isAvailable) {
      throw new Error('Backend not available');
    }

    try {
      const response = await this.client.get(`/chapters/export/${taskId}/status`);
      return response.data;

    } catch (error: any) {
      console.error('[Backend] Failed to get export status:', error.message);
      throw error;
    }
  }

  getDownloadUrl(taskId: string): string {
    return `${this.baseUrl}/api/chapters/download/${taskId}`;
  }

  async healthCheck(): Promise<any> {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      return { status: 'unhealthy', error };
    }
  }
}

// Singleton
export const backendService = new BackendService();
