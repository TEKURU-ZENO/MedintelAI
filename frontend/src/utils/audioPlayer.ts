/**
 * audioPlayer.ts — Client-side Audio Orchestrator
 *
 * Handles preloading, caching, queuing, and interruption of audio.
 * Prevents multiple audios from overlapping chaotically.
 */

class AudioPlayer {
  private cache: Map<string, HTMLAudioElement> = new Map();
  private currentAudio: HTMLAudioElement | null = null;
  private queue: string[] = [];
  private isPlaying: boolean = false;
  private basePath: string = "http://localhost:8000"; // Assuming backend hosts /audio statically

  /**
   * Preloads an array of audio URLs silently.
   */
  public async preload(urls: string[]) {
    urls.forEach((url) => {
      if (!url) return;
      const fullUrl = url.startsWith("http") ? url : `${this.basePath}${url}`;
      if (!this.cache.has(fullUrl)) {
        const audio = new Audio(fullUrl);
        audio.preload = "auto";
        this.cache.set(fullUrl, audio);
      }
    });
  }

  /**
   * Stops currently playing audio immediately.
   */
  public interrupt() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    this.isPlaying = false;
    this.queue = [];
  }

  /**
   * Plays a single audio URL. Interrupts whatever is playing.
   */
  public async play(url: string, onEnded?: () => void) {
    if (!url) return;
    this.interrupt();

    const fullUrl = url.startsWith("http") ? url : `${this.basePath}${url}`;
    
    let audio = this.cache.get(fullUrl);
    if (!audio) {
      audio = new Audio(fullUrl);
      this.cache.set(fullUrl, audio);
    }

    this.currentAudio = audio;
    this.isPlaying = true;

    audio.onended = () => {
      this.isPlaying = false;
      this.currentAudio = null;
      if (onEnded) onEnded();
      this.playNextInQueue();
    };

    try {
      await audio.play();
    } catch (e) {
      console.warn("Audio playback prevented by browser policy", e);
      this.isPlaying = false;
      this.playNextInQueue();
    }
  }

  /**
   * Queues an audio clip to play after the current one finishes.
   */
  public enqueue(url: string) {
    if (!url) return;
    this.queue.push(url);
    if (!this.isPlaying) {
      this.playNextInQueue();
    }
  }

  private playNextInQueue() {
    if (this.queue.length > 0) {
      const nextUrl = this.queue.shift();
      if (nextUrl) {
        this.play(nextUrl);
      }
    }
  }
}

export const audioPlayer = new AudioPlayer();
