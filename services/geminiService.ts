
import { GoogleGenAI, Modality } from "@google/genai";
import { VoiceName, Dialect } from '../types';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export class GeminiTTSService {
  async generateSpeech(text: string, voice: VoiceName, dialect: Dialect, retries = 6): Promise<string | undefined> {
    const dialectInstruction = dialect === Dialect.Valencian 
      ? "Llegeix aquest text amb accent i entonació de la variant regional valenciana (València, Alacant o Castelló)."
      : "Llegeix aquest text amb accent de català estàndard.";

    const fullPrompt = `${dialectInstruction} El text és: ${text}`;

    for (let i = 0; i < retries; i++) {
      try {
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

        const data = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
        if (!data) throw new Error("No audio data received");
        return data;

      } catch (error: any) {
        const errorMsg = error?.message || "";
        const isRateLimit = errorMsg.includes('429') || error?.status === 429 || error?.code === 429;
        
        if (isRateLimit && i < retries - 1) {
          // Exponential backoff: 8s, 16s, 32s... to let the quota bucket refill
          const waitTime = Math.pow(2, i) * 8000; 
          console.warn(`Quota excedida (429). Esperant ${waitTime}ms per reintentar...`);
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
