/**
 * spelling.ts — API Client for Phase 6.3 Spelling System
 */

import { api } from "./client";

export interface WordMetadata {
  word: string;
  difficulty: number;
  phonics?: string;
  stroke_complexity?: string;
  focus_letters: string[];
  category?: string;
}

export interface LiteracySessionConfig {
  word_metadata: WordMetadata;
  assist_profile: {
    show_ghost_word: boolean;
    show_next_letter_hint: boolean;
    auto_repeat_pronunciation: boolean;
    forgiveness_level: string;
  };
  coaching_policy: any;
  audio: {
    pronunciations: {
      word: string;
      letters: Record<string, string>;
    };
    coach_audio: Record<string, string>;
  };
}

export interface SpellingProgressionState {
  target: string;
  progress: string[];
  next_expected: string | null;
  state: "idle" | "listening" | "attempting" | "partial_success" | "correct" | "retrying" | "celebrating";
  accuracy: number;
  attempts_on_current: number;
}

export const spellingApi = {
  /** Fetch the complete literacy orchestrator payload for a specific word. */
  getConfig: (word: string, learningStyle: string = "adult", profileType: string = "child") => {
    return api.get<LiteracySessionConfig>(`/spelling/config`, {
      params: { word, learning_style: learningStyle, profile_type: profileType }
    });
  },

  /** Validates a letter attempt and returns the updated state machine. */
  validateAttempt: (targetWord: string, currentProgress: string[], attemptedLetter: string) => {
    return api.post<SpellingProgressionState>("/spelling/attempt", {
      target_word: targetWord,
      current_progress: currentProgress,
      attempted_letter: attemptedLetter
    });
  }
};
