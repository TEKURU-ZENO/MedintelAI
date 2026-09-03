import { samplePath } from "../utils/pathSampler";

export type LetterDef = {
  char: string;
  path: string;
  points: { x: number; y: number }[];
};

export const LETTERS: LetterDef[] = [
  {
    char: "A",
    path: "M0.2 0.8 L0.5 0.2 L0.8 0.8 M0.35 0.5 L0.65 0.5",
    points: []
  },
  {
    char: "B",
    path: "M0.3 0.2 L0.3 0.8 M0.3 0.8 L0.6 0.8 Q0.75 0.8 0.75 0.65 Q0.75 0.5 0.6 0.5 M0.3 0.5 L0.6 0.5 Q0.7 0.5 0.7 0.35 Q0.7 0.2 0.6 0.2 L0.3 0.2",
    points: []
  },
  {
    char: "C",
    path: "M0.7 0.3 Q0.5 0.1 0.3 0.3 Q0.1 0.5 0.3 0.7 Q0.5 0.9 0.7 0.7",
    points: []
  }
];

// Initialize points lazily in the browser
if (typeof document !== "undefined") {
  LETTERS.forEach(l => {
    if (!l.points.length) l.points = samplePath(l.path, 140);
  });
}
