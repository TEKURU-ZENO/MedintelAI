/**
 * coachingEngine.ts — Phase 6.2 Declarative Audio Engine
 *
 * Tracks cooldowns and repeat limits locally.
 * Receives the event_map, policy, and coach_audio from the backend SessionPlan.
 */

import { audioPlayer } from "./audioPlayer";

export interface CoachingEventConfig {
  intent: string;
  priority: number;
  interrupt: boolean;
  cooldown_ms: number;
  max_repeats: number;
}

export interface AudioMetadata {
  profile: any;
  policy: {
    intensity: string;
    cooldown_multiplier: number;
    global_cooldown_ms: number;
    allow_interruptions: boolean;
  };
  event_map: Record<string, CoachingEventConfig>;
  item_audio: Record<string, string>;
  coach_audio: Record<string, string>;
  celebration_audio: Record<string, string>;
}

class CoachingEngine {
  private lastGlobalPlay: number = 0;
  private eventLastPlay: Record<string, number> = {};
  private eventPlayCount: Record<string, number> = {};

  public reset() {
    this.lastGlobalPlay = 0;
    this.eventLastPlay = {};
    this.eventPlayCount = {};
  }

  public handleEvent(eventName: string, metadata?: AudioMetadata) {
    if (!metadata || !metadata.event_map) return;

    const config = metadata.event_map[eventName];
    if (!config) return;

    const { policy, coach_audio, celebration_audio } = metadata;
    const now = Date.now();

    // 1. Check global cooldown
    if (now - this.lastGlobalPlay < policy.global_cooldown_ms) {
      // Unless it's a high priority interruption
      if (!(config.interrupt && policy.allow_interruptions)) {
        return;
      }
    }

    // 2. Check event-specific cooldown
    const lastPlay = this.eventLastPlay[eventName] || 0;
    const cooldownMs = config.cooldown_ms * policy.cooldown_multiplier;
    if (now - lastPlay < cooldownMs) {
      return;
    }

    // 3. Check repeat limits
    const playCount = this.eventPlayCount[eventName] || 0;
    if (playCount >= config.max_repeats) {
      return;
    }

    // 4. Resolve audio URL
    let url = coach_audio[config.intent];
    if (!url && eventName.startsWith("success_")) {
      // It's a celebration event
      const tier = eventName.replace("success_", "");
      url = celebration_audio[tier];
    }

    if (!url) return;

    // 5. Play Audio
    if (config.interrupt && policy.allow_interruptions) {
      audioPlayer.play(url);
    } else {
      audioPlayer.enqueue(url);
    }

    // 6. Record usage
    this.lastGlobalPlay = now;
    this.eventLastPlay[eventName] = now;
    this.eventPlayCount[eventName] = playCount + 1;
  }
}

export const coachingEngine = new CoachingEngine();
