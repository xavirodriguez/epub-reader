
import { GoogleGenAI, Modality } from "@google/genai";
import { VoiceName, Dialect } from '../types';
import { backendService, TTSProvider } from './backendService';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export class GeminiTTSService {
  private lastRequestTime = 0;
  private readonly MIN_GAP = 15000; 

  async generateSpeech(
    text: string,
    voice: VoiceName,
    dialect: Dialect,
    retries = 1
  ): Promise<string | undefined> {

    // NUEVO: Intentar primero con backend local si está habilitado
    try {
      const useBackend = localStorage.getItem('tts_provider') !== 'gemini';

      if (useBackend) {
        const audioBase64 = await backendService.generateSpeech(
          text,
          voice.toLowerCase(),
          dialect === Dialect.Valencian ? 'ca-valencia' : 'ca'
        );

        if (audioBase64) {
          console.log('[TTS] Used local backend');
          return audioBase64;
        }
      }
    } catch (backendError) {
      console.warn('[TTS] Backend failed, falling back to Gemini:', backendError);
    }

    // FALLBACK: Código original de Gemini
    const cleanedText = text.replace(/\s+/g, ' ').trim();
    if (!cleanedText) return undefined;

    const dialectContext = dialect === Dialect.Valencian ? "valencià" : "català";
    
    const fullPrompt = `
      Format: TTS Dialogue. Language: ${dialectContext}.
      Narradora: (descriptive text)
      Harry: (Harry's dialogue)
      Text: ${cleanedText}
    `.trim();

    for (let i = 0; i <= retries; i++) {
      try {
        const now = Date.now();
        const timeSinceLast = now - this.lastRequestTime;
        if (timeSinceLast < this.MIN_GAP) {
          await sleep(this.MIN_GAP - timeSinceLast);
        }

        const ai = new GoogleGenAI({ apiKey: import.meta.env.VITE_GEMINI_API_KEY });
        
        const response = await ai.models.generateContent({
          model: "gemini-2.5-flash-preview-tts",
          contents: [{ parts: [{ text: fullPrompt }] }],
          config: {
            responseModalities: [Modality.AUDIO],
            speechConfig: {
              multiSpeakerVoiceConfig: {
                speakerVoiceConfigs: [
                  {
                    speaker: 'Narradora',
                    voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Puck' } }
                  },
                  {
                    speaker: 'Harry',
                    voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } }
                  }
                ]
              }
            }
          },
        });

        const data = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
        if (!data) throw new Error("No data received");
        
        this.lastRequestTime = Date.now();
        return data;

      } catch (error: any) {
        const status = error?.status || (error?.message?.includes('429') ? 429 : 0);
        
        if (status === 429 && i < retries) {
          console.warn(`[Quota 429] Intentant un últim cop en 10s...`);
          await sleep(10000);
          continue;
        }
        
        throw error;
      }
    }
  }
}

export const geminiTTS = new GeminiTTSService();
