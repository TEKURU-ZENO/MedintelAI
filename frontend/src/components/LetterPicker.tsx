export default function LetterPicker({ letters, onSelect, activeLetter }: any) {
  return (
    <div className="flex flex-wrap gap-3 justify-center mb-6">
      {letters.map((l: any) => (
        <button
          key={l.char}
          onClick={() => onSelect(l)}
          className={`w-14 h-14 rounded-2xl text-2xl font-bold shadow-sm transition-transform hover:scale-105 active:scale-95 ${
            activeLetter === l.char 
              ? "bg-sky-500 text-white ring-4 ring-sky-200" 
              : "bg-white text-sky-600 border-2 border-sky-100"
          }`}
        >
          {l.char}
        </button>
      ))}
    </div>
  );
}
