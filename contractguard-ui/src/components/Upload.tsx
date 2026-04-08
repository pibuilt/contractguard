import { useState } from "react";
import { api } from "../api/client";

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);

  const handleUpload = async () => {
    if (!file) return alert("Select a file");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.post("/contracts", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      alert(`Uploaded! Contract ID: ${res.data.data.contract_id}`);
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }
  };

  return (
    <div>
      <input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={handleUpload}>Upload</button>
    </div>
  );
}
