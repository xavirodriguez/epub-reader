
import { GoogleGenAI, Modality } from "@google/genai";
import { VoiceName, Dialect } from '../types';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export class GeminiTTSService {
  private ai: GoogleGenAI;

  constructor() {
    this.ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
  }

  async generateSpeech(text: string, voice: VoiceName, dialect: Dialect, retries = 5): Promise<string | undefined> {
    const dialectInstruction = dialect === Dialect.Valencian 
      ? "Llegeix aquest text amb accent i entonació de la variant regional valenciana (València, Alacant o Castelló)."
      : "Llegeix aquest text amb accent de català estàndard.";

    const fullPrompt = `${dialectInstruction} El text és: ${text}`;

    for (let i = 0; i < retries; i++) {
      try {
        // Create a new instance if needed or use existing. Rules say create new if needed to ensure up-to-date key,
        // but since we rely on process.env.API_KEY which is injected, one instance is usually fine.
        // However, following the instruction: "Create a new GoogleGenAI instance right before making an API call"
        const genAI = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
        
        const response = await genAI.models.generateContent({
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

        return response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      } catch (error: any) {
        const errorMsg = error?.message || "";
        const isRateLimit = errorMsg.includes('429') || error?.status === 429 || error?.code === 429;
        
        if (isRateLimit && i < retries - 1) {
          // More aggressive backoff for 429s: 5s, 10s, 20s, 40s...
          const waitTime = Math.pow(2, i) * 5000; 
          console.warn(`Quota excedida (429). Esperant ${waitTime}ms... (Intent ${i + 1}/${retries})`);
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
