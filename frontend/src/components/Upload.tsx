import { useState } from "react";
import { api } from "../api/client";

export default function Upload({ onResult }: any) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    const selectedFile = e.target.files?.[0] || null;
    if (selectedFile && selectedFile.size > 5 * 1024 * 1024) {
      setError("File is too large. Maximum size is 5MB.");
      setFile(null);
      e.target.value = ""; // Reset input
    } else {
      setFile(selectedFile);
    }
  };

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
        const form = new FormData();
        form.append("input_type", "image");
        form.append("file", file);

        const res = await api.post("/analysis/run", form, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        onResult(res.data);
    } catch (err: any) {
        console.error("Analysis failed:", err);
        setError(err.response?.data?.detail || "Analysis failed. Please try again.");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="border border-dashed border-gray-300 p-6 rounded-lg bg-gray-50 flex flex-col items-center justify-center space-y-4">
      <h3 className="text-lg font-medium text-gray-700">Upload Handwriting Sample</h3>
      {error && <div className="text-red-500 text-sm font-medium">{error}</div>}
      <input 
        type="file" 
        accept="image/*" 
        onChange={handleFileChange} 
        className="text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />
      <button 
        disabled={loading || !file} 
        onClick={submit} 
        className={`px-6 py-2 rounded-full font-semibold transition-colors ${
            loading || !file 
            ? "bg-gray-300 text-gray-500 cursor-not-allowed" 
            : "bg-blue-600 hover:bg-blue-700 text-white shadow-md"
        }`}
      >
        {loading ? "Analyzing..." : "Analyze Image"}
      </button>
    </div>
  );
}
