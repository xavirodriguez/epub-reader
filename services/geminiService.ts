
import { GoogleGenAI, Modality } from "@google/genai";
import { VoiceName, Dialect } from '../types';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export class GeminiTTSService {
  private lastRequestTime = 0;
  private readonly MIN_GAP = 10000; // 10 seconds minimum between successful requests for free tier

  async generateSpeech(text: string, voice: VoiceName, dialect: Dialect, retries = 8): Promise<string | undefined> {
    // Basic cleaning to optimize character count
    const cleanedText = text.replace(/\s+/g, ' ').trim();
    if (!cleanedText) return undefined;

    const dialectInstruction = dialect === Dialect.Valencian 
      ? "Llegeix aquest text amb accent i entonació de la variant regional valenciana (València, Alacant o Castelló)."
      : "Llegeix aquest text amb accent de català estàndard.";

    const fullPrompt = `${dialectInstruction} El text és: ${cleanedText}`;

    for (let i = 0; i < retries; i++) {
      try {
        // Enforce a global gap between requests to stay under RPM limits
        const now = Date.now();
        // Fixed typo: removed duplicate 'this' keyword
        const timeSinceLast = now - this.lastRequestTime;
        if (timeSinceLast < this.MIN_GAP) {
          await sleep(this.MIN_GAP - timeSinceLast);
        }

        // Always initialize GoogleGenAI with a named parameter object and process.env.API_KEY
        const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
        
        const response = await ai.models.generateContent({
          model: "gemini-2.5-flash-preview-tts",
          contents: [{ parts: [{ text: fullPrompt }] }],
          config: {
            responseModalities: [Modality.AUDIO],
            speechConfig: {
              voiceConfig: {
                prebuiltVoiceConfig: { voiceName: voice },
              },
            },
          },
        });

        const data = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
        if (!data) throw new Error("No audio data received");
        
        this.lastRequestTime = Date.now();
        return data;

      } catch (error: any) {
        const errorMsg = error?.message || "";
        const isRateLimit = errorMsg.includes('429') || error?.status === 429 || error?.code === 429;
        
        if (isRateLimit && i < retries - 1) {
          // Very aggressive backoff for free tier: 30s, 60s, 120s...
          // This ensures the "leaky bucket" of the API has time to empty.
          const waitTime = Math.pow(2, i) * 30000; 
          console.warn(`Quota 429 (Resource Exhausted). Esperant ${waitTime/1000} segons per a reintentar...`);
          await sleep(waitTime);
          continue;
        }
        
        console.error("Gemini TTS Error:", error);
        throw error;
      }
    }
  }
}

export const geminiTTS = new GeminiTTSService();
