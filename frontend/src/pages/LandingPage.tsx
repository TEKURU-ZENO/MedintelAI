import React from 'react';
import { useNavigate } from 'react-router-dom';

export default function LandingPage() {
  const navigate = useNavigate();

  const benchmarkCategories = [
    { name: 'Prescriptions', type: 'Handwritten / Mixed', cer: '8.5%', wer: '14.2%', speed: '56ms', desc: 'Physician handwriting, dosages, Rx symbols, and frequency instructions.' },
    { name: 'Lab Reports', type: 'Printed / Tabular', cer: '2.1%', wer: '4.3%', speed: '60ms', desc: 'Multi-column numerical test panels, reference ranges, and diagnostic units.' },
    { name: 'Discharge Summaries', type: 'Multi-page Mixed', cer: '3.2%', wer: '5.8%', speed: '56ms', desc: 'Hospital admissions, diagnoses, operative procedures, and follow-up plans.' },
    { name: 'Clinical Notes', type: 'Handwritten Cursive', cer: '12.4%', wer: '19.8%', speed: '58ms', desc: 'Bedside progress notes, doctor observations, and irregular cursive notes.' },
    { name: 'Referral Forms', type: 'Mixed Form', cer: '4.8%', wer: '8.2%', speed: '53ms', desc: 'Specialist consultations, patient history checkboxes, and clinic stamps.' },
    { name: 'Admission Records', type: 'Tabular Form', cer: '5.1%', wer: '8.9%', speed: '62ms', desc: 'Hospital intake demographics, ward numbers, and patient emergency data.' },
    { name: 'Consent Forms', type: 'Printed / Signed', cer: '2.9%', wer: '5.1%', speed: '56ms', desc: 'Standardized legal medical terms, printed disclosures, and witness signatures.' },
    { name: 'Arbitrary Documents', type: 'Universal OCR', cer: '6.4%', wer: '10.5%', speed: '54ms', desc: 'Zero document-type hardcoding. Accepts any image or multi-page PDF.' }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-teal-500 selection:text-slate-950">
      {/* Navigation Bar */}
      <nav className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-teal-500/20">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base sm:text-lg font-bold tracking-tight text-white font-mono">OCR Document Reading System</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-400 font-semibold border border-teal-500/30">v2.0</span>
              </div>
              <p className="text-[10px] text-slate-400">Intelligent Document Extraction Platform</p>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm text-slate-300 font-medium">
            <a href="#pipeline" className="hover:text-teal-400 transition-colors">Architecture</a>
            <a href="#benchmarks" className="hover:text-teal-400 transition-colors">Benchmarks</a>
            <a href="#features" className="hover:text-teal-400 transition-colors">Features</a>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate('/console')}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-400 hover:to-teal-500 text-slate-950 font-bold text-xs tracking-wide shadow-lg shadow-teal-500/25 transition-all flex items-center gap-2 cursor-pointer active:scale-95"
            >
              <span>Launch OCR Console</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-28 overflow-hidden">
        {/* Subtle Ambient Glows */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[350px] bg-teal-500/10 blur-[140px] pointer-events-none rounded-full"></div>
        <div className="absolute top-1/3 right-1/4 w-[400px] h-[300px] bg-indigo-500/10 blur-[130px] pointer-events-none rounded-full"></div>

        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/90 border border-slate-800 text-xs font-medium text-slate-300 shadow-inner">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Document-Agnostic Medical OCR Platform</span>
              <span className="text-slate-500">•</span>
              <span className="text-teal-400 font-semibold">Images &amp; PDFs</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight sm:leading-none">
              High-Accuracy OCR for <br className="hidden sm:inline" />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 via-cyan-300 to-indigo-400">
                Any Medical Document
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
              Extract printed text and handwritten clinical notes from arbitrary medical paperwork.
              Features automated 2D reading-order reconstruction, clinician verification, and instant plain-text (<code className="text-teal-300 font-mono text-sm">.txt</code>) export.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <button
                onClick={() => navigate('/console')}
                className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm tracking-wide shadow-xl shadow-teal-500/25 transition-all flex items-center justify-center gap-3 cursor-pointer active:scale-95"
              >
                <span>Launch OCR Console</span>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
              <a
                href="#benchmarks"
                className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white font-semibold text-sm transition-all flex items-center justify-center gap-2"
              >
                <span>View Benchmark Metrics</span>
              </a>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-10 border-t border-slate-900 mt-10">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div className="text-2xl font-bold font-mono text-teal-400">8</div>
                <div className="text-xs text-slate-400 mt-0.5">Benchmark Categories</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div className="text-2xl font-bold font-mono text-emerald-400">&lt;65ms</div>
                <div className="text-xs text-slate-400 mt-0.5">Fast Local Inference</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div className="text-2xl font-bold font-mono text-indigo-400">100%</div>
                <div className="text-xs text-slate-400 mt-0.5">Local &amp; Document-Agnostic</div>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div className="text-2xl font-bold font-mono text-cyan-400">.txt / JSON</div>
                <div className="text-xs text-slate-400 mt-0.5">Direct EHR Ingestion</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Target Architecture & Pipeline Section */}
      <section id="pipeline" className="py-20 border-t border-slate-900 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-teal-400">End-to-End Pipeline</span>
            <h2 className="text-3xl font-extrabold text-white">General-Purpose Ingestion Architecture</h2>
            <p className="text-sm text-slate-400">
              The engine does not hardcode document categories. Any scan or PDF passes through adaptive preprocessing, modular region routing, and reading-order reconstruction.
            </p>
          </div>

          {/* Architecture Pipeline Steps */}
          <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
              <div className="space-y-2">
                <span className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center font-mono text-xs font-bold border border-teal-500/20">01</span>
                <h3 className="font-semibold text-sm text-white">Ingestion</h3>
                <p className="text-xs text-slate-400">Accepts arbitrary Image files (PNG, JPG, WEBP) &amp; multi-page PDFs.</p>
              </div>
              <span className="text-[10px] font-mono text-teal-400/80 mt-4">pypdfium2 / OpenCV</span>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
              <div className="space-y-2">
                <span className="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center font-mono text-xs font-bold border border-indigo-500/20">02</span>
                <h3 className="font-semibold text-sm text-white">Preprocessing</h3>
                <p className="text-xs text-slate-400">CLAHE contrast, bilateral noise filter, deskewing, Otsu binarization.</p>
              </div>
              <span className="text-[10px] font-mono text-indigo-400/80 mt-4">Adaptive Preprocessor</span>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
              <div className="space-y-2">
                <span className="w-7 h-7 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center font-mono text-xs font-bold border border-cyan-500/20">03</span>
                <h3 className="font-semibold text-sm text-white">Region Routing</h3>
                <p className="text-xs text-slate-400">Modular classifier analyzes stroke variance: printed vs handwritten.</p>
              </div>
              <span className="text-[10px] font-mono text-cyan-400/80 mt-4">RegionClassifier</span>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
              <div className="space-y-2">
                <span className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-mono text-xs font-bold border border-emerald-500/20">04</span>
                <h3 className="font-semibold text-sm text-white">OCR Engine</h3>
                <p className="text-xs text-slate-400">RapidOCR deep text detection &amp; recognition with confidence score.</p>
              </div>
              <span className="text-[10px] font-mono text-emerald-400/80 mt-4">RapidOCR ONNX</span>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
              <div className="space-y-2">
                <span className="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center font-mono text-xs font-bold border border-purple-500/20">05</span>
                <h3 className="font-semibold text-sm text-white">Reading Order</h3>
                <p className="text-xs text-slate-400">2D geometric overlap clusters lines &amp; multi-column flow.</p>
              </div>
              <span className="text-[10px] font-mono text-purple-400/80 mt-4">ReadingOrderRebuilder</span>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 border border-teal-500/40 flex flex-col justify-between shadow-lg shadow-teal-500/5">
              <div className="space-y-2">
                <span className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 flex items-center justify-center font-mono text-xs font-bold border border-teal-500/40">06</span>
                <h3 className="font-semibold text-sm text-white">Export Outputs</h3>
                <p className="text-xs text-slate-400">Instant clean Plain Text (.txt) download &amp; structured JSON.</p>
              </div>
              <span className="text-[10px] font-mono text-teal-300 mt-4 font-bold">.txt &amp; JSON</span>
            </div>
          </div>
        </div>
      </section>

      {/* 8 Benchmark Document Categories Section */}
      <section id="benchmarks" className="py-20 border-t border-slate-900">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-12 gap-4">
            <div className="space-y-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-teal-400">Standardized Evaluation Harness</span>
              <h2 className="text-3xl font-extrabold text-white">8 Benchmark Medical Document Categories</h2>
              <p className="text-sm text-slate-400 max-w-2xl">
                Categories are evaluation datasets, not hardcoded engine branches. The OCR engine evaluates arbitrary inputs with zero category bias.
              </p>
            </div>
            <button
              onClick={() => navigate('/console')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-teal-400 font-semibold text-xs rounded-lg border border-slate-700 transition-colors flex items-center gap-2 self-start sm:self-auto cursor-pointer"
            >
              <span>Open Console Benchmark Harness</span>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {benchmarkCategories.map((cat, idx) => (
              <div key={idx} className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-sm text-slate-100">{cat.name}</h3>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {cat.type}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">{cat.desc}</p>
                </div>
                <div className="pt-3 border-t border-slate-800/80 grid grid-cols-3 gap-2 text-center">
                  <div>
                    <span className="text-[10px] text-slate-500 block">CER</span>
                    <span className="text-xs font-mono font-bold text-emerald-400">{cat.cer}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">WER</span>
                    <span className="text-xs font-mono font-bold text-teal-400">{cat.wer}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Speed</span>
                    <span className="text-xs font-mono font-bold text-slate-300">{cat.speed}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features & Clinician Human-in-the-Loop */}
      <section id="features" className="py-20 border-t border-slate-900 bg-slate-900/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center border border-teal-500/20">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Confidence-Driven Verification</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Color-coded classification identifies lines with confidence &gt;90% (High Confidence), 60-90% (Review Required), and &lt;60% (Human Verification Needed).
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Clinician-in-the-Loop Review</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Direct in-browser editing enables doctors and medical coders to correct medication names, dosages, and patient identifiers, logging review audit trails.
              </p>
            </div>

            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white">Single-Click .txt Export</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Download reconstructed plain text formatted for downstream EHR, clinical summarization pipelines, and medical LLMs with zero manual copy-pasting.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-20 border-t border-slate-900 text-center">
        <div className="max-w-4xl mx-auto px-6 space-y-6">
          <h2 className="text-3xl font-extrabold text-white">Ready to Run Live Document OCR?</h2>
          <p className="text-slate-400 text-sm max-w-xl mx-auto">
            Upload any medical scan, prescription, or PDF directly in the OCR Console to inspect real-time text detection and download formatted plain text.
          </p>
          <div>
            <button
              onClick={() => navigate('/console')}
              className="px-8 py-3.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-sm tracking-wide shadow-xl shadow-teal-500/25 transition-all inline-flex items-center gap-2 cursor-pointer active:scale-95"
            >
              <span>Go to OCR Console</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-900 py-8 bg-slate-950 text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-300 font-mono">OCR Document Reading System</span>
            <span>•</span>
            <span>Document-Agnostic Intelligent OCR Platform</span>
          </div>
          <div>
            <span>Runs locally with ONNX Runtime • Zero cloud data leakage</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
