export default function ResultPanel({ data }: any) {
  const { gamification, progress, feedback, confidence, audio_url } = data;

  return (
    <div className="bg-white border p-6 rounded-lg shadow-sm space-y-6">
      <div className="flex items-center justify-between border-b pb-4">
        <div className="flex items-center gap-6">
          <div className="text-3xl font-bold tracking-tight text-yellow-500">
            {Array(gamification.stars).fill("⭐").join("")}
            <span className="text-gray-300 text-xl ml-2">({gamification.stars}/5)</span>
          </div>
          <div className="text-2xl font-bold text-gray-800">Grade: <span className="text-blue-600">{gamification.grade}</span></div>
        </div>
        <div className="flex flex-col items-end gap-2">
            <div className="text-gray-500 font-medium bg-gray-100 px-3 py-1 rounded-full w-fit">Level: {gamification.level}</div>
            {progress?.improved && (
                <div className="text-green-600 font-bold bg-green-50 px-3 py-1 rounded-full w-fit animate-pulse border border-green-200">
                    🎉 You improved!
                </div>
            )}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3">AI Feedback</h3>
        <ul className="space-y-2">
          {feedback.map((f: any, i: number) => {
             const msg = typeof f === 'string' ? f : f.message;
             return (
              <li key={i} className="flex items-start">
                <span className="text-blue-500 mr-2">•</span>
                <span className="text-gray-700">{msg}</span>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex items-center justify-between pt-4 border-t">
        <div className="text-sm font-medium text-gray-500">
            Confidence Score: <span className={confidence > 0.7 ? "text-green-600" : "text-yellow-600"}>{(confidence * 100).toFixed(1)}%</span>
        </div>
        {audio_url && (
          <audio controls src={`http://localhost:8000/${audio_url}`} className="h-10 outline-none" />
        )}
      </div>
    </div>
  );
}
