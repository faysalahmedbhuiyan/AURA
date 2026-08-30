import { useState } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api/v1";

export default function ImageGenView() {
  const [prompt, setPrompt] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [imageUrl, setImageUrl] = useState(null);
  const [durationMs, setDurationMs] = useState(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError("");
    setImageUrl(null);

    try {
      const res = await axios.post(`${API_BASE}/image/generate`, {
        prompt,
        negative_prompt: negativePrompt,
        steps: 1,
      });

      if (res.data.success) {
        setImageUrl(`${API_BASE}/image/file/${res.data.file_name}`);
        setDurationMs(res.data.duration_ms);
      } else {
        setError(res.data.error || "Generation failed.");
      }
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || "Request failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="image-gen-view">
      <h2>Image Generation</h2>
      <p className="hint">Local SDXL Turbo · Intel Iris Xe · ~45–90s per image</p>

      <textarea
        placeholder="Describe the image you want..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
      />
      <input
        type="text"
        placeholder="Negative prompt (optional)"
        value={negativePrompt}
        onChange={(e) => setNegativePrompt(e.target.value)}
      />

      <button onClick={handleGenerate} disabled={loading || !prompt.trim()}>
        {loading ? "Generating... (45-90s)" : "Generate"}
      </button>

      {error && <div className="error-box">{error}</div>}

      {imageUrl && (
        <div className="result-box">
          <img src={imageUrl} alt={prompt} style={{ maxWidth: "512px" }} />
          {durationMs != null && (
            <p className="meta">Generated in {(durationMs / 1000).toFixed(1)}s</p>
          )}
          <a href={imageUrl} download>
            Download
          </a>
        </div>
      )}
    </div>
  );
}
