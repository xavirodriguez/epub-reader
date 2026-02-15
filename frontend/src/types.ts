
export enum VoiceName {
  Kore = 'Kore',
  Puck = 'Puck',
  Charon = 'Charon',
  Fenrir = 'Fenrir',
  Zephyr = 'Zephyr'
}

export enum Dialect {
  Standard = 'Català Estàndard',
  Valencian = 'Valencià'
}

export interface Chapter {
  id: string;
  title: string;
  href: string;
}

export interface BookMetadata {
  title: string;
  author: string;
  cover?: string;
}

export interface PlaybackState {
  isPlaying: boolean;
  isPaused: boolean;
  currentChapterIndex: number;
  currentSentenceIndex: number;
  voice: VoiceName;
  dialect: Dialect;
}
