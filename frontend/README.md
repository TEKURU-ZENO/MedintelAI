# OCR Document Reading System — Frontend Application

The frontend client for the **OCR Document Reading System** is an interactive, dual-pane document intelligence studio built with React 19, TypeScript, Vite, and Tailwind CSS v4.

---

## Features

- **Google Lens Visual Overlay**: Renders detected text lines directly over the document image with zero spatial drift using exact normalized percentages (`normalized_bbox`).
- **Interactive Click-to-Copy**: Click any recognized text line directly on the visual document canvas to copy it to the system clipboard.
- **Marquee Snippet Crop Tool**: Interactive mouse drag-and-drop tool that allows users to select any focused snippet on screen or scanned documents to execute resolution-preserving 2.5× OCR.
- **Live Screen / Window Capture**: Uses `navigator.mediaDevices.getDisplayMedia` to capture open applications, hospital EHRs, browser tabs, or PDF viewers into a region-first snippet OCR workflow.
- **Three Visualization Modes**:
  - **Lens Text Mode**: Floating, semitransparent text tags directly covering the underlying document.
  - **Boxes Mode**: SVG wireframes color-coded by confidence status (`HIGH_CONFIDENCE`, `REVIEW_REQUIRED`, `HUMAN_VERIFICATION_NEEDED`).
  - **Original Document Mode**: Clean preview of the input document.
- **Plain Text (.txt) View**: Reconstructed reading-order text flow with download button.
- **Human Clinician Review Drawer**: Review and correct any block's transcription with notes, sending data back to `/ocr/correct`.

---

## Directory Architecture

```
frontend/src/
├── components/
│   └── MedIntelOCRStudio.tsx    # Primary studio console, Google Lens canvas, marquee tool
├── pages/
│   ├── LandingPage.tsx          # Feature showcase and benchmark performance dashboard
│   └── Home.tsx                 # Root console redirect
├── App.tsx                      # Client-side router configuration
├── index.css                    # Tailwind CSS v4 styling & dark theme definitions
└── main.tsx                     # React 19 root DOM renderer
```

---

## Scripts

```bash
# Install dependencies
npm install

# Run local development server
npm run dev

# Compile production bundle
npm run build

# Preview production build locally
npm run preview
```

---

## Environment Configuration

By default, the frontend sends API requests to `http://localhost:8000`. To override this, configure `.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
```
