
import { GoogleGenAI, Modality } from "@google/genai";
import { VoiceName, Dialect } from '../types';

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

export class GeminiTTSService {
  private lastRequestTime = 0;
  private readonly MIN_GAP = 12000; // 12 segons de seguretat

  async generateSpeech(text: string, voice: VoiceName, dialect: Dialect, retries = 0): Promise<string | undefined> {
    const cleanedText = text.replace(/\s+/g, ' ').trim();
    if (!cleanedText) return undefined;

    // Prompt comprimit per estalviar tokens i evitar 429
    const dialectInfo = dialect === Dialect.Valencian ? "Valencian (Western Catalan)" : "Standard Catalan";
    const fullPrompt = `Role: TTS Multi-speaker. Language: Western Catalan.
Voices: NARRADORA (desc), HARRY (Harry's dialogue).
Input: ${cleanedText}`.trim();

    for (let i = 0; i <= retries; i++) {
      try {
        const now = Date.now();
        const timeSinceLast = now - this.lastRequestTime;
        if (timeSinceLast < this.MIN_GAP) {
          await sleep(this.MIN_GAP - timeSinceLast);
        }

        const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
        
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
        throw error; // Fail fast per tancar popups
      }
    }
  }
}

export const geminiTTS = new GeminiTTSService();
